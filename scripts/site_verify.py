"""Verify local references in the complete static artifact before publication."""
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

from .site_metadata import site_url


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                raise ValueError(f"Duplicate HTML id: {attrs['id']}")
            self.ids.add(attrs["id"])
        for name in ("src", "href"):
            if attrs.get(name):
                self.links.append(attrs[name])
        if tag in ("img", "source") and attrs.get("srcset"):
            for candidate in attrs["srcset"].split(","):
                parts = candidate.strip().split()
                if parts:
                    self.links.append(parts[0])
        if tag == "meta" and (attrs.get("property") or attrs.get("name")) in ("og:image", "twitter:image"):
            if attrs.get("content"):
                self.links.append(attrs["content"])


def verify(root):
    root = root.resolve()
    origin = site_url(root)
    host = urlsplit(origin).netloc
    pages = {path: Page(path.read_text(encoding="utf-8")) for path in root.rglob("*.html")}
    if root / "index.html" not in pages:
        raise ValueError("Build did not produce index.html")
    for path, page in pages.items():
        route = "/" + path.relative_to(root).as_posix()
        for link in page.links:
            input_url = urlsplit(link)
            if input_url.scheme and input_url.scheme not in ("http", "https"):
                if input_url.scheme in ("mailto", "tel", "data"):
                    continue
                raise ValueError(f"{route}: unsupported URL scheme: {link}")
            url = urlsplit(urljoin(origin + route, link))
            if url.netloc != host:
                continue
            if url.scheme != "https":
                raise ValueError(f"{route}: non-HTTPS same-origin reference: {link}")
            target = (root / unquote(url.path).lstrip("/")).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"{route}: path escapes artifact: {link}")
            if target.is_dir() or url.path.endswith("/"):
                target /= "index.html"
            if not target.is_file():
                raise ValueError(f"{route}: missing local resource: {link}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"{route}: missing anchor: {link}")
    return len(pages)
