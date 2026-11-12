#!/usr/bin/env python3
"""Verify generated static pages and local references before deployment."""
from __future__ import annotations
import json
import re
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree
from asset_urls import version_assets
from site_metadata import site_url
from site_metadata import SOCIAL_REQUIRED_META, load_site_metadata
from sync_activity import START as ACTIVITY_START, END as ACTIVITY_END, render as render_activity

ROOT = Path(__file__).resolve().parents[1] / "_site"
ORIGIN = site_url(ROOT.parent)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.lang = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
        if tag == "link" and "canonical" in attrs.get("rel", "").split():
            self.meta["canonical"] = attrs.get("href", "")
        if tag == "link" and "alternate" in attrs.get("rel", "").split() and attrs.get("type") == "application/rss+xml":
            self.meta["rss"] = attrs.get("href", "")
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key:
                self.meta[key] = attrs.get("content", "")
                if key in ("og:image", "twitter:image") and self.meta[key]:
                    self.links.append(self.meta[key])
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
    assert (ROOT / "rss.xml").is_file(), "Missing RSS feed"
    assert not (ROOT / "rss").exists(), "Obsolete RSS page remains in site output"
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
    home_html = (ROOT / "index.html").read_text(encoding="utf-8")
    try:
        snapshot = json.loads((ROOT / "contributions.json").read_text(encoding="utf-8"))
        activity = render_activity(snapshot)
        section = re.search(re.escape(ACTIVITY_START) + r"(.*?)" + re.escape(ACTIVITY_END), home_html, re.S)
        if section is None or section[1].strip() != activity:
            errors.append("Homepage contributions do not match contributions.json")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(f"Invalid contributions.json: {error}")
    source_metadata = load_site_metadata(ROOT.parent)
    toc = re.search(r'<nav class="page-toc"[^>]*>(.*?)</nav>', home_html, re.S)
    actual_toc = re.findall(r'<a\s+href="#([^"]+)"[^>]*>(.*?)</a>', toc[1], re.S) if toc else []
    actual_toc = [(section_id, re.sub(r"<[^>]+>", "", label).strip()) for section_id, label in actual_toc]
    if actual_toc != source_metadata["toc_entries"]:
        errors.append(f"Homepage On This Page entries are {actual_toc}, expected {source_metadata['toc_entries']}")

    for file, parsed in pages.items():
        name = file.relative_to(ROOT)
        if urljoin(ORIGIN + "/", parsed.meta.get("rss", "")) != ORIGIN + "/rss.xml":
            errors.append(f"{name}: missing RSS auto-discovery")
        for key in SOCIAL_REQUIRED_META:
            if not parsed.meta.get(key):
                errors.append(f"{name}: missing social metadata {key}")
        if parsed.meta.get("og:image") != source_metadata["image"] or parsed.meta.get("twitter:image") != source_metadata["image"]:
            errors.append(f"{name}: social image does not follow the About portrait")
        for key, expected in (
            ("og:site_name", source_metadata["site_name"]),
            ("og:image:type", source_metadata["image_type"]),
            ("og:image:width", source_metadata["image_width"]),
            ("og:image:height", source_metadata["image_height"]),
            ("og:image:alt", source_metadata["image_alt"]),
            ("twitter:site", source_metadata["twitter_site"]),
            ("twitter:image:alt", source_metadata["image_alt"]),
        ):
            if parsed.meta.get(key) != expected:
                errors.append(f"{name}: {key} does not match homepage source data")
        if parsed.meta.get("og:title") != parsed.meta.get("twitter:title"):
            errors.append(f"{name}: Open Graph and X titles do not match")
        if parsed.meta.get("og:description") != parsed.meta.get("twitter:description") or parsed.meta.get("og:description") != parsed.meta.get("description"):
            errors.append(f"{name}: social descriptions do not match")
        if parsed.meta.get("og:url") != parsed.meta.get("canonical"):
            errors.append(f"{name}: social URL does not match the canonical URL")
        if parsed.meta.get("twitter:card") != "summary":
            errors.append(f"{name}: expected a summary card for the portrait image")
        if parsed.meta.get("og:type") not in ("website", "article"):
            errors.append(f"{name}: invalid Open Graph type")
        expected_locale = "zh_CN" if parsed.lang.lower().startswith("zh") else "en_US"
        if parsed.meta.get("og:locale") != expected_locale:
            errors.append(f"{name}: social locale does not match the page language")
        if file == (ROOT / "index.html").resolve():
            if parsed.meta.get("og:title") != source_metadata["title"] or parsed.meta.get("og:description") != source_metadata["description"]:
                errors.append("Homepage social title or description does not match its source metadata")
            if parsed.meta.get("og:url") != source_metadata["origin"] + "/" or parsed.meta.get("og:type") != "website":
                errors.append("Homepage social URL or Open Graph type is incorrect")
        elif len(name.parts) == 3 and name.parts[0] == "blog" and name.parts[1] != "tags":
            if parsed.meta.get("og:type") != "article":
                errors.append(f"{name}: article page Open Graph type must be article")

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

    rss = ElementTree.parse(ROOT / "rss.xml").getroot()
    if rss.tag != "rss" or rss.get("version") != "2.0":
        errors.append("RSS feed is not RSS 2.0")
    if rss.findtext("./channel/title") != source_metadata["site_name"] + " · Blog" or rss.findtext("./channel/description") != source_metadata["description"]:
        errors.append("RSS channel metadata differs from homepage")
    items = rss.findall("./channel/item")
    if len(items) != len(posts):
        errors.append("RSS item count does not match posts")
    for post, item in zip(posts, items):
        url = ORIGIN + post["url"]
        if item.findtext("link") != url or item.findtext("guid") != url:
            errors.append(f"RSS URL or GUID differs for {post['slug']}")
        if item.findtext("title") != post["title"] or parsedate_to_datetime(item.findtext("pubDate")).date().isoformat() != post["date"]:
            errors.append(f"RSS title or date differs for {post['slug']}")
        body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
        if not body:
            errors.append(f"RSS body missing for {post['slug']}")
        else:
            article = Page()
            article.feed(body)
            for link in article.links:
                if not urlsplit(link).scheme:
                    errors.append(f"RSS body has a relative link for {post['slug']}: {link}")

    xml = ElementTree.parse(ROOT / "sitemap.xml")
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for loc in xml.findall(f".//{ns}loc"):
        if loc.text == ORIGIN + "/rss/":
            errors.append("Obsolete RSS page remains in sitemap")
        result = local_target((ROOT / "index.html").resolve(), loc.text or "")
        if result is None or not result[0].is_file():
            errors.append(f"Invalid sitemap URL: {loc.text}")

    if errors:
        raise SystemExit("Static site verification failed:\n" + "\n".join(errors))
    print(f"Verified {len(pages)} HTML pages, {len(posts)} posts, {count} references and sitemap.")


if __name__ == "__main__":
    main()
