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
import subprocess
import sys
import tempfile
from threading import Event, RLock, Thread
import time
import unicodedata

from scripts import site_build

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"
SERVING_LOCK = RLock()
REQUIREMENTS = tuple(line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#")) if (ROOT / "requirements.txt").is_file() else ()
CHECK_FLAG = "--check-dependencies"
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
        self.send_header("Cache-Control", "no-store")
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


def build(options=None, destination=None):
    """Build in isolation and replace the artifact only after successful validation."""
    destination = (destination or SITE).resolve()
    generated = SITE.resolve()
    if destination == ROOT.resolve() or destination in ROOT.resolve().parents or (
            ROOT.resolve() in destination.parents and destination != generated and
            generated not in destination.parents):
        raise ValueError("Refusing to replace source files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".preview-", dir=destination.parent) as directory:
        candidate = Path(directory)
        staged = candidate / "site"
        summary = site_build.build(ROOT, staged, options or argparse.Namespace())
        from scripts.asset_urls import version_assets
        from scripts.site_verify import verify
        for page in staged.rglob("*.html"):
            page.write_text(version_assets(page.read_text(encoding="utf-8"), staged), encoding="utf-8")
        verify(staged)
        (staged / ".nojekyll").touch()
        with SERVING_LOCK:
            previous = candidate / "previous"
            if destination.exists():
                if not destination.is_dir():
                    raise ValueError(f"Output is not a directory: {destination}")
                destination.rename(previous)
            try:
                staged.rename(destination)
            except OSError:
                if previous.exists():
                    previous.rename(destination)
                raise
        return summary


def source_state():
    files = [ROOT / name for name in ("preview.py", "requirements.txt", *site_build.SOURCE_FILES)]
    for folder in ("assets", "scripts", *site_build.SOURCE_DIRS):
        files.extend((ROOT / folder).rglob("*"))
    state = {}
    for path in files:
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
            continue
        try:
            if path.is_file():
                stat = path.stat()
                state[path] = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            pass  # Editors may replace a file while it is being scanned.
    return state


def rebuild(initial=False, options=None, destination=None):
    """Report initial counts or a short update; return False on a failed build."""
    try:
        with Progress(mark("正在生成预览 / Building preview…", "Building preview...")):
            parts, notes = build(options, destination)
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


def watch(previous, options=None):
    pending = False
    while True:
        time.sleep(0.5)
        current = source_state()
        if current != previous:
            previous = current
            pending = True
        elif pending:
            pending = False
            rebuild(options=options)


def dependencies_valid():
    """Check installed distributions against the shared PEP 508 requirements."""
    if not REQUIREMENTS:
        return True
    try:
        from packaging.requirements import Requirement
        for entry in REQUIREMENTS:
            requirement = Requirement(entry)
            if not requirement.specifier.contains(version(requirement.name)):
                return False
        return True
    except (ImportError, PackageNotFoundError, ValueError, TypeError):
        return False


def dependencies_ready(interpreter):
    """Probe the same dependency check in the selected interpreter."""
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
    parser.add_argument("--output", type=Path, default=SITE, help="Build destination (build-only)")
    if hasattr(site_build, "configure_parser"):
        site_build.configure_parser(parser)
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
        if not rebuild(initial=True, options=args, destination=args.output):
            sys.exit(1)
        return
    if args.output.resolve() != SITE.resolve():
        parser.error("--output requires --build-only")
    handler = partial(PreviewHandler, directory=str(SITE))
    try:
        server = PreviewServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        parser.exit(1, f"Cannot use port {args.port}: {error}. Stop the existing preview or use --port.\n")
    with server:
        previous = source_state()
        if not rebuild(initial=True, options=args, destination=args.output) and not (SITE / "index.html").is_file():
            return 1
        print(paint(f"{mark('→', '->')} http://127.0.0.1:{args.port}/", CYAN), flush=True)
        print(paint("  保存文件后自动生成，浏览器需手动刷新。 / Saving rebuilds the site; refresh the browser manually.", DIM), flush=True)
        print(paint("  按 Ctrl+C 停止。 / Press Ctrl+C to stop.", DIM), flush=True)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            watch(previous, args)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        sys.exit(130)
