"""Offline checks for public activity selection and build fallbacks."""
import contextlib
import copy
import io
import json
from datetime import datetime, timedelta, timezone
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
    def test_personal_repositories_are_excluded_case_insensitively(self):
        items = [event(repo="FuTseYi/FuTseYi"), event(repo="FUTSEYI/futseyi.github.io"), event()]
        self.assertEqual([entry["name"] for entry in activity.select_events(items)], ["FuTseYi/example"])

    def test_refresh_policy_and_failure_keeps_timestamp(self):
        for age, force, fail in ((1, False, False), (25, False, False),
                                 (1, True, False), (25, False, True), (1, True, True)):
            with self.subTest(age=age, force=force, fail=fail), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "_site").mkdir()
                page = root / "_site/index.html"
                page.write_text(activity.START + "fallback" + activity.END, encoding="utf-8")
                cache = root / "_site/contributions.json"
                old = {"updated_at": (datetime.now(timezone.utc) - timedelta(hours=age)).isoformat(), "entries": []}
                fresh = {"updated_at": datetime.now(timezone.utc).isoformat(), "entries": []}
                cache.write_text(json.dumps(old), encoding="utf-8")
                with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", cache), \
                        patch.object(activity, "fetch") as fetch, \
                        patch.object(activity, "collect", side_effect=URLError("offline") if fail else None,
                                     return_value=fresh) as collect, \
                        patch("sys.argv", ["sync_activity.py"] + (["--refresh"] if force else [])), \
                        contextlib.redirect_stdout(io.StringIO()):
                    activity.main()
                fetch.assert_not_called()
                self.assertEqual(collect.call_count, int(force))
                expected = fresh if force and not fail else old
                self.assertEqual(json.loads(cache.read_text(encoding="utf-8")), expected)

    def test_missing_snapshot_bootstraps_from_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            page = root / "_site/index.html"
            page.write_text(activity.START + "fallback" + activity.END, encoding="utf-8")
            cache = root / "_site/contributions.json"
            fresh = {"updated_at": datetime.now(timezone.utc).isoformat(), "entries": []}
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", cache), \
                    patch.object(activity, "fetch", side_effect=URLError("404")), \
                    patch.object(activity, "collect", return_value=fresh) as collect, \
                    patch("sys.argv", ["sync_activity.py"]), contextlib.redirect_stdout(io.StringIO()):
                activity.main()
            collect.assert_called_once()
            self.assertEqual(json.loads(cache.read_text(encoding="utf-8")), fresh)

    def test_invalid_local_snapshot_uses_remote_and_filters_old_personal_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "contributions.json"
            cache.write_text('{broken', encoding="utf-8")
            snapshot = {"updated_at": "2026-01-01T00:00:00Z", "entries": [
                {"name": "FuTseYi/FuTseYi"}, {"name": "FuTseYi/futseyi.github.io"}]}
            with patch.object(activity, "SNAPSHOT", cache), patch.object(activity, "fetch", return_value=snapshot):
                self.assertEqual(activity.previous_snapshot()["entries"], [])

    def test_invalid_snapshot_is_not_published_when_all_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            page = root / "_site/index.html"
            source = activity.START + "fallback" + activity.END
            page.write_text(source, encoding="utf-8")
            cache = root / "_site/contributions.json"
            cache.write_text('{broken', encoding="utf-8")
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", cache), \
                    patch.object(activity, "fetch", side_effect=URLError("offline")), \
                    patch("sys.argv", ["sync_activity.py"]), contextlib.redirect_stdout(io.StringIO()):
                activity.main()
            self.assertFalse(cache.exists())
            self.assertEqual(page.read_text(encoding="utf-8"), source)

    def test_fresh_deployed_snapshot_seeds_local_without_api_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            page = root / "_site/index.html"
            page.write_text(activity.START + "fallback" + activity.END, encoding="utf-8")
            cache = root / "_site/contributions.json"
            snapshot = {"updated_at": datetime.now(timezone.utc).isoformat(), "entries": []}
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", cache), \
                    patch.object(activity, "fetch", return_value=snapshot) as fetch, \
                    patch.object(activity, "collect") as collect, \
                    patch("sys.argv", ["sync_activity.py"]), contextlib.redirect_stdout(io.StringIO()):
                activity.main()
            fetch.assert_called_once_with(activity.SITE + "/contributions.json")
            collect.assert_not_called()
            self.assertEqual(json.loads(cache.read_text(encoding="utf-8")), snapshot)

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
