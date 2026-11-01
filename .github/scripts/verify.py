#!/usr/bin/env python3
"""Verify generated static pages and local references before deployment."""
from __future__ import annotations
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree
from asset_urls import version_assets, site_url

ROOT = Path(__file__).resolve().parents[2] / "_site"
ORIGIN = site_url(ROOT.parent)


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



class ArticleStructure(HTMLParser):
    """Inspect article markup without depending on exact HTML serialization."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.language = None
        self.h1_count = 0
        self.body_h1 = False
        self.article_found = False
        self.pre_count = 0
        self.pre_with_code = 0
        self.table_count = 0
        self.wrapped_table_count = 0
        self.image_errors = []
        self.toc_links = []
        self.pre_has_code = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        ancestors = [kind for _, kind in self.stack]
        classes = attrs.get("class", "").split()
        in_article = "article" in ancestors
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "h1":
            self.h1_count += 1
            self.body_h1 |= in_article
        if tag == "article" and "article" in classes:
            self.article_found = True
        if in_article:
            if tag == "pre":
                self.pre_count += 1
                self.pre_has_code.append(False)
            if tag == "code" and self.pre_has_code and "pre" in ancestors:
                self.pre_has_code[-1] = True
            if tag == "table":
                self.table_count += 1
                if "table-wrap" in ancestors:
                    self.wrapped_table_count += 1
            if tag == "img":
                if "alt" not in attrs:
                    self.image_errors.append("image missing alt attribute")
                if attrs.get("loading") != "lazy" or attrs.get("decoding") != "async":
                    self.image_errors.append("image missing native loading hints")
        if tag == "a" and "toc" in ancestors and attrs.get("href", "").startswith("#"):
            self.toc_links.append(attrs["href"][1:])
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            kind = ("article" if tag == "article" and "article" in classes else
                    "table-wrap" if "article-table" in classes else
                    "toc" if tag == "details" and "article-toc-inline" in classes else tag)
            self.stack.append((tag, kind))

    def handle_endtag(self, tag):
        if tag == "pre" and self.pre_has_code:
            self.pre_with_code += self.pre_has_code.pop()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def local_target(page: Path, link: str) -> tuple[Path, str] | None:
    link = link.strip()
    parsed = urlsplit(link)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        if parsed.scheme in ("mailto", "tel", "data"):
            return None
        raise ValueError(f"Unsupported link scheme in {page}: {link}")
    if parsed.netloc and parsed.netloc != urlsplit(ORIGIN).netloc:
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
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in (ROOT / "robots.txt").read_text(encoding="utf-8"), "Incorrect robots sitemap URL"

    pages = {}
    for file in ROOT.rglob("*.html"):
        parsed = Page()
        html = file.read_text(encoding="utf-8")
        assert version_assets(html, ROOT) == html, f"Stale shared asset version: {file}"
        parsed.feed(html)
        pages[file.resolve()] = parsed

    errors = []
    for post_page in (ROOT / "blog").glob("*/index.html"):
        if post_page.parent.name == "tags":
            continue
        html = post_page.read_text(encoding="utf-8")
        name = post_page.relative_to(ROOT)
        parsed = ArticleStructure()
        parsed.feed(html)
        if parsed.language not in ("en", "zh-CN"):
            errors.append(f"{name}: missing or unsupported page language")
        if parsed.h1_count != 1 or parsed.body_h1:
            errors.append(f"{name}: expected one page H1 and no H1 inside article")
        if not parsed.article_found:
            errors.append(f"{name}: article body missing")
        if parsed.pre_count != parsed.pre_with_code:
            errors.append(f"{name}: code block missing code element")
        if parsed.table_count != parsed.wrapped_table_count:
            errors.append(f"{name}: table missing scroll wrapper")
        if parsed.image_errors:
            errors.extend(f"{name}: {issue}" for issue in parsed.image_errors)
        for anchor in parsed.toc_links:
            if anchor not in pages[post_page.resolve()].ids:
                errors.append(f"{name}: missing inline TOC target #{anchor}")
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
