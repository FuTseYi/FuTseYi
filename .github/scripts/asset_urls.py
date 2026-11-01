"""Version shared CSS and JavaScript from their contents at build time."""
import hashlib
import re
from pathlib import Path


def version_assets(html: str, root: Path) -> str:
    def replace(match):
        path = match[1]
        digest = hashlib.sha256((root / path).read_bytes()).hexdigest()[:12]
        return match[0].split('?')[0].rstrip('"') + f'?v={digest}"'

    return re.sub(r'(?:href|src)="/?(assets/(?:css/style\.css|js/(?:site|atmosphere)\.js))(?:\?[^"\s]*)?"',
                  replace, html)


def site_url(root: Path) -> str:
    """Read the production site origin from the homepage canonical URL."""
    from urllib.parse import urlsplit
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"',
                      (root / "index.html").read_text(encoding="utf-8"))
    if not match:
        raise ValueError("index.html: missing canonical URL")
    url = match[1].rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("index.html: canonical must be an HTTPS site origin")
    return url
