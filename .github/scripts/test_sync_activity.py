"""Offline checks for public activity selection and build fallbacks."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import sync_activity as activity


def event(kind="PushEvent", repo="FuTseYi/example", day="27", **changes):
    item = {"type": kind, "public": True, "actor": {"login": "FuTseYi"},
            "repo": {"name": repo}, "created_at": f"2026-10-{day}T12:00:00Z",
            "payload": {"ref": "refs/heads/main"}}
    item.update(changes)
    return item


class ActivityTests(unittest.TestCase):
    def test_selection_uses_actor_and_latest_event_not_input_order(self):
        items = [event(day="20"), event(repo="org/other", day="25"), event(),
                 event(repo="private/repo", public=False),
                 event(repo="bot/repo", actor={"login": "bot"}),
                 event(kind="WatchEvent"), event(repo="tags/only", payload={"ref": "refs/tags/v1"})]
        selected = activity.select_events(items)
        self.assertEqual([item["name"] for item in selected], ["FuTseYi/example", "org/other"])
        self.assertEqual(selected[0]["date"], "2026-10-27T12:00:00Z")

    def test_pr_must_be_authored_non_draft_and_meaningful(self):
        payload = {"action": "opened", "pull_request": {"user": {"login": "FuTseYi"}, "draft": False}}
        good = event("PullRequestEvent", payload=payload)
        draft = copy.deepcopy(good)
        draft["payload"]["pull_request"]["draft"] = True
        other = copy.deepcopy(good)
        other["payload"]["pull_request"]["user"]["login"] = "someone-else"
        rejected = copy.deepcopy(good)
        rejected["payload"]["action"] = "closed"
        self.assertEqual(len(activity.select_events([good])), 1)
        self.assertEqual(activity.select_events([draft, other, rejected]), [])

    def test_collect_paginates_and_checks_repository_visibility(self):
        first = [event(repo=f"org/repo{i}") for i in range(100)]
        def fetch(url):
            if "&page=1" in url:
                return first
            if "&page=2" in url:
                return [event(repo="org/newest", day="28")]
            name = url.rsplit("/", 1)[1]
            return {"private": name == "newest", "archived": name == "repo0",
                    "description": "A <project>", "language": "Python"}
        with patch.object(activity, "fetch", side_effect=fetch):
            result = activity.collect()
        self.assertEqual(len(result["entries"]), activity.MAX_REPOSITORIES)
        self.assertNotIn("org/newest", [item["name"] for item in result["entries"]])
        self.assertNotIn("org/repo0", [item["name"] for item in result["entries"]])
        self.assertIn("&lt;project&gt;", activity.render(result))

    def test_api_failure_preserves_snapshot_and_missing_snapshot_keeps_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            page = root / "_site/index.html"
            source = activity.START + "source fallback" + activity.END
            snapshot = {"updated_at": "2026-10-28T00:00:00+00:00", "entries": []}
            cache = root / "_site/contributions.json"
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", cache), \
                    patch.object(activity, "fetch", side_effect=URLError("offline")), \
                    patch("sys.argv", ["sync_activity.py", "--refresh"]), contextlib.redirect_stdout(io.StringIO()):
                page.write_text(source, encoding="utf-8")
                activity.main()
                self.assertEqual(page.read_text(encoding="utf-8"), source)
                cache.write_text(json.dumps(snapshot), encoding="utf-8")
                activity.main()
                self.assertIn("No recent public", page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
