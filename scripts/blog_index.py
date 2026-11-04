#!/usr/bin/env python3
"""Generate or verify the lightweight editorial index for blog articles."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from post_metadata import post_tags, read_posts

ROOT = Path(__file__).resolve().parents[1]


def build_index(root: Path = ROOT) -> list[dict[str, object]]:
    """Read article metadata from the Markdown sources."""
    articles = []
    for slug, metadata, _ in read_posts(root):
        articles.append({
            "slug": slug,
            "title": metadata["title"],
            "date": metadata["date"],
            "tags": post_tags(metadata),
        })

    return articles


def render_index(root: Path = ROOT) -> str:
    return json.dumps(build_index(root), ensure_ascii=False, indent=2) + "\n"


def write_index(root: Path = ROOT) -> None:
    (root / "BLOG_INDEX.json").write_text(render_index(root), encoding="utf-8")


def check_index(root: Path = ROOT) -> None:
    path = root / "BLOG_INDEX.json"
    if not path.is_file():
        raise ValueError("Missing BLOG_INDEX.json; run python scripts/blog_index.py --write")
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"BLOG_INDEX.json contains invalid JSON: {error}") from error
    if current != build_index(root):
        raise ValueError("BLOG_INDEX.json is out of date; regenerate it with --write")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="Regenerate BLOG_INDEX.json")
    action.add_argument("--check", action="store_true", help="Check BLOG_INDEX.json against posts/")
    args = parser.parse_args()

    try:
        if args.write:
            write_index()
            print("Generated BLOG_INDEX.json")
        else:
            check_index()
            print("Verified BLOG_INDEX.json")
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
