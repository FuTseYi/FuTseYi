"""Read homepage-owned site data and render shared navigation/social metadata."""
from __future__ import annotations
import argparse
import mimetypes
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


SOCIAL_REQUIRED_META = (
    "og:site_name", "og:title", "og:description", "og:type", "og:url", "og:locale",
    "og:image", "og:image:type", "og:image:width", "og:image:height", "og:image:alt",
    "twitter:card", "twitter:site", "twitter:title", "twitter:description",
    "twitter:image", "twitter:image:alt",
)
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                 "meta", "param", "source", "track", "wbr"}


class HomepageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.lang = "en"
        self.portrait: dict[str, str] = {}
        self.portrait_depth = 0
        self.toc_entries: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "html":
            self.lang = attrs.get("lang", "en")
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key:
                self.meta[key] = attrs.get("content", "")
        if tag == "link" and "canonical" in attrs.get("rel", "").split():
            self.canonical = attrs.get("href", "")
        if tag == "section" and attrs.get("id") and attrs.get("data-toc-label"):
            self.toc_entries.append((attrs["id"], attrs["data-toc-label"]))
        if tag == "figure" and "portrait" in attrs.get("class", "").split():
            self.portrait_depth = 1
        elif self.portrait_depth and tag not in VOID_ELEMENTS:
            self.portrait_depth += 1
        if tag == "img" and self.portrait_depth and not self.portrait:
            self.portrait = attrs

    def handle_endtag(self, tag):
        if self.portrait_depth:
            self.portrait_depth -= 1


def _parse_homepage(root: Path) -> HomepageParser:
    source = root / "index.html"
    if not source.is_file():
        raise ValueError(f"{source}: missing homepage")
    parser = HomepageParser()
    parser.feed(source.read_text(encoding="utf-8"))
    return parser


def _validated_origin(canonical: str) -> str:
    """Validate the homepage canonical URL without reparsing its HTML."""
    if not canonical:
        raise ValueError("index.html: missing canonical URL")
    url = canonical.rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("index.html: canonical must be an HTTPS site origin")
    return url


def site_url(root: Path) -> str:
    """Return the HTTPS origin declared by the homepage canonical URL."""
    return _validated_origin(_parse_homepage(root).canonical)


def load_site_metadata(root: Path) -> dict:
    """Read shared identity and sharing data from the homepage and its About portrait."""
    parser = _parse_homepage(root)
    origin = _validated_origin(parser.canonical)
    portrait = parser.portrait
    if any(not portrait.get(key) for key in ("src", "alt", "width", "height")):
        raise ValueError("index.html: About portrait must define src, alt, width, and height")

    source = portrait["src"]
    parsed_source = urlsplit(source)
    if parsed_source.scheme or parsed_source.netloc:
        if parsed_source.netloc != urlsplit(origin).netloc or parsed_source.scheme != "https":
            raise ValueError("index.html: About portrait must use a local site asset")
        image_path = root / parsed_source.path.lstrip("/")
        image_url = source
    else:
        image_path = (root / parsed_source.path.lstrip("/")).resolve()
        if not image_path.is_relative_to(root.resolve()):
            raise ValueError("index.html: About portrait path escapes the site root")
        image_url = urljoin(origin + "/", source)

    if not image_path.is_file():
        raise ValueError(f"index.html: About portrait asset does not exist: {source}")
    image_type = mimetypes.guess_type(image_path.name)[0]
    if not image_type or not image_type.startswith("image/"):
        raise ValueError(f"index.html: unsupported About portrait type: {source}")

    values = parser.meta
    title = values.get("og:title", "").strip()
    description = values.get("description", "").strip()
    site_name = values.get("og:site_name", "").strip()
    twitter_site = values.get("twitter:site", "").strip()
    if not all((title, description, site_name, twitter_site)):
        raise ValueError("index.html: missing homepage title, description, site name, or X account")

    return {
        "origin": origin, "title": title, "description": description,
        "site_name": site_name, "twitter_site": twitter_site,
        "image": image_url, "image_type": image_type,
        "image_width": str(int(portrait["width"])),
        "image_height": str(int(portrait["height"])),
        "image_alt": portrait["alt"], "lang": parser.lang,
        "toc_entries": parser.toc_entries,
    }


def locale_for(lang: str) -> str:
    return "zh_CN" if lang.lower().startswith("zh") else "en_US"


def social_metadata_values(metadata: dict, title: str, description: str, url: str,
                           lang: str, social_type: str) -> dict[str, str]:
    return {
        "og:site_name": metadata["site_name"], "og:title": title,
        "og:description": description, "og:type": social_type, "og:url": url,
        "og:locale": locale_for(lang), "og:image": metadata["image"],
        "og:image:type": metadata["image_type"], "og:image:width": metadata["image_width"],
        "og:image:height": metadata["image_height"], "og:image:alt": metadata["image_alt"],
        "twitter:card": "summary", "twitter:site": metadata["twitter_site"],
        "twitter:title": title, "twitter:description": description,
        "twitter:image": metadata["image"], "twitter:image:alt": metadata["image_alt"],
    }


def render_social_metadata(metadata: dict, title: str, description: str, url: str,
                           lang: str, social_type: str = "website",
                           tags: list[str] | None = None) -> str:
    values = social_metadata_values(metadata, title, description, url, lang, social_type)
    lines = []
    for key, value in values.items():
        attribute = "name" if key.startswith("twitter:") else "property"
        lines.append(f'<meta {attribute}="{escape(key, quote=True)}" content="{escape(value, quote=True)}">')
    lines.extend(f'<meta property="article:tag" content="{escape(tag, quote=True)}">' for tag in tags or [])
    return "\n".join(lines)


def render_homepage(source_html: str, metadata: dict) -> str:
    social = render_social_metadata(
        metadata, metadata["title"], metadata["description"],
        metadata["origin"] + "/", metadata["lang"], "website",
    )
    source_html, count = re.subn(
        r"<!-- SOCIAL-METADATA:START -->.*?<!-- SOCIAL-METADATA:END -->",
        lambda _: "<!-- SOCIAL-METADATA:START -->\n" + social + "\n<!-- SOCIAL-METADATA:END -->",
        source_html, count=1, flags=re.S,
    )
    if count != 1:
        raise ValueError("index.html: expected one social metadata source block")

    toc = ['  <span class="toc-title">ON THIS PAGE</span>']
    for index, (section_id, label) in enumerate(metadata["toc_entries"]):
        active = ' class="is-active" aria-current="location"' if index == 0 else ""
        toc.append(f'  <a href="#{escape(section_id, quote=True)}"{active}>{escape(label)}</a>')
    if not metadata["toc_entries"]:
        raise ValueError("index.html: no sections declare data-toc-label")
    source_html, count = re.subn(
        r'(<nav class="page-toc"[^>]*>).*?(</nav>)',
        lambda match: match[1] + "\n" + "\n".join(toc) + "\n" + match[2],
        source_html, count=1, flags=re.S,
    )
    if count != 1:
        raise ValueError("index.html: expected one homepage On This Page navigation")
    return source_html


def update_homepage(root: Path) -> None:
    metadata = load_site_metadata(root)
    output = root / "_site" / "index.html"
    if not output.is_file():
        raise ValueError(f"{output}: missing copied homepage")
    output.write_text(render_homepage(output.read_text(encoding="utf-8"), metadata), encoding="utf-8")
    print("Generated homepage social metadata and On This Page navigation.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-homepage", action="store_true")
    args = parser.parse_args()
    if not args.update_homepage:
        parser.error("choose --update-homepage")
    update_homepage(Path(__file__).resolve().parents[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
