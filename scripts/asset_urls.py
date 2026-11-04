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
    """Compatibility export for the homepage-owned canonical origin."""
    from site_metadata import site_url as canonical_site_url
    return canonical_site_url(root)
