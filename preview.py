#!/usr/bin/env python3
"""Build, verify and serve the complete website locally (Python 3.10+)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
import venv
import re
import shutil
import subprocess
import sys
import tempfile
from threading import RLock, Thread
import time

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"
SERVING_LOCK = RLock()


class PreviewServer(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        with SERVING_LOCK:
            super().do_GET()

    def do_HEAD(self):
        with SERVING_LOCK:
            super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        # Always serve the current build, including clients with old cached files.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        return super().send_head()


def run(root, script, *args):
    subprocess.run([sys.executable, str(root / ".github/scripts" / script), *args],
                   cwd=root, check=True)


def assemble(root):
    """Reuse the deployment builders inside an isolated source copy."""
    site = root / "_site"
    run(root, "build.py")
    site.mkdir(exist_ok=True)
    for name in ("index.html", "robots.txt", "sitemap.xml"):
        shutil.copy2(root / name, site / name)
    for name in ("assets", "blog"):
        shutil.copytree(root / name, site / name)
    (site / ".nojekyll").touch()
    run(root, "sync_readme.py", "--update-site")
    run(root, "sync_activity.py")
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*\bhref=[\'"])https://futseyi\.github\.io(?=/)', r'\1', html)
        page.write_text(html, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pagefind", "--site", str(site), "--force-language", "zh"], cwd=root, check=True)
    run(root, "verify.py")


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
        assemble(candidate)
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


def rebuild():
    try:
        build()
        print("Build complete. Refresh your browser.", flush=True)
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f"Build failed: {error}. Fix the source and save to retry.", flush=True)


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


def ensure_dependencies():
    try:
        installed = tuple(int(part) for part in version("Markdown").split(".")[:2])
        if (3, 7) <= installed < (4, 0) and version("pagefind") == "1.5.2":
            return
    except PackageNotFoundError:
        pass
    # Install into an active virtual environment, or create a project-local one.
    if sys.prefix != sys.base_prefix:
        interpreter = Path(sys.executable)
    else:
        environment = ROOT / ".venv"
        interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not interpreter.exists():
            print("Creating .venv for preview dependencies...", flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
    print("Installing preview build dependencies...", flush=True)
    subprocess.run([str(interpreter), "-m", "pip", "install", "Markdown>=3.7,<4", "pagefind[extended]==1.5.2"], check=True)
    if interpreter != Path(sys.executable):
        raise SystemExit(subprocess.call([str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build-only", action="store_true", help="Build and verify without starting a server")
    args = parser.parse_args()
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
        previous = source_state()
        if args.build_only:
            build()
            return
        rebuild()
        print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
        print("Press Ctrl+C to stop. Watching source files; refresh the browser after rebuilding.", flush=True)
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
    main()
