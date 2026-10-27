#!/usr/bin/env python3
"""Generate a static Writing archive from posts/*.md.

Dependencies: Python 3.12 + Python-Markdown 3.x (installed by GitHub Actions).
No client-side JavaScript, CMS, Node.js, or frontend build framework.
"""
from __future__ import annotations
import json
import re
import shutil
from datetime import date
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import markdown

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posts"
OUTPUT = ROOT / "blog"
SITE = "https://futseyi.github.io"
CSS = "/assets/style.css"

def get_post(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", raw, re.S)
    if not match:
        raise ValueError(f"{path}: Missing --- frontmatter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}: Invalid metadata line {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("title", "date", "description"):
        if not meta.get(key):
            raise ValueError(f"{path}: Missing {key}")
    date.fromisoformat(meta["date"])
    return meta, raw[match.end():]

def layout(title: str, description: str, url: str, content: str) -> str:
    title, description, url = (escape(value, quote=True) for value in (title, description, url))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#ffffff"><meta name="description" content="{description}">
<title>{title} · FuTseYi</title><link rel="canonical" href="{url}">
<link rel="icon" href="/assets/HKUST.svg" type="image/svg+xml">
<link rel="stylesheet" href="{CSS}"><script src="/assets/site.js" defer></script>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header" id="site-header"><div class="header-inner">
  <a class="brand" href="/" aria-label="FuTseYi homepage">FuTseYi<span class="brand-dot">.</span></a>
  <button class="nav-toggle" type="button" aria-controls="primary-navigation" aria-expanded="false" aria-label="Open navigation menu"><span class="menu-icon" aria-hidden="true"><span></span><span></span><span></span></span></button>
  <nav class="nav-links" id="primary-navigation" aria-label="Main navigation">
    <a href="/#about">About</a><a href="/#education">Education</a><a href="/#interests">Research</a><a href="/#projects">Projects</a><a class="is-active" href="/blog/" aria-current="page">Writing</a><a href="/#contact">Contact</a>
  </nav>
</div></header>
<main class="blog-container" id="main">{content}</main>
<footer class="site-footer"><div class="blog-footer"><span>© 2026 FuTseYi.</span><span>Made to be simple. Built to last.</span><a href="/">Home <span class="link-arrow" aria-hidden="true"></span></a></div></footer>
</body></html>
"""


def pretty_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%b %d, %Y").replace(" 0", " ")

def main() -> None:
    # Validate every source before replacing the generated website.
    # A malformed post must not erase an otherwise usable local preview.
    source_posts: list[tuple[str, dict[str, str], str]] = []
    for path in sorted(SOURCE.glob("*.md")):
        slug = path.stem
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Post filename must be a lowercase URL slug: {path.name}")
        meta, source = get_post(path)
        if meta.get("draft", "").lower() not in ("", "true", "false"):
            raise ValueError(f"{path}: draft must be true or false")
        if meta.get("draft", "").lower() != "true":
            source_posts.append((slug, meta, source))

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    posts: list[dict] = []
    parser = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    for slug, meta, source in source_posts:
        url = f"/blog/{slug}/"
        item = dict(slug=slug, url=url, title=meta["title"], date=meta["date"], description=meta["description"], tags=[t.strip() for t in meta.get("tags", "").split(",") if t.strip()])
        parser.reset()
        article = parser.convert(source)
        header = f'<a class="back-link" href="/blog/">← All writing</a><div class="article-head"><span class="blog-kicker">WRITING & NOTES</span><h1>{escape(item["title"])}</h1><time class="post-date" datetime="{item["date"]}">{pretty_date(item["date"])}</time><p class="blog-description">{escape(item["description"])}</p></div>'
        content = header + '<article class="article">' + article + '</article><div class="article-footer"><a class="back-link" href="/blog/">← Back to writing</a></div>'
        destination = OUTPUT / slug
        destination.mkdir(exist_ok=True)
        (destination / "index.html").write_text(layout(item["title"], item["description"], SITE + url, content), encoding="utf-8")
        posts.append(item)

    posts.sort(key=lambda post: (post["date"], post["slug"]), reverse=True)
    entries = []
    for post in posts:
        entries.append(f'<a class="blog-entry" href="{escape(post["url"], quote=True)}"><time class="post-date" datetime="{post["date"]}">{pretty_date(post["date"])}</time><div><h2>{escape(post["title"])} <span class="link-arrow" aria-hidden="true"></span></h2><p>{escape(post["description"])}</p></div></a>')
    index = '<a class="back-link" href="/">← Back to homepage</a><span class="blog-kicker">WRITING & NOTES</span><h1>Writing<span style="color:var(--blue)">.</span></h1><p class="blog-description">Field notes on AI, software, projects, and the things I learn along the way. Written simply, shared occasionally.</p><div class="blog-list">' + ("".join(entries) if entries else "<p>No posts yet.</p>") + '</div>'
    (OUTPUT / "index.html").write_text(layout("Writing", "Notes on AI, engineering and open-source experiments", SITE + "/blog/", index), encoding="utf-8")
    (OUTPUT / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    urls = [SITE + "/", SITE + "/blog/"] + [SITE + post["url"] for post in posts]
    sitemap = '<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{xml_escape(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    # Confirm that every published article has an HTML page and the index is sound.
    assert (OUTPUT / "index.html").is_file()
    assert all((OUTPUT / post["slug"] / "index.html").is_file() for post in posts)
    print(f"Writing: generated {len(posts)} article(s)")

if __name__ == "__main__":
    main()
