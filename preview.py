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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build-only", action="store_true", help="Build and verify without starting a server")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.exit(1, "Python 3.10+ is required. On Windows, try: py -3 preview.py\n")
    try:
        import markdown  # noqa: F401
    except ImportError:
        parser.exit(1, 'Install the dependency with your Python: -m pip install "Markdown>=3.7,<4"\n')
    build()
    if args.build_only:
        return
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
        print("Press Ctrl+C to stop. Re-run this command after editing files.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
