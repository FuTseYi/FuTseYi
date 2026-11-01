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
import unicodedata

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"
SERVING_LOCK = RLock()
REQUIREMENTS = tuple(line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#"))
CHECK_FLAG = "--check-dependencies"
# Summarize routine build output; retain unrecognized messages.
SUMMARY_RULES = (
    (re.compile(r"^Blog: generated (\d+) article", re.MULTILINE), r"\1 篇文章 / articles"),
    (re.compile(r"^Verified (\d+) HTML pages", re.MULTILINE), r"\1 个页面检查通过 / pages verified"),
    (re.compile(r"^Rendered (\d+) public contribution repositories", re.MULTILINE), r"\1 个贡献仓库 / contribution repositories"),
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
    """Show build progress on interactive terminals."""

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
            width = sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in self.label)
            sys.stdout.write("\r" + " " * (width + 4) + "\r")
            sys.stdout.flush()
        return False

    def spin(self):
        while not self.stopping.is_set():
            sys.stdout.write(f"\r  {next(self.frames)} {self.label}")
            sys.stdout.flush()
            self.stopping.wait(self.INTERVAL)


def run(root, script, *args):
    """Run a build step, reporting failures."""
    result = subprocess.run([sys.executable, str(root / ".github/scripts" / script), *args],
                            cwd=root, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise subprocess.CalledProcessError(result.returncode, script)
    return result.stdout


def assemble(root, refresh_activity=False):
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
    log += run(root, "sync_activity.py", *(("--refresh",) if refresh_activity else ()))
    origin = re.search(r'<link rel="canonical" href="([^"]+)"',
                       (root / "index.html").read_text(encoding="utf-8"))[1].rstrip("/")
    robots = site / "robots.txt"
    robots.write_text(robots.read_text(encoding="utf-8").rstrip("\n") +
                      "\nSitemap: " + origin + "/sitemap.xml\n", encoding="utf-8")
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*\bhref=[\'"])' + re.escape(origin) + r'(?=/)', r'\1', html)
        page.write_text(html, encoding="utf-8")
    # Pagefind's banner and progress lines are noise on success; surface them on failure.
    result = subprocess.run([sys.executable, "-m", "pagefind", "--site", str(site), "--force-language", "zh"],
                            cwd=root, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise subprocess.CalledProcessError(result.returncode, "pagefind")
    return summarize(log + run(root, "verify.py"))


def build(refresh_activity=False):
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
        summary = assemble(candidate, refresh_activity) if refresh_activity else assemble(candidate)
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
    files = [ROOT / "index.html", ROOT / "robots.txt", ROOT / "requirements.txt"]
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


def rebuild(initial=False, refresh_activity=False):
    """Report initial counts or a short update; return False on a failed build."""
    try:
        with Progress(mark("正在生成预览 / Building preview…", "Building preview...")):
            parts, notes = build(refresh_activity) if refresh_activity else build()
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(paint(f"{mark('✗', 'x')} 生成失败 / Build failed: {error}", RED), flush=True)
        print(paint("  保留上次预览，修正文件并保存后重试。 / Previous preview kept; fix the source and save to retry.", DIM), flush=True)
        return False
    separator = mark(" · ", " - ")
    details = separator.join(parts)
    message = "生成完成 / Build complete" if initial else "网站已更新，请刷新浏览器。 / Updated. Refresh your browser."
    print(paint(f"{mark('✓', 'OK')} {message}", GREEN), flush=True)
    if initial and details:
        print(paint(f"  {details}", DIM), flush=True)
    for note in notes:
        print(paint(f"  {note}", DIM), flush=True)
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
    """Check the installed packages against the shared requirements file."""
    try:
        for requirement in REQUIREMENTS:
            match = re.fullmatch(r"([a-zA-Z0-9_-]+)(?:\[[^]]+\])?((?:[<>=]+[0-9.]+)(?:,[<>=]+[0-9.]+)*)", requirement)
            if not match:
                raise ValueError(f"Unsupported requirement: {requirement}")
            installed = tuple(int(part) for part in version(match[1]).split(".")[:3])
            for operator, value in re.findall(r"(>=|<=|==|>|<)([0-9.]+)", match[2]):
                expected = tuple(int(part) for part in value.split("."))
                left, right = (installed + (0, 0, 0))[:3], (expected + (0, 0, 0))[:3]
                if not {"==": left == right, ">=": left >= right, "<=": left <= right,
                        ">": left > right, "<": left < right}[operator]:
                    return False
        return True
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
    if dependencies_ready(current):
        return
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
        subprocess.run([str(interpreter), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    if interpreter != current:
        # Restart inside the environment that now has the build dependencies.
        raise SystemExit(subprocess.call([str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build-only", action="store_true", help="Build and verify without starting a server")
    parser.add_argument("--refresh-activity", action="store_true", help="Refresh public GitHub activity during the build")
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
    if args.build_only:
        discard_stale_builds()
        if not rebuild(initial=True, refresh_activity=args.refresh_activity):
            sys.exit(1)
        return
    handler = partial(PreviewHandler, directory=str(SITE))
    try:
        server = PreviewServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        parser.exit(1, f"Cannot use port {args.port}: {error}. Stop the existing preview or use --port.\n")
    with server:
        discard_stale_builds()
        previous = source_state()
        rebuild(initial=True, refresh_activity=args.refresh_activity)
        print(paint(f"{mark('→', '->')} http://127.0.0.1:{args.port}/", CYAN), flush=True)
        print(paint("  保存文件后自动生成，浏览器需手动刷新。 / Saving rebuilds the site; refresh the browser manually.", DIM), flush=True)
        print(paint("  按 Ctrl+C 停止。 / Press Ctrl+C to stop.", DIM), flush=True)
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
