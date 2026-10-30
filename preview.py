#!/usr/bin/env python3
"""Build, verify and serve the complete website locally (Python 3.10+)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
import itertools
import os
import venv
import re
import shutil
import subprocess
import sys
import tempfile
from threading import Event, RLock, Thread
import time

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"
SERVING_LOCK = RLock()
# Single source of truth: pip specs and the version probe are derived from these.
MARKDOWN_MIN, MARKDOWN_MAX = (3, 7), (4, 0)
PAGEFIND_VERSION = "1.5.2"
REQUIREMENTS = (f"Markdown>={MARKDOWN_MIN[0]}.{MARKDOWN_MIN[1]},<{MARKDOWN_MAX[0]}.{MARKDOWN_MAX[1]}",
                f"pagefind[extended]=={PAGEFIND_VERSION}")
CHECK_FLAG = "--check-dependencies"
# Build output is condensed to one line: these messages become counts, the rest is
# noise while previewing. Anything unlisted is still shown, so warnings survive.
SUMMARY_RULES = (
    (re.compile(r"^Blog: generated (\d+) article", re.MULTILINE), r"\1 articles"),
    (re.compile(r"^Verified (\d+) HTML pages", re.MULTILINE), r"\1 pages verified"),
    (re.compile(r"^Rendered (\d+) public contribution repositories", re.MULTILINE), r"\1 repositories"),
)
ROUTINE_MESSAGES = re.compile(r"^(?:Injected latest blog posts|Website README unchanged|Generated website README"
                              r"|Profile README already matches)")
GREEN, RED, DIM, CYAN = "32", "31", "2", "36"
ANSI_READY = None


class PreviewServer(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        with SERVING_LOCK:
            super().do_GET()

    def do_HEAD(self):
        with SERVING_LOCK:
            super().do_HEAD()

    def log_request(self, code="-", size="-"):
        # Successful page loads are noise while previewing; failures still name the path.
        if isinstance(code, int) and code >= 400:
            super().log_request(code, size)

    def end_headers(self):
        versioned = re.fullmatch(r"/assets/(?:css/style\.css|js/site\.js)\?v=[0-9a-f]{12}", self.path)
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if versioned else "no-store")
        super().end_headers()

    def send_head(self):
        # Always serve the current build, including clients with old cached files.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        return super().send_head()


def enable_windows_ansi():
    """Enable VT sequences on classic Windows consoles; modern terminals already accept them."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mode = ctypes.c_uint32()
        handle = kernel32.GetStdHandle(-11)
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError, ValueError):
        return False


def color_enabled():
    global ANSI_READY
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return False
    if ANSI_READY is None:
        ANSI_READY = enable_windows_ansi()
    return ANSI_READY


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if color_enabled() else text


def mark(preferred, fallback):
    """Use the typographic glyph only when the console encoding can print it."""
    try:
        preferred.encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        return fallback
    return preferred


def summarize(log):
    """Condense build output into counts, returning those parts plus anything unrecognized."""
    parts = [match.expand(template) for pattern, template in SUMMARY_RULES
             if (match := pattern.search(log))]
    unexpected = [line.strip() for line in log.splitlines()
                  if line.strip() and not ROUTINE_MESSAGES.match(line.strip())
                  and not any(pattern.search(line) for pattern, _ in SUMMARY_RULES)]
    return parts, unexpected


class Progress:
    """A single rewritable line so a build never looks frozen; silent when output is redirected."""

    FRAMES = "|/-\\"
    INTERVAL = 0.12

    def __init__(self, label="Building"):
        self.label = label
        self.active = sys.stdout.isatty()
        self.stopping = Event()
        self.frames = itertools.cycle(self.FRAMES)
        self.worker = None

    def __enter__(self):
        if self.active:
            self.worker = Thread(target=self.spin, daemon=True)
            self.worker.start()
        return self

    def __exit__(self, *error):
        self.stopping.set()
        if self.worker:
            self.worker.join(timeout=1)
            sys.stdout.write("\r" + " " * (len(self.label) + 4) + "\r")
            sys.stdout.flush()
        return False

    def spin(self):
        while not self.stopping.is_set():
            sys.stdout.write(f"\r  {next(self.frames)} {self.label}")
            sys.stdout.flush()
            self.stopping.wait(self.INTERVAL)


def run(root, script, *args):
    """Run a shared build step, hiding its routine chatter but never its failures."""
    result = subprocess.run([sys.executable, str(root / ".github/scripts" / script), *args],
                            cwd=root, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise subprocess.CalledProcessError(result.returncode, script)
    return result.stdout


def assemble(root):
    """Reuse the deployment builders inside an isolated source copy, returning a one-line summary."""
    site = root / "_site"
    log = run(root, "build.py")
    site.mkdir(exist_ok=True)
    for name in ("index.html", "robots.txt", "sitemap.xml"):
        shutil.copy2(root / name, site / name)
    for name in ("assets", "blog"):
        shutil.copytree(root / name, site / name)
    (site / ".nojekyll").touch()
    log += run(root, "sync_readme.py", "--update-site")
    log += run(root, "sync_activity.py")
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*\bhref=[\'"])https://futseyi\.github\.io(?=/)', r'\1', html)
        page.write_text(html, encoding="utf-8")
    # Pagefind's banner and progress lines are noise on success; surface them on failure.
    result = subprocess.run([sys.executable, "-m", "pagefind", "--site", str(site), "--force-language", "zh"],
                            cwd=root, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise subprocess.CalledProcessError(result.returncode, "pagefind")
    return summarize(log + run(root, "verify.py"))


def build():
    # Same filesystem as _site, so publishing uses directory renames, not copies.
    with tempfile.TemporaryDirectory(prefix=".preview-", dir=ROOT) as directory:
        candidate = Path(directory)
        for name in ("index.html", "robots.txt"):
            shutil.copy2(ROOT / name, candidate / name)
        for name in ("assets", "posts", ".github/scripts"):
            shutil.copytree(ROOT / name, candidate / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        snapshot = SITE / "contributions.json"
        if snapshot.is_file():
            (candidate / "_site").mkdir()
            shutil.copy2(snapshot, candidate / "_site/contributions.json")
        summary = assemble(candidate)
        with SERVING_LOCK:
            previous = candidate / "previous"
            if SITE.exists():
                SITE.rename(previous)
            try:
                (candidate / "_site").rename(SITE)
            except OSError:
                if previous.exists():
                    previous.rename(SITE)
                raise
        return summary


def source_state():
    files = [ROOT / "index.html", ROOT / "robots.txt"]
    for folder, pattern in (("posts", "*"), ("assets", "*"), (".github/scripts", "*.py")):
        files.extend((ROOT / folder).rglob(pattern))
    state = {}
    for path in files:
        try:
            if path.is_file():
                stat = path.stat()
                state[path] = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            pass  # Editors may replace a file while it is being scanned.
    return state


def rebuild(initial=False):
    """Build and report one line; returns False when the last good preview was kept."""
    try:
        with Progress(mark("Building preview…", "Building preview...")):
            parts, notes = build()
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(paint(f"{mark('✗', 'x')} Build failed: {error}", RED), flush=True)
        print(paint("  The previous preview is still served. Fix the source and save to retry.", DIM), flush=True)
        return False
    separator = mark(" · ", " - ")
    details = separator.join(parts)
    headline = paint(f"{mark('✓', 'OK')} Build complete", GREEN)
    print(headline + (f"{separator}{details}" if details else ""), flush=True)
    for note in notes:
        print(paint(f"  {note}", DIM), flush=True)
    if not initial:
        print(paint("  Refresh your browser.", DIM), flush=True)
    return True


def discard_stale_builds():
    """Remove candidates orphaned by a killed preview; the bound port proves none is live."""
    for path in ROOT.glob(".preview-*"):
        shutil.rmtree(path, ignore_errors=True)


def watch(previous):
    pending = False
    while True:
        time.sleep(0.5)
        current = source_state()
        if current != previous:
            previous = current
            pending = True
        elif pending:
            pending = False
            rebuild()


def dependencies_valid():
    try:
        markdown = tuple(int(part) for part in version("Markdown").split(".")[:2])
        return MARKDOWN_MIN <= markdown < MARKDOWN_MAX and version("pagefind") == PAGEFIND_VERSION
    except (PackageNotFoundError, ValueError):
        return False


def dependencies_ready(interpreter):
    """Report whether interpreter already provides what build.py and Pagefind need."""
    if interpreter == Path(sys.executable):
        return dependencies_valid()
    # Probe the same script in the target environment, so the check lives in one place.
    probe = subprocess.run([str(interpreter), str(Path(__file__).resolve()), CHECK_FLAG], capture_output=True)
    return probe.returncode == 0


def ensure_dependencies():
    current = Path(sys.executable)
    if sys.prefix != sys.base_prefix:
        interpreter = current
    else:
        environment = ROOT / ".venv"
        interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not interpreter.exists():
            print("Creating .venv for preview dependencies...", flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
    if not dependencies_ready(interpreter):
        print("Installing preview build dependencies...", flush=True)
        subprocess.run([str(interpreter), "-m", "pip", "install", *REQUIREMENTS], check=True)
    if interpreter != current:
        # Restart inside the environment that now has the build dependencies.
        raise SystemExit(subprocess.call([str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build-only", action="store_true", help="Build and verify without starting a server")
    parser.add_argument(CHECK_FLAG, action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_dependencies:
        parser.exit(0 if dependencies_valid() else 1)
    if sys.version_info < (3, 10):
        parser.exit(1, "Python 3.10+ is required. On Windows, try: py -3 preview.py\n")
    try:
        ensure_dependencies()
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Dependency setup failed: {error}. Check network access and Python venv/pip support.\n")
    handler = partial(PreviewHandler, directory=str(SITE))
    try:
        server = PreviewServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        parser.exit(1, f"Cannot use port {args.port}: {error}. Stop the existing preview or use --port.\n")
    with server:
        discard_stale_builds()
        previous = source_state()
        if args.build_only:
            if not rebuild(initial=True):
                sys.exit(1)
            return
        rebuild(initial=True)
        print(paint(f"{mark('→', '->')} http://127.0.0.1:{args.port}/", CYAN), flush=True)
        print(paint("  Ctrl+C to stop. Saving a file rebuilds; refresh the browser to see it.", DIM), flush=True)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            watch(previous)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
