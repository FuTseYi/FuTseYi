#!/usr/bin/env python3
"""Render the Git-owned contribution snapshot; never fetch data during builds."""
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "contributions.json"
OUTPUT = ROOT / "_site/contributions.json"
START = "<!-- CONTRIBUTIONS:START -->"
END = "<!-- CONTRIBUTIONS:END -->"
REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
EXCLUDED_REPOSITORIES = {"futseyi/futseyi.github.io", "futseyi/futseyi"}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Contribution timestamp must be a string")
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Contribution timestamp requires a timezone")
    return date.astimezone(timezone.utc)


def validate_snapshot(snapshot):
    """Reject missing, malformed, duplicate, and future-dated records."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("entries"), list):
        raise ValueError("Invalid contribution snapshot")
    if timestamp(snapshot.get("updated_at")) > datetime.now(timezone.utc):
        raise ValueError("Future contribution snapshot timestamp")
    names = set()
    for item in snapshot["entries"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("Invalid contribution entry")
        name = item["name"]
        if (not REPO_NAME.fullmatch(name) or name.lower() in EXCLUDED_REPOSITORIES
                or any(part in (".", "..") for part in name.split("/"))):
            raise ValueError("Invalid or excluded contribution repository")
        if name.lower() in names:
            raise ValueError("Duplicate contribution repository")
        names.add(name.lower())
        if timestamp(item.get("date")) > datetime.now(timezone.utc):
            raise ValueError("Future contribution date")
        for key in ("activity", "description", "language"):
            if not isinstance(item.get(key), str):
                raise ValueError(f"Invalid contribution {key}")
    return snapshot


def render(snapshot):
    validate_snapshot(snapshot)
    rows = []
    for entry in snapshot["entries"]:
        name = entry["name"]
        dt = timestamp(entry["date"])
        description = f'<p>{escape(entry["description"])}</p>' if entry["description"] else ""
        tags = " · ".join(escape(value) for value in (entry["activity"], entry["language"]) if value)
        rows.append(f'<article class="project-item"><time class="contribution-date" datetime="{dt.date().isoformat()}">{dt:%Y.%m.%d}</time><div>'
                    f'<h3><a href="https://github.com/{name}" target="_blank" rel="noopener noreferrer">'
                    f'{escape(name)} <span class="link-arrow" aria-hidden="true"></span></a></h3>'
                    f'{description}<div class="project-tags"><span>{tags}</span></div></div></article>')
    if not rows:
        rows.append('<p class="section-lead">No verified public contributions available.</p>')
    updated = timestamp(snapshot["updated_at"])
    rows.append(f'<p class="activity-note">Activity snapshot · {updated:%Y.%m.%d} UTC</p>')
    return "\n".join(rows)


def main():
    snapshot = validate_snapshot(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    page = ROOT / "_site/index.html"
    html = page.read_text(encoding="utf-8")
    if html.count(START) != 1 or html.count(END) != 1:
        raise ValueError("Missing or duplicate contributions slot")
    html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                  lambda _: START + "\n" + render(snapshot) + "\n" + END, html, flags=re.S)
    page.write_text(html, encoding="utf-8")
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(snapshot['entries'])} public contribution repositories.")


if __name__ == "__main__":
    main()
