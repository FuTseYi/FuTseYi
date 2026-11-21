"""Shared parsing and validation for Markdown article front matter."""
from __future__ import annotations
import re
from datetime import date
from pathlib import Path


def get_post(path: Path) -> tuple[dict[str, str], str]:
    """Parse the repository's deliberately small, flat front-matter format."""
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", raw, re.S)
    if not match:
        raise ValueError(f"{path}: Missing --- frontmatter")
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}: Invalid metadata line {line!r}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("title", "date"):
        if not metadata.get(key):
            raise ValueError(f"{path}: Missing {key}")
    date.fromisoformat(metadata["date"])
    return metadata, raw[match.end():]


def post_slug(path: Path) -> str:
    """Return a valid lowercase URL slug for an article source path."""
    slug = path.parent.name
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(f"{path}: Post directory must be a lowercase URL slug")
    return slug


def read_posts(root: Path) -> list[tuple[str, dict[str, str], str]]:
    """Read and order article sources once for every publication consumer."""
    posts = [(post_slug(path), *get_post(path))
             for path in (root / "posts").glob("*/index.md")]
    return sorted(posts, key=lambda post: (post[1]["date"], post[0]), reverse=True)


def post_tags(metadata: dict[str, str]) -> list[str]:
    """Normalize article tags identically for discovery and rendered pages."""
    return list(dict.fromkeys(tag.strip() for tag in metadata.get("tags", "").split(",") if tag.strip()))
