#!/usr/bin/env python3
"""Generate a static Blog archive from posts/*/index.md.

Dependencies: Python 3.12 + Python-Markdown 3.x (installed by GitHub Actions).
Pagefind indexes the generated HTML after this script runs.
"""
from __future__ import annotations
import json
import hashlib
from calendar import month_name
from itertools import groupby
import re
import shutil
import struct
from datetime import date
from html import escape, unescape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import markdown
from asset_urls import version_assets, site_url

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posts"
OUTPUT = ROOT / "blog"
SITE = site_url(ROOT)

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
    for key in ("title", "date"):
        if not meta.get(key):
            raise ValueError(f"{path}: Missing {key}")
    date.fromisoformat(meta["date"])
    return meta, raw[match.end():]

def layout(title: str, description: str, url: str, content: str, body_class: str = "blog-page", lang: str = "en") -> str:
    title, description, url = (escape(value, quote=True) for value in (title, description, url))
    lang = escape(lang, quote=True)
    home = version_assets((ROOT / "index.html").read_text(encoding="utf-8"), ROOT)
    header = re.search(r'<header class="site-header".*?</header>', home, re.S)[0]
    header = re.sub(r'(aria-label="[^"]*), back to top"', r'\1 homepage"', header)
    header = re.sub(r'href="#([^"]+)"', r'href="/#\1"', header)
    header = header.replace('src="assets/icons/favicon.svg"', 'src="/assets/icons/favicon.svg"')
    header = header.replace('href="/blog/"', 'href="/blog/" class="is-active" aria-current="page"')
    if url == f"{SITE}/blog/":
        header = header.replace('href="/blog/" class="is-active"', 'href="#main" class="is-active"')
    footer = re.search(r'<footer class="site-footer">.*?</footer>', home, re.S)[0]
    footer = footer.replace('href="#about"', 'href="#main"')
    css = '/' + re.search(r'<link rel="stylesheet" href="([^"]+)"', home)[1]
    theme_init = re.search(r'<script data-theme-init>.*?</script>', home, re.S)[0]
    year_font = '<link rel="preload" href="/assets/fonts/bodoni-moda-numerals.ttf" as="font" type="font/ttf" crossorigin>\n' if url == f"{SITE}/blog/" else ""
    scripts = '\n'.join(f'<script src="/{src}" defer></script>' for src in re.findall(r'<script src="([^"]+)"', home))

    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{description}">
<title>{title} · FuTseYi</title><link rel="canonical" href="{url}">
<link rel="icon" href="/assets/icons/favicon.ico" sizes="any">
<link rel="icon" href="/assets/icons/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
<link rel="manifest" href="/assets/icons/site.webmanifest">
<link rel="preload" href="/assets/fonts/caveat-handwriting.woff2" as="font" type="font/woff2" crossorigin>
{year_font}{theme_init}
<link rel="stylesheet" href="{css}">{scripts}
</head>
<body class="{body_class}">
<a class="skip-link" href="#main">Skip to content</a>
{header}
<main class="blog-container wrap" id="main">{content}</main>
{footer}
</body></html>
"""


def pretty_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%b %d, %Y").replace(" 0", " ")

def tag_id(tag: str) -> str:
    return "tag-" + hashlib.sha1(tag.encode("utf-8")).hexdigest()[:12]

def image_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        header = image.read(30)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">II", header[16:24])
        if header[:3] == b"GIF":
            return struct.unpack("<HH", header[6:10])
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            if header[12:16] == b"VP8X":
                return int.from_bytes(header[24:27], "little") + 1, int.from_bytes(header[27:30], "little") + 1
            if header[12:16] == b"VP8L":
                bits = int.from_bytes(header[21:25], "little")
                return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
            if header[12:16] == b"VP8 ":
                return int.from_bytes(header[26:28], "little") & 0x3fff, int.from_bytes(header[28:30], "little") & 0x3fff
        if header.startswith(b"\xff\xd8"):
            image.seek(2)
            while image.read(1) == b"\xff":
                marker = image.read(1)[0]
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    continue
                length = int.from_bytes(image.read(2), "big")
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    size = image.read(5)
                    return int.from_bytes(size[3:5], "big"), int.from_bytes(size[1:3], "big")
                image.seek(length - 2, 1)
    raise ValueError(f"Unsupported image: {path}")

def size_article_images(article: str, folder: Path) -> str:
    def size(match: re.Match[str]) -> str:
        tag = match.group()
        source = re.search(r'\bsrc="([^"]+)"', tag)
        if not source:
            return tag
        for attribute, value in (("loading", "lazy"), ("decoding", "async")):
            if not re.search(rf'\b{attribute}=', tag):
                tag = tag[:-2].rstrip() + f' {attribute}="{value}" />' if tag.endswith("/>") else tag[:-1] + f' {attribute}="{value}">'
        if re.search(r'\bwidth=', tag):
            return tag
        path = (folder / unescape(source[1])).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            return tag
        width, height = image_dimensions(path)
        return tag[:-2] + f' width="{width}" height="{height}" />' if tag.endswith("/>") else tag[:-1] + f' width="{width}" height="{height}">'
    return re.sub(r'<img\b[^>]*>', size, article)

def article_toc(tokens: list[dict]) -> tuple[str, str]:
    entries = []
    first_level = min((token["level"] for token in tokens), default=2)
    pending = list(reversed(tokens))
    while pending:
        token = pending.pop()
        pending.extend(reversed(token.get("children", [])))
        if first_level <= token["level"] <= first_level + 1:
            label = escape(unescape(re.sub(r"<[^>]+>", "", token["name"])))
            entries.append(f'<a href="#{escape(token["id"], quote=True)}" class="toc-level-{token["level"] - first_level + 1}">{label}</a>')
    if len(entries) < 3:
        return "", ""
    links = "".join(entries)
    sidebar = '<nav class="page-toc article-toc is-visible" aria-label="On this page"><span class="toc-title">ON THIS PAGE</span>' + links + '</nav>'
    inline = '<div class="article-toc-inline"><button class="article-toc-toggle" type="button" aria-expanded="false" aria-controls="article-toc-links">On this page</button><div class="article-toc-panel"><div class="article-toc-clip"><nav id="article-toc-links" aria-label="Article contents">' + links + '</nav></div></div></div>'
    return sidebar, inline


def main() -> None:
    # Validate article metadata before replacing generated pages.
    source_posts: list[tuple[str, dict[str, str], str]] = []
    for path in sorted(SOURCE.glob("*/index.md")):
        slug = path.parent.name
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Post directory must be a lowercase URL slug: {slug}")
        meta, source = get_post(path)
        source_posts.append((slug, meta, source))

    source_posts.sort(key=lambda post: (post[1]["date"], post[0]), reverse=True)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    posts: list[dict] = []
    parser = markdown.Markdown(extensions=["extra", "sane_lists", "toc", "codehilite"],
                               extension_configs={"codehilite": {"guess_lang": False, "linenums": False}})
    for position, (slug, meta, source) in enumerate(source_posts):
        url = f"/blog/{slug}/"
        item = dict(slug=slug, url=url, title=meta["title"], date=meta["date"], tags=[t.strip() for t in meta.get("tags", "").split(",") if t.strip()])
        parser.reset()
        article = size_article_images(parser.convert(source), SOURCE / slug)
        # The frontmatter title is the page H1; preserve existing TOC IDs while shifting body headings.
        article = re.sub(r"<(/?)h([1-5])(?=[\s>])", lambda match: f"<{match[1]}h{int(match[2]) + 1}", article)
        article = article.replace('<table>', '<div class="article-table" role="region" aria-label="Data table" tabindex="0"><table>').replace('</table>', '</table></div>')
        tags = ''.join(f'<a class="post-tag" href="/blog/tags/#{tag_id(tag)}"># {escape(tag)}</a>' for tag in item["tags"])
        header = f'<a class="back-link" href="/blog/"><span class="link-arrow link-arrow-left" aria-hidden="true"></span>All posts</a><div class="article-head"><span class="blog-kicker">BLOG & NOTES</span><h1>{escape(item["title"])}</h1><div class="article-meta"><time class="post-date" datetime="{item["date"]}">{pretty_date(item["date"])}</time><a class="post-date" href="https://github.com/FuTseYi/futseyi.github.io/edit/main/posts/{slug}/index.md" target="_blank" rel="noopener noreferrer"><em>Edit on GitHub</em></a></div><div class="post-tags">{tags}</div></div>'
        neighbors = []
        for offset, css_class in ((1, "previous"), (-1, "next")):
            other = position + offset
            if 0 <= other < len(source_posts):
                other_slug, other_meta, _ = source_posts[other]
                direction = '<i class="link-arrow link-arrow-left" aria-hidden="true"></i>Previous post' if offset == 1 else 'Next post<i class="link-arrow" aria-hidden="true"></i>'
                neighbors.append(f'<a class="post-neighbor {css_class}" href="/blog/{other_slug}/"><span class="post-neighbor-label">{direction}</span><strong>{escape(other_meta["title"])}</strong></a>')
        sidebar_toc, inline_toc = article_toc(parser.toc_tokens)
        content = '<div class="article-layout"><div data-pagefind-body>' + header + inline_toc + '<article class="article">' + article + '</article></div>' + sidebar_toc + '</div><nav class="post-neighbors" aria-label="Adjacent posts">' + ''.join(neighbors) + '</nav>'
        destination = OUTPUT / slug
        destination.mkdir(exist_ok=True)
        assets = SOURCE / slug / "assets"
        if assets.is_dir():
            shutil.copytree(assets, destination / "assets")
        (destination / "index.html").write_text(layout(item["title"], item["title"], SITE + url, content, body_class="blog-page article-page", lang=meta.get("lang", "zh-CN" if re.search(r"[\u3400-\u9fff]", meta["title"] + source) else "en")), encoding="utf-8")
        posts.append(item)

    entries = []
    toc_entries = []
    for year, year_posts_iter in groupby(posts, key=lambda post: post["date"][:4]):
        year_posts = list(year_posts_iter)
        entries.append(f'<section class="archive-year" id="year-{year}" aria-label="{year} posts"><div class="archive-heading"><h2>{year}</h2><span>{len(year_posts)} posts</span></div>')
        toc_entries.append(f'<a class="toc-level-1" href="#year-{year}">{year}</a>')
        for month, month_posts_iter in groupby(year_posts, key=lambda post: post["date"][5:7]):
            month_posts = list(month_posts_iter)
            month_id = f'month-{year}-{month}'
            toc_entries.append(f'<a class="toc-level-2" href="#{month_id}">{month_name[int(month)]}</a>')
            for position, post in enumerate(month_posts):
                anchor = f' id="{month_id}"' if position == 0 else ''
                entries.append(f'<a class="blog-entry" id="post-{post["slug"]}" href="{escape(post["url"], quote=True)}"><time class="post-date"{anchor} datetime="{post["date"]}">{pretty_date(post["date"])}</time><h3><span class="link-label">{escape(post["title"][:-2])}<span class="title-tail">{escape(post["title"][-2:])}&nbsp;<span class="link-arrow" aria-hidden="true"></span></span></span></h3></a>')
        entries.append('</section>')
    tag_posts: dict[str, list[dict]] = {}
    for post in posts:
        for tag in post["tags"]:
            tag_posts.setdefault(tag, []).append(post)
    sorted_tags = sorted(tag_posts.items(), key=lambda pair: (-len(pair[1]), pair[0].casefold()))
    sidebar_tags = ''.join(f'<li><a class="post-tag" href="/blog/tags/#{tag_id(tag)}"># {escape(tag)} <span>({len(matches)})</span></a></li>' for tag, matches in sorted_tags[:30])
    sidebar = '<aside class="blog-sidebar"><h2>Tags</h2><ul>' + sidebar_tags + '</ul><a class="all-tags-link" href="/blog/tags/">View all<span class="link-arrow" aria-hidden="true"></span></a></aside>'
    archive_toc = '<nav class="page-toc archive-toc" aria-label="Archive by year and month"><span class="toc-title">ARCHIVE</span>' + ''.join(toc_entries) + '</nav>'
    search = '<dialog class="search-dialog" id="search-dialog" aria-label="Search articles"><div class="search-dialog-head"><label for="blog-search">Search articles</label><button type="button" class="search-close" aria-label="Close search">×</button></div><input id="blog-search" type="search" placeholder="Search in English or 中文" autocomplete="off" aria-controls="search-results"><div id="search-results" aria-live="polite"></div></dialog>'
    search_icon = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.2 4.2"/></svg>'
    index = search + '<div class="blog-layout"><h1 class="blog-title">Blog<span style="color:var(--accent)">.</span></h1><div class="blog-actions"><button type="button" class="search-open" aria-keyshortcuts="Control+K Meta+K" aria-label="Search articles">' + search_icon + '<span class="search-label">Search</span><kbd>⌘/Ctrl K</kbd></button><a class="blog-tags-mobile" href="/blog/tags/">All tags <span class="link-arrow" aria-hidden="true"></span></a></div>' + archive_toc + '<div class="blog-list">' + ("".join(entries) if entries else "<p>No posts yet.</p>") + '</div>' + sidebar + '</div>'
    (OUTPUT / "index.html").write_text(layout("Blog", "Notes on AI, engineering and open-source experiments", SITE + "/blog/", index), encoding="utf-8")
    tag_groups = []
    for tag, matches in sorted_tags:
        links = ''.join(f'<li><a href="{escape(post["url"], quote=True)}">{escape(post["title"])}</a></li>' for post in matches)
        tag_groups.append(f'<details class="tag-group" id="{tag_id(tag)}" open><summary># {escape(tag)} <span>({len(matches)})</span></summary><ul>{links}</ul></details>')
    tags_content = '<a class="back-link" href="/blog/"><span class="link-arrow link-arrow-left" aria-hidden="true"></span>All posts</a><h1>All Tags</h1><div class="tag-groups">' + ''.join(tag_groups) + '</div>'
    tags_output = OUTPUT / "tags"
    tags_output.mkdir()
    (tags_output / "index.html").write_text(layout("All Tags", "Browse blog posts by tag", SITE + "/blog/tags/", tags_content), encoding="utf-8")
    (OUTPUT / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    urls = [SITE + "/", SITE + "/blog/", SITE + "/blog/tags/"] + [SITE + post["url"] for post in posts]
    sitemap = '<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{xml_escape(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"Blog: generated {len(posts)} article(s)")

if __name__ == "__main__":
    main()
