#!/usr/bin/env python3
"""Render public development activity into the staged homepage. Standard library only."""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
USER = "FuTseYi"
SITE = "https://futseyi.github.io"
API = "https://api.github.com"
SNAPSHOT = ROOT / "_site/contributions.json"
START = "<!-- CONTRIBUTIONS:START -->"
END = "<!-- CONTRIBUTIONS:END -->"


def fetch(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "FuTseYi-homepage"}
    if url.startswith(API + "/"):
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def select_events(events):
    """Count only the user's public pushes and authored, non-draft PR contributions."""
    repos = {}
    for event in sorted(events, key=lambda item: item["created_at"], reverse=True):
        if not event.get("public") or event.get("actor", {}).get("login", "").lower() != USER.lower():
            continue
        kind = event.get("type")
        payload = event.get("payload", {})
        if kind == "PushEvent":
            if not payload.get("ref", "").startswith("refs/heads/"):
                continue
            label = "Code push"
        elif kind == "PullRequestEvent":
            pr = payload.get("pull_request", {})
            if (pr.get("user", {}).get("login", "").lower() != USER.lower()
                    or pr.get("draft")
                    or payload.get("action") not in ("opened", "reopened", "synchronize", "closed")
                    or (payload.get("action") == "closed" and not pr.get("merged"))):
                continue
            label = "Pull request"
        else:
            continue
        name = event.get("repo", {}).get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            continue
        if name not in repos:
            repos[name] = {"name": name, "date": event["created_at"], "activity": label}
    return list(repos.values())


def collect():
    events = []
    for page in range(1, 4):
        batch = fetch(f"{API}/users/{USER}/events/public?per_page=100&page={page}")
        events.extend(batch)
        if len(batch) < 100:
            break
    entries = []
    for event in select_events(events):
        try:
            repo = fetch(f"{API}/repos/{event['name']}")
        except HTTPError as error:
            if error.code == 404:
                continue
            raise
        if repo.get("private") or repo.get("visibility", "public") != "public" or repo.get("archived") or repo.get("disabled"):
            continue
        entries.append({**event, "description": repo.get("description") or "",
                        "language": repo.get("language") or ""})
        if len(entries) == 3:
            break
    return {"updated_at": datetime.now(timezone.utc).isoformat(), "entries": entries}


def previous_snapshot():
    if SNAPSHOT.exists():
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return fetch(SITE + "/contributions.json")


def render(snapshot):
    rows = []
    for i, entry in enumerate(snapshot["entries"], 1):
        name = entry["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("Invalid repository name")
        dt = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
        description = f'<p>{escape(entry["description"])}</p>' if entry["description"] else ""
        tags = " · ".join(escape(value) for value in (entry["activity"], entry["language"]) if value)
        rows.append(f'<article class="project-item"><span class="item-no">{i:02}</span><div>'
                    f'<h3><a href="https://github.com/{name}" target="_blank" rel="noopener noreferrer">'
                    f'{escape(name)} <span class="link-arrow" aria-hidden="true"></span></a></h3>'
                    f'{description}<div class="project-tags"><span>{tags}</span>'
                    f'<time datetime="{dt.date().isoformat()}">{dt:%Y.%m.%d}</time></div></div></article>')
    if not rows:
        rows.append('<p class="section-lead">No recent public code pushes or pull requests in the available activity window.</p>')
    updated = datetime.fromisoformat(snapshot["updated_at"].replace("Z", "+00:00"))
    rows.append(f'<p class="activity-note">Activity snapshot · {updated:%Y.%m.%d} UTC</p>')
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh public GitHub activity")
    args = parser.parse_args()
    page = ROOT / "_site/index.html"
    html = page.read_text(encoding="utf-8")
    if html.count(START) != 1 or html.count(END) != 1:
        raise ValueError("Missing or duplicate contributions slot")
    snapshot = None
    try:
        snapshot = collect() if args.refresh else previous_snapshot()
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        print(f"::warning::Public activity unavailable ({type(error).__name__}); retaining previous snapshot or source fallback.")
        if args.refresh:
            try:
                snapshot = previous_snapshot()
            except (HTTPError, URLError, TimeoutError, OSError, ValueError):
                pass
    if snapshot is None:
        return
    content = render(snapshot)
    html = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: START + "\n" + content + "\n" + END, html, flags=re.S)
    page.write_text(html, encoding="utf-8")
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(snapshot['entries'])} public contribution repositories.")


if __name__ == "__main__":
    main()
