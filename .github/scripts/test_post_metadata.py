"""Tests for the shared Markdown front-matter parser."""
import tempfile
import unittest
from pathlib import Path
from post_metadata import get_post, post_slug


class PostMetadataTests(unittest.TestCase):
    def test_parses_metadata_and_preserves_body(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.md"
            path.write_text('---\r\ntitle: "A title"\r\ndate: 2026-11-03\r\ntags: Notes, Python\r\n# comment\r\n---\r\n\nBody\n',
                            encoding="utf-8")
            metadata, body = get_post(path)
            self.assertEqual(metadata["title"], "A title")
            self.assertEqual(metadata["tags"], "Notes, Python")
            self.assertEqual(body, "\nBody\n")

    def test_rejects_missing_front_matter_and_invalid_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.md"
            path.write_text("No metadata", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing --- frontmatter"):
                get_post(path)
            path.write_text("---\ntitle: Valid\ndate: 2026-11-03\nbroken\n---\nBody", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid metadata line"):
                get_post(path)

    def test_requires_title_and_valid_iso_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.md"
            path.write_text("---\ndate: 2026-11-03\n---\nBody", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing title"):
                get_post(path)
            path.write_text("---\ntitle: Valid\ndate: not-a-date\n---\nBody", encoding="utf-8")
            with self.assertRaises(ValueError):
                get_post(path)

    def test_validates_article_slug(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(post_slug(Path(directory) / "good-slug" / "index.md"), "good-slug")
            with self.assertRaisesRegex(ValueError, "lowercase URL slug"):
                post_slug(Path(directory) / "Bad Slug" / "index.md")


if __name__ == "__main__":
    unittest.main()
