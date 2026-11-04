"""Content-address local CSS/JavaScript URLs without changing published routes."""
import hashlib
import re
from pathlib import Path


def version_assets(html: str, root: Path) -> str:
    def replace(match):
        digest = hashlib.sha256((root / match[3]).read_bytes()).hexdigest()[:12]
        return f'{match[1]}="{match[2]}?v={digest}"'

    return re.sub(r'(href|src)="((?:\.\./|\./|/)?(assets/(?:css|js)/[^"?#]+))(?:\?[^"\s]*)?"',
                  replace, html)
