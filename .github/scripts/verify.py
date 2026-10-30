#!/usr/bin/env python3
"""Verify generated static pages and local references before deployment."""
from __future__ import annotations
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree
from asset_urls import version_assets

ROOT = Path(__file__).resolve().parents[2] / "_site"
ORIGIN = "https://futseyi.github.io"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag in ("a", "link") and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in ("img", "source", "script") and attrs.get("src"):
            self.links.append(attrs["src"])
        if tag in ("img", "source") and attrs.get("srcset"):
            for candidate in attrs["srcset"].split(","):
                src = candidate.strip().split()
                if src:
                    self.links.append(src[0])


def local_target(page: Path, link: str) -> tuple[Path, str] | None:
    link = link.strip()
    parsed = urlsplit(link)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        if parsed.scheme in ("mailto", "tel", "data"):
            return None
        raise ValueError(f"Unsupported link scheme in {page}: {link}")
    if parsed.netloc and parsed.netloc not in ("futseyi.github.io",):
        return None
    if not parsed.path and not parsed.netloc:
        target = page
    else:
        relative_page = "/" + page.relative_to(ROOT).as_posix()
        absolute_path = unquote(urlsplit(urljoin(ORIGIN + relative_page, link)).path)
        target = ROOT / absolute_path.lstrip("/")
        if target.is_dir() or absolute_path.endswith("/"):
            target /= "index.html"
    resolved = target.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Path escapes site root: {link}")
    return resolved, unquote(parsed.fragment)


def main():
    assert (ROOT / "index.html").is_file(), "Missing homepage"
    assert (ROOT / "blog/index.html").is_file(), "Missing Writing index"
    assert (ROOT / "blog/posts.json").is_file(), "Missing Writing feed"
    assert (ROOT / "pagefind/pagefind.js").is_file(), "Missing search index"
    assert (ROOT / "assets/icons/favicon.svg").is_file(), "Missing favicon"

    pages = {}
    for file in ROOT.rglob("*.html"):
        parsed = Page()
        html = file.read_text(encoding="utf-8")
        assert version_assets(html, ROOT) == html, f"Stale shared asset version: {file}"
        parsed.feed(html)
        pages[file.resolve()] = parsed

    errors = []
    for post_page in (ROOT / "blog").glob("*/index.html"):
        html = post_page.read_text(encoding="utf-8")
        name = post_page.relative_to(ROOT)
        language = re.search(r'<html\s+lang="([^"]+)"', html)
        if not language or language.group(1) not in ("en", "zh-CN"):
            errors.append(f"{name}: unsupported page language")
        if len(re.findall(r"<h1(?:\s|>)", html)) != 1:
            errors.append(f"{name}: expected exactly one H1")
        body = re.search(r'<article class="article">(.*?)</article>', html, re.S)
        if body:
            article = body.group(1)
            if re.search(r"<h1(?:\s|>)", article):
                errors.append(f"{name}: H1 inside article body")
            if re.search(r"<pre(?:\s|>)", article) and not re.search(r"<code(?:\s|>)", article):
                errors.append(f"{name}: code block missing code element")
            if article.count('<table>') != article.count('class="article-table"'):
                errors.append(f"{name}: table missing scroll wrapper")
            for image in re.findall(r'<img\b[^>]*>', article):
                if 'loading="lazy"' not in image or 'decoding="async"' not in image:
                    errors.append(f"{name}: image missing native loading hints")
        else:
            errors.append(f"{name}: article body missing")
        for anchor in re.findall(r'<details class="article-toc-inline">.*?</details>', html, re.S):
            for target in re.findall(r'href="#([^"]+)"', anchor):
                if target not in pages[post_page.resolve()].ids:
                    errors.append(f"{name}: missing inline TOC target #{target}")
    count = 0
    for file, parsed in pages.items():
        for link in parsed.links:
            count += 1
            try:
                result = local_target(file, link)
                if result is None:
                    continue
                target, fragment = result
                if not target.is_file():
                    errors.append(f"{file.relative_to(ROOT)}: missing {link}")
                elif fragment and target in pages and fragment not in pages[target].ids:
                    errors.append(f"{file.relative_to(ROOT)}: missing anchor {link}")
            except ValueError as error:
                errors.append(str(error))

    posts = json.loads((ROOT / "blog/posts.json").read_text(encoding="utf-8"))
    assert isinstance(posts, list), "Post index is not a list"
    slugs = set()
    for post in posts:
        slug = post["slug"]
        if slug in slugs:
            errors.append(f"Duplicate post slug: {slug}")
        slugs.add(slug)
        if not (ROOT / "blog" / slug / "index.html").is_file():
            errors.append(f"Missing HTML for post: {slug}")

    xml = ElementTree.parse(ROOT / "sitemap.xml")
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for loc in xml.findall(f".//{ns}loc"):
        result = local_target((ROOT / "index.html").resolve(), loc.text or "")
        if result is None or not result[0].is_file():
            errors.append(f"Invalid sitemap URL: {loc.text}")

    if errors:
        raise SystemExit("Static site verification failed:\n" + "\n".join(errors))
    print(f"Verified {len(pages)} HTML pages, {len(posts)} posts, {count} references and sitemap.")


if __name__ == "__main__":
    main()
