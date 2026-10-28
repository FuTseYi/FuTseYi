#!/usr/bin/env python3
"""Build, verify and serve the complete website locally (Python 3.10+)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Thread
import time

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"


def run(script, *args):
    subprocess.run([sys.executable, str(ROOT / ".github/scripts" / script), *args],
                   cwd=ROOT, check=True)


def build():
    run("build.py")
    SITE.mkdir(exist_ok=True)
    for name in ("index.html", "robots.txt", "sitemap.xml"):
        shutil.copy2(ROOT / name, SITE / name)
    for name in ("assets", "blog"):
        target = SITE / name
        if target.exists():
            # Replace only these generated directories, avoiding stale files.
            if target.is_symlink() or target.resolve().parent != SITE.resolve():
                raise ValueError(f"Unsafe preview directory: {target}")
            shutil.rmtree(target)
        shutil.copytree(ROOT / name, target)
    (SITE / ".nojekyll").touch()
    run("sync_readme.py", "--update-site")
    run("sync_activity.py")
    for page in SITE.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*\bhref=[\'"])https://futseyi\.github\.io(?=/)', r'\1', html)
        page.write_text(html, encoding="utf-8")
    run("verify.py")


def source_state():
    files = [ROOT / "index.html", ROOT / "robots.txt"]
    for folder, pattern in (("posts", "*.md"), ("assets", "*"), (".github/scripts", "*.py")):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build-only", action="store_true", help="Build and verify without starting a server")
    parser.add_argument("--watch", action="store_true", help="Rebuild after source changes; refresh the browser manually")
    args = parser.parse_args()
    if args.watch and args.build_only:
        parser.error("--watch cannot be combined with --build-only")
    if sys.version_info < (3, 10):
        parser.exit(1, "Python 3.10+ is required. On Windows, try: py -3 preview.py\n")
    try:
        import markdown  # noqa: F401
    except ImportError:
        parser.exit(1, 'Install the dependency with your Python: -m pip install "Markdown>=3.7,<4"\n')
    previous = source_state() if args.watch else None
    if args.watch:
        rebuild()
    else:
        build()
    if args.build_only:
        return
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
        print("Press Ctrl+C to stop. " + ("Watching source files; refresh the browser after rebuilding."
              if args.watch else "Re-run this command after editing files."), flush=True)
        try:
            if args.watch:
                worker = Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    watch(previous)
                finally:
                    server.shutdown()
                    worker.join()
            else:
                server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
