#!/usr/bin/env python3
"""Refresh Git-owned public contribution history using official GitHub GraphQL."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from sync_activity import EXCLUDED_REPOSITORIES, validate_snapshot

ROOT = Path(__file__).resolve().parents[1]
USER = "FuTseYi"
API = "https://api.github.com/graphql"
SNAPSHOT = ROOT / "contributions.json"
REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
  }
}
"""

# The latest contribution per repository and category is enough for the existing cards.
# GitHub bounds the number of repositories per collection; incomplete windows are split.
COLLECTION_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalRepositoriesWithContributedCommits
      totalRepositoriesWithContributedPullRequests
      totalRepositoriesWithContributedIssues
      totalRepositoriesWithContributedPullRequestReviews
      totalRepositoryContributions
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner visibility isFork description primaryLanguage { name } }
        contributions(first: 1, orderBy: {field: OCCURRED_AT, direction: DESC}) {
          nodes { occurredAt }
        }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner visibility isFork description primaryLanguage { name } }
        contributions(first: 1, orderBy: {direction: DESC}) {
          nodes { occurredAt }
        }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner visibility isFork description primaryLanguage { name } }
        contributions(first: 1, orderBy: {direction: DESC}) {
          nodes { occurredAt }
        }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner visibility isFork description primaryLanguage { name } }
        contributions(first: 1, orderBy: {direction: DESC}) {
          nodes { occurredAt }
        }
      }
      repositoryContributions(first: 100) {
        nodes {
          occurredAt
          repository { nameWithOwner visibility isFork description primaryLanguage { name } }
        }
      }
    }
  }
}
"""

KINDS = (
    ("commitContributionsByRepository", "totalRepositoriesWithContributedCommits", "Commit"),
    ("pullRequestContributionsByRepository", "totalRepositoriesWithContributedPullRequests", "Pull request"),
    ("issueContributionsByRepository", "totalRepositoriesWithContributedIssues", "Issue"),
    ("pullRequestReviewContributionsByRepository",
     "totalRepositoriesWithContributedPullRequestReviews", "Review"),
)


def query(document, **variables):
    """One authenticated GitHub API transport; no token in published assets."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN is required for official contribution history")
    request = Request(API, data=json.dumps({"query": document, "variables": variables}).encode(),
                      headers={"Authorization": "Bearer " + token,
                               "Content-Type": "application/json",
                               "Accept": "application/vnd.github+json",
                               "User-Agent": "FuTseYi-homepage"})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise ValueError("GitHub GraphQL: " + result["errors"][0].get("message", "query failed"))
    return result["data"]["user"]


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone is required")
    return result.astimezone(timezone.utc)


def valid_name(name):
    return (isinstance(name, str) and bool(REPO_NAME.fullmatch(name))
            and name.lower() not in EXCLUDED_REPOSITORIES)


def contribution(repo, date, activity):
    if not repo or repo.get("visibility") != "PUBLIC":
        return None
    # Creating a fork is not an authored contribution by itself.
    if activity == "Repository" and repo.get("isFork"):
        return None
    name = repo.get("nameWithOwner")
    if not valid_name(name):
        return None
    return {"name": name, "date": date, "activity": activity,
            "description": repo.get("description") or "",
            "language": (repo.get("primaryLanguage") or {}).get("name") or ""}


def merge(groups, now=None):
    """One latest personal contribution per repository, with no age or count cap."""
    now = now or datetime.now(timezone.utc)
    by_name = {}
    for entry in groups:
        name = entry.get("name")
        if not valid_name(name):
            continue
        date = timestamp(entry["date"])
        if date > now:
            continue
        key = name.lower()
        if key not in by_name or timestamp(by_name[key]["date"]) < date:
            by_name[key] = dict(entry)
    return sorted(by_name.values(),
                  key=lambda entry: (timestamp(entry["date"]), entry["name"].lower()),
                  reverse=True)


def windows(year, now):
    """A calendar year may be 366 days; split it into <=365-day API windows."""
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    finish = min(datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1), now)
    while start <= finish:
        end = min(start + timedelta(days=365) - timedelta(seconds=1), finish)
        yield start, end
        start = end + timedelta(seconds=1)


def collection(start, end):
    data = query(COLLECTION_QUERY, login=USER, **{"from": start.isoformat(), "to": end.isoformat()})
    rows = data["contributionsCollection"]
    # Do not mistake the API's repository cap for the user's lifetime total.
    overflow = any(rows[total] > len(rows[field]) for field, total, _ in KINDS)
    overflow |= rows["totalRepositoryContributions"] > len(rows["repositoryContributions"]["nodes"])
    if overflow:
        if end - start < timedelta(days=1):
            raise ValueError("GitHub contribution repository limit exceeded within one day")
        midpoint = start + (end - start) / 2
        return collection(start, midpoint) + collection(midpoint + timedelta(seconds=1), end)

    entries = []
    for field, _, label in KINDS:
        for group in rows[field]:
            nodes = group["contributions"]["nodes"]
            if nodes:
                entry = contribution(group["repository"], nodes[0]["occurredAt"], label)
                if entry:
                    entries.append(entry)
    for node in rows["repositoryContributions"]["nodes"]:
        if node:
            entry = contribution(node["repository"], node["occurredAt"], "Repository")
            if entry:
                entries.append(entry)
    return entries


def collect(now=None):
    now = now or datetime.now(timezone.utc)
    user = query(YEARS_QUERY, login=USER)
    years = sorted(set(user["contributionsCollection"]["contributionYears"]))
    entries = []
    for year in years:
        if year <= now.year:
            for start, end in windows(year, now):
                entries.extend(collection(start, end))
    return {"updated_at": now.isoformat(), "entries": merge(entries, now)}


def main():
    previous = validate_snapshot(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    fresh = collect()
    if not fresh["entries"]:
        raise RuntimeError("Refusing empty GraphQL contribution response")
    # Historical evidence remains in Git even if a later API query is incomplete.
    entries = merge(previous["entries"] + fresh["entries"])
    if entries == previous["entries"]:
        print("Contribution history unchanged")
        return
    fresh["entries"] = entries
    validate_snapshot(fresh)
    SNAPSHOT.write_text(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated contribution history: {len(fresh['entries'])} repositories")


if __name__ == "__main__":
    main()
