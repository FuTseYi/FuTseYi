"""Tests for the generated editorial index."""
import tempfile
import unittest
from pathlib import Path

from blog_index import ROOT, build_index, check_index, render_index, write_index


class BlogIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "posts").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def add_post(self, slug, title, day, tags):
        folder = self.root / "posts" / slug
        folder.mkdir()
        (folder / "index.md").write_text(
            f"---\ntitle: {title}\ndate: {day}\ntags: {tags}\n---\n\nArticle body.\n",
            encoding="utf-8",
        )

    def test_reads_metadata_and_sorts_articles(self):
        self.add_post("older", "Older article", "2026-10-01", "Notes, Python")
        self.add_post("newer", "Newer article", "2026-11-02", "Python, Notes, Python")
        self.assertEqual(build_index(self.root), [
            {"slug": "newer", "title": "Newer article", "date": "2026-11-02", "tags": ["Python", "Notes"]},
            {"slug": "older", "title": "Older article", "date": "2026-10-01", "tags": ["Notes", "Python"]},
        ])

    def test_index_is_deterministic_and_detects_stale_content(self):
        self.add_post("sample", "Sample", "2026-11-03", "Notes")
        self.assertEqual(render_index(self.root), render_index(self.root))
        write_index(self.root)
        check_index(self.root)
        (self.root / "posts" / "sample" / "index.md").write_text(
            "---\ntitle: Updated\ndate: 2026-11-03\ntags: Notes\n---\n\nArticle body.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "out of date"):
            check_index(self.root)

    def test_missing_or_invalid_index_is_reported(self):
        self.add_post("sample", "Sample", "2026-11-03", "Notes")
        with self.assertRaisesRegex(ValueError, "Missing BLOG_INDEX.json"):
            check_index(self.root)
        (self.root / "BLOG_INDEX.json").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            check_index(self.root)

    def test_repository_index_is_current(self):
        check_index(ROOT)

    def test_invalid_slug_is_rejected(self):
        self.add_post("Bad Slug", "Sample", "2026-11-03", "Notes")
        with self.assertRaisesRegex(ValueError, "invalid article slug"):
            build_index(self.root)


if __name__ == "__main__":
    unittest.main()
