"""Regression tests for lifetime contribution preservation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from datetime import datetime, timezone
import sync_activity as activity
from scripts import refresh_contributions as refresh


def snapshot(entries):
    return {"updated_at": "2026-11-08T04:36:39+00:00", "entries": entries}


def entry(name, date="2026-01-01T00:00:00Z", activity_type="Commit"):
    return {"name": name, "date": date, "activity": activity_type,
            "description": "", "language": ""}


class ActivityTests(unittest.TestCase):
    def test_restored_history_has_full_coverage(self):
        source = Path(__file__).resolve().parents[1] / "contributions.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["entries"]), 29)
        self.assertIn("fmhy/edit", [item["name"] for item in data["entries"]])
        self.assertIn("datawhalechina/diy-llm", [item["name"] for item in data["entries"]])

    def test_partial_refresh_preserves_history(self):
        old = snapshot([entry(f"org/project{i}") for i in range(29)])
        new = snapshot([entry("org/project0", "2026-11-08T00:00:00Z", "Code push"),
                        entry("org/new", "2026-11-08T01:00:00Z", "Pull request")])
        result = activity.merge_snapshots(old, new)
        self.assertEqual(len(result["entries"]), 30)
        self.assertEqual(result["entries"][1]["name"], "org/project0")
        self.assertEqual(result["entries"][1]["activity"], "Code push")

    def test_case_insensitive_deduplication(self):
        result = activity.merge_snapshots(snapshot([entry("Org/Repo")]),
                                          snapshot([entry("org/repo", "2026-11-08T00:00:00Z")]))
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["name"], "org/repo")

    def test_graphql_history_merge_preserves_old_entries(self):
        old = [entry("fmhy/edit", "2025-01-01T00:00:00Z")]
        new = [entry("datawhalechina/diy-llm", "2026-11-01T00:00:00Z")]
        merged = refresh.merge(old + new)
        self.assertEqual({item["name"] for item in merged},
                         {"fmhy/edit", "datawhalechina/diy-llm"})

    def test_graphql_refresh_does_not_rewrite_unchanged_history(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "contributions.json"
            original = snapshot([entry("org/historical")])
            source.write_text(json.dumps(original), encoding="utf-8")
            before = source.read_bytes()
            with patch.object(refresh, "SNAPSHOT", source), \
                 patch.object(refresh, "collect", return_value=snapshot([entry("org/historical")])):
                refresh.main()
            self.assertEqual(source.read_bytes(), before)

    def test_graphql_refresh_rejects_empty_result(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "contributions.json"
            original = snapshot([entry("org/historical")])
            source.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(refresh, "SNAPSHOT", source), \
                 patch.object(refresh, "collect", return_value=snapshot([])):
                with self.assertRaisesRegex(RuntimeError, "empty"):
                    refresh.main()
            self.assertEqual(json.loads(source.read_text()), original)

    def test_source_is_unchanged_after_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            (root / "_site/index.html").write_text(activity.START + activity.END, encoding="utf-8")
            original = snapshot([entry(f"org/project{i}") for i in range(29)])
            source = root / "contributions.json"
            source.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", source), \
                 patch.object(activity, "OUTPUT", root / "_site/contributions.json"), \
                 patch.object(activity, "collect", return_value=snapshot([entry("org/new")])):
                with patch("sys.argv", ["sync_activity.py", "--refresh"]):
                    activity.main()
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), original)
            self.assertEqual(len(json.loads((root / "_site/contributions.json").read_text())["entries"]), 30)

    def test_api_failure_retains_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            (root / "_site/index.html").write_text(activity.START + activity.END, encoding="utf-8")
            source = root / "contributions.json"
            source.write_text(json.dumps(snapshot([entry("org/historical")])), encoding="utf-8")
            with patch.object(activity, "ROOT", root), patch.object(activity, "SNAPSHOT", source), \
                 patch.object(activity, "OUTPUT", root / "_site/contributions.json"), \
                 patch.object(activity, "collect", side_effect=URLError("offline")), \
                 patch("sys.argv", ["sync_activity.py", "--refresh"]):
                activity.main()
            self.assertEqual(len(json.loads((root / "_site/contributions.json").read_text())["entries"]), 1)


if __name__ == "__main__":
    unittest.main()
