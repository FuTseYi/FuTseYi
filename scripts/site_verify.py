"""Verify local references in the complete static artifact before publication."""
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit


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


def verify(root):
    root = root.resolve()
    pages = {path: Page(path.read_text(encoding="utf-8")) for path in root.rglob("*.html")}
    if root / "index.html" not in pages:
        raise ValueError("Build did not produce index.html")
    for path, page in pages.items():
        route = "/" + path.relative_to(root).as_posix()
        for link in page.links:
            url = urlsplit(urljoin("https://preview.invalid" + route, link))
            if url.netloc != "preview.invalid" or url.scheme != "https":
                continue
            target = (root / unquote(url.path).lstrip("/")).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"{route}: path escapes artifact: {link}")
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                raise ValueError(f"{route}: missing local resource: {link}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"{route}: missing anchor: {link}")
    return len(pages)
