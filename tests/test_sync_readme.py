"""Check that the profile README follows homepage content."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import sync_readme as sync


class ReadmeTests(unittest.TestCase):
    def test_profile_sync_writes_only_root_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text("Old profile\n", encoding="utf-8")
            architecture = root / "docs" / "ARCHITECTURE.md"
            architecture.parent.mkdir()
            architecture.write_text("Technical guide\n", encoding="utf-8")
            with patch.object(sync, "ROOT", root), \
                 patch.object(sys, "argv", ["sync_readme.py", "--sync-profile"]), \
                 patch.object(sync, "render", return_value="Profile content\n"):
                sync.main()
            self.assertEqual(readme.read_bytes(), b"Profile content\n")
            self.assertEqual(architecture.read_text(encoding="utf-8"), "Technical guide\n")

    def test_sections_and_profile_content_match_homepage(self):
        home = sync.read_home()
        result = sync.render()
        self.assertEqual([line for line in result.splitlines() if line.startswith("#")],
                         ["## About", "## Active In", "## Recent Blog"])
        for text in [*home["paragraphs"], home["languages"],
                     *home["quotes"], *home["links"]]:
            self.assertIn(text, result)
        for title, image in home["communities"]:
            self.assertIn(sync.community_row(title, image, sync.site_url()), result)
        for label in ("**Focus:**", "**Lang:**", "**Motto:**"):
            self.assertIn(label, result)
        for dt, _, _ in sync.read_post_entries():
            self.assertNotIn(dt.strftime("%Y.%m.%d"), result)
        ordered=["**Homepage**:",*home["paragraphs"],
                 home["languages"],home["motto_label"],
                 *home["quotes"],*home["links"],home["badge"],"## Active In","## Recent Blog"]
        positions=[result.index(text) for text in ordered]
        self.assertEqual(positions,sorted(positions))

    def test_markdown_preserves_emphasis_with_html_attributes(self):
        self.assertEqual(sync.md('<strong class="name">Name</strong> and <em>note</em>'),
                         '**Name** and *note*')

    def test_markdown_preserves_italics_in_link_labels(self):
        for tag in ("i", "em"):
            with self.subTest(tag=tag):
                self.assertEqual(sync.md(f'<a href="https://example.com/"><{tag}>Campus</{tag}></a>'),
                                 '[*Campus*](https://example.com/)')

    def test_markdown_preserves_nested_inline_formatting(self):
        self.assertEqual(
            sync.md("<em><a href='/about'><strong>A &amp; B</strong></a></em>"),
            f"*[**A & B**]({sync.site_url()}/about)*",
        )

    def test_website_urls_ignore_repository_name(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "NewOwner/NewOwner.github.io"}):
            result = sync.render()
        self.assertIn(f"**Homepage**: [{sync.site_url().split('://', 1)[-1]}]({sync.site_url()}/)", result)
        self.assertIn(f"{sync.site_url()}/blog/", result)
        self.assertIn(f"[RSS]({sync.site_url()}/rss.xml)", result)

    def test_local_website_url_follows_canonical(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / "index.html").write_text('<link rel="canonical" href="https://another.github.io/">')
            with patch.object(sync, "ROOT", root):
                self.assertEqual(sync.site_url(), "https://another.github.io")

    def test_recent_posts_use_shared_frontmatter_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = root / "posts" / "invalid" / "index.md"
            post.parent.mkdir(parents=True)
            post.write_text("---\ntitle: Invalid\ndate: 2099-01-01\nmalformed metadata\n---\nText",
                            encoding="utf-8")
            with patch.object(sync, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "Invalid metadata line"):
                    sync.read_post_entries()

    def test_recent_posts_share_the_canonical_editorial_index(self):
        from blog_index import build_index
        expected = [(sync.date.fromisoformat(item["date"]),item["slug"],item["title"])
                    for item in build_index(sync.ROOT)[:6]]
        self.assertEqual(sync.read_post_entries(), expected)

    def test_recent_posts_sort_by_date_without_publication_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "posts").mkdir()
            for i in range(1, 8):
                (root / "posts" / f"post-{i}").mkdir()
                (root / "posts" / f"post-{i}" / "index.md").write_text(
                    f"---\ntitle: Post {i}\ndate: 2099-01-0{i}\ndraft: {'true' if i == 5 else 'false'}\n---\nText", encoding="utf-8")
            with patch.object(sync, "ROOT", root):
                self.assertEqual([entry[1] for entry in sync.read_post_entries()],
                                 ["post-7", "post-6", "post-5", "post-4", "post-3", "post-2"])


if __name__ == "__main__":
    unittest.main()
