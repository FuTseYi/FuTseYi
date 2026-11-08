"""Personal-site content pipeline; preview.py owns serving and atomic publication."""
import re
import shutil
import subprocess
import sys

SOURCE_FILES = ("index.html", "robots.txt", "LICENSE", "LICENSE-CONTENT", "LICENSING.md", "PUBLISHED_README.md")
SOURCE_DIRS = ("posts",)


def configure_parser(parser):
    parser.add_argument("--refresh-activity", action="store_true", help="Refresh public GitHub activity")


# Summarize routine build output; retain unrecognized messages.
SUMMARY_RULES = (
    (re.compile(r"^Blog: generated (\d+) article", re.MULTILINE), r"\1 篇文章 / articles"),
    (re.compile(r"^Verified (\d+) HTML pages", re.MULTILINE), r"\1 个页面检查通过 / pages verified"),
    (re.compile(r"^Rendered (\d+) public contribution repositories", re.MULTILINE), r"\1 个贡献仓库 / contribution repositories"),
)
ROUTINE_MESSAGES = re.compile(r"^(?:Injected latest blog posts|Profile README already matches)")

def summarize(log):
    """Condense build output into counts, returning those parts plus anything unrecognized."""
    parts = [match.expand(template) for pattern, template in SUMMARY_RULES
             if (match := pattern.search(log))]
    unexpected = [line.strip() for line in log.splitlines()
                  if line.strip() and not ROUTINE_MESSAGES.match(line.strip())
                  and not any(pattern.search(line) for pattern, _ in SUMMARY_RULES)]
    return parts, unexpected


def run(root, script, *args):
    """Run a build step, reporting failures."""
    result = subprocess.run([sys.executable, str(root / "scripts" / script), *args],
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
    for name in ("LICENSE", "LICENSE-CONTENT", "LICENSING.md"):
        shutil.copy2(root / name, site / name)
    shutil.copy2(root / "PUBLISHED_README.md", site / "README.md")
    log += run(root, "site_metadata.py", "--update-homepage")
    for name in ("assets", "blog"):
        shutil.copytree(root / name, site / name)
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
    from .asset_urls import version_assets
    for page in site.rglob("*.html"):
        page.write_text(version_assets(page.read_text(encoding="utf-8"), site), encoding="utf-8")
    return summarize(log + run(root, "verify.py"))



def build(root, destination, options):
    candidate = destination.parent / "source"
    candidate.mkdir()
    for name in SOURCE_FILES:
        shutil.copy2(root / name, candidate / name)
    for name in ("assets", "posts", "scripts"):
        shutil.copytree(root / name, candidate / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    snapshot = root / "_site/contributions.json"
    if snapshot.is_file():
        (candidate / "_site").mkdir()
        shutil.copy2(snapshot, candidate / "_site/contributions.json")
    summary = assemble(candidate, getattr(options, "refresh_activity", False))
    (candidate / "_site").rename(destination)
    return summary
