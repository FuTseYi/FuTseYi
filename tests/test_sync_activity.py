"""Regression checks for a versioned, offline contribution pipeline."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_activity as activity
from scripts import refresh_contributions as refresh


def entry(name, date="2026-01-01T00:00:00Z", description=""):
    return {"name": name, "date": date, "activity": "Commit",
            "description": description, "language": "Python"}


def snapshot(entries):
    return {"updated_at": "2026-11-08T04:36:39+00:00", "entries": entries}


class ActivityTests(unittest.TestCase):
    def test_restored_history(self):
        data = json.loads((Path(__file__).resolve().parents[1] / "contributions.json").read_text(encoding="utf-8"))
        activity.validate_snapshot(data)
        self.assertGreaterEqual(len(data["entries"]), 29)
        self.assertIn("fmhy/edit", {x["name"] for x in data["entries"]})
        self.assertIn("datawhalechina/diy-llm", {x["name"] for x in data["entries"]})
        self.assertNotIn("futseyi/futseyi-site-source", {x["name"].lower() for x in data["entries"]})

    def test_schema_rejects_duplicate_names(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            activity.validate_snapshot(snapshot([entry("Org/Repo"), entry("org/repo")]))

    def test_schema_rejects_invalid_names(self):
        for name in ("../secret", "org/repo?bad", "FuTseYi/futseyi.github.io", "FuTseYi/FuTseYi-Site-Source"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                activity.validate_snapshot(snapshot([entry(name)]))

    def test_schema_rejects_naive_and_future_dates(self):
        for date in ("2026-01-01T00:00:00", "2999-01-01T00:00:00Z"):
            with self.subTest(date=date), self.assertRaises(ValueError):
                activity.validate_snapshot(snapshot([entry("org/repo", date)]))

    def test_schema_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            activity.validate_snapshot(snapshot([{"name": "org/repo", "date": "2026-01-01T00:00:00Z"}]))

    def test_render_escapes_untrusted_metadata(self):
        html = activity.render(snapshot([entry("org/repo", description="<script>alert(1)</script>")]))
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn('datetime="2026-01-01"', html)

    def test_offline_build_reads_canonical_snapshot_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            (root / "_site/index.html").write_text(activity.START + activity.END)
            original = snapshot([entry("org/repo")])
            (root / "contributions.json").write_text(json.dumps(original))
            with patch.object(activity, "ROOT", root), \
                 patch.object(activity, "SNAPSHOT", root / "contributions.json"), \
                 patch.object(activity, "OUTPUT", root / "_site/contributions.json"):
                activity.main()
            self.assertEqual(json.loads((root / "_site/contributions.json").read_text()), original)
            self.assertIn("org/repo", (root / "_site/index.html").read_text())

    def test_bad_snapshot_cannot_replace_generated_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            (root / "_site/index.html").write_text("last good build")
            (root / "contributions.json").write_text('{"entries":[]}')
            with patch.object(activity, "ROOT", root), \
                 patch.object(activity, "SNAPSHOT", root / "contributions.json"):
                with self.assertRaises(ValueError):
                    activity.main()
            self.assertEqual((root / "_site/index.html").read_text(), "last good build")

    def test_fork_creation_alone_is_not_a_contribution(self):
        fork = {"nameWithOwner": "FuTseYi/upstream-fork", "visibility": "PUBLIC",
                "isFork": True, "description": "", "primaryLanguage": None}
        self.assertIsNone(refresh.contribution(fork, "2026-11-08T00:00:00Z", "Repository"))
        for activity_type in ("Commit", "Pull request", "Issue", "Review"):
            with self.subTest(activity=activity_type):
                actual = refresh.contribution(fork, "2026-11-08T00:00:00Z", activity_type)
                self.assertEqual(actual["activity"], activity_type)
        original = {**fork, "isFork": False}
        self.assertEqual(refresh.contribution(original, "2026-11-08T00:00:00Z", "Repository")["activity"], "Repository")

    def test_canonical_snapshot_has_no_verified_fork_only_entries(self):
        path = Path(__file__).resolve().parents[1] / "contributions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        fork_only = {"FuTseYi/xianyu-auto-reply", "FuTseYi/edit", "FuTseYi/easy-vibe"}
        self.assertFalse(fork_only & {entry["name"] for entry in data["entries"]})
        self.assertIn("fmhy/edit", {entry["name"] for entry in data["entries"]})

    def test_site_source_is_filtered_from_graphql(self):
        repo = {"nameWithOwner": "FuTseYi/FuTseYi-Site-Source", "visibility": "PUBLIC",
                "isFork": False, "description": "", "primaryLanguage": None}
        self.assertIsNone(refresh.contribution(repo, "2026-11-08T00:00:00Z", "Commit"))
        self.assertEqual(refresh.merge([entry("FuTseYi/FuTseYi-Site-Source")]), [])

    def test_graphql_merge_preserves_history(self):
        original = entry("fmhy/edit", "2025-01-01T00:00:00Z")
        fresh = entry("datawhalechina/diy-llm", "2026-11-01T00:00:00Z")
        merged = refresh.merge([original, fresh])
        self.assertEqual({x["name"] for x in merged}, {"fmhy/edit", "datawhalechina/diy-llm"})

    def test_graphql_merge_deduplicates_case_insensitively(self):
        old = entry("Org/Repo", "2025-01-01T00:00:00Z")
        new = entry("org/repo", "2026-11-01T00:00:00Z")
        self.assertEqual([x["name"] for x in refresh.merge([old, new])], ["org/repo"])

    def test_graphql_no_change_does_not_rewrite_data(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "contributions.json"
            old = snapshot([entry("org/historical")])
            file.write_text(json.dumps(old))
            previous = file.read_bytes()
            with patch.object(refresh, "SNAPSHOT", file), \
                 patch.object(refresh, "collect", return_value=snapshot([entry("org/historical")])):
                refresh.main()
            self.assertEqual(file.read_bytes(), previous)

    def test_empty_graphql_result_cannot_erase_history(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "contributions.json"
            old = snapshot([entry("org/historical")])
            file.write_text(json.dumps(old))
            with patch.object(refresh, "SNAPSHOT", file), \
                 patch.object(refresh, "collect", return_value=snapshot([])):
                with self.assertRaisesRegex(RuntimeError, "empty"):
                    refresh.main()
            self.assertEqual(json.loads(file.read_text()), old)


if __name__ == "__main__":
    unittest.main()
