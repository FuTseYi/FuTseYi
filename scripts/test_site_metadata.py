"""Tests for homepage-owned identity, social metadata, and generated navigation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import site_metadata
from site_metadata import load_site_metadata, render_homepage, render_social_metadata, site_url

ROOT = Path(__file__).resolve().parents[1]


class SiteMetadataTests(unittest.TestCase):
    def test_repository_metadata_follows_about_portrait_and_sections(self):
        metadata = load_site_metadata(ROOT)
        self.assertEqual(metadata["image"], metadata["origin"] + "/assets/images/profile/me.jpg")
        self.assertEqual(metadata["image_alt"], "FuTseYi's profile photo")
        self.assertEqual([item[0] for item in metadata["toc_entries"]],
                         ["about", "recent-blog", "education", "active-in", "contributions"])

    def test_load_site_metadata_parses_homepage_only_once(self):
        with patch.object(site_metadata, "_parse_homepage",
                          wraps=site_metadata._parse_homepage) as parse:
            metadata = load_site_metadata(ROOT)
        self.assertEqual(metadata["origin"], site_url(ROOT))
        parse.assert_called_once_with(ROOT)

    def test_homepage_generation_uses_source_order_and_portrait(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "assets/images/profile/portrait.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"test")
            source = """<!doctype html><html lang="zh-CN"><head>
<meta name="description" content="A &amp; B">
<meta property="og:site_name" content="Example">
<meta property="og:title" content="Example Home">
<meta property="og:locale" content="en_US"><meta name="twitter:site" content="@example">
<!-- SOCIAL-METADATA:START --><meta property="og:title" content="stale"><!-- SOCIAL-METADATA:END -->
<link rel="canonical" href="https://example.org/"></head><body>
<figure class="portrait"><img src="assets/images/profile/portrait.png" alt="A portrait" width="600" height="900"></figure>
<section id="second" data-toc-label="Second"></section><section id="unlisted"></section>
<section id="first" data-toc-label="First"></section>
<nav class="page-toc" aria-label="On this page"><!-- generated --></nav></body></html>"""
            (root / "index.html").write_text(source, encoding="utf-8")
            metadata = load_site_metadata(root)
            generated = render_homepage(source, metadata)
            self.assertIn('content="https://example.org/assets/images/profile/portrait.png"', generated)
            self.assertIn('content="A portrait"', generated)
            self.assertLess(generated.index('href="#second"'), generated.index('href="#first"'))
            self.assertNotIn('href="#unlisted"', generated)
            self.assertIn('content="zh_CN"', generated)

    def test_canonical_origin_rejects_paths_and_non_https(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<link rel="canonical" href="https://example.org/subpath/">')
            with self.assertRaises(ValueError):
                site_url(root)
            (root / "index.html").write_text('<link rel="canonical" href="http://example.org/">')
            with self.assertRaises(ValueError):
                site_url(root)

    def test_social_metadata_is_shared_and_escaped(self):
        metadata = load_site_metadata(ROOT)
        rendered = render_social_metadata(metadata, 'A "quoted" title', "Description",
                                          metadata["origin"] + "/blog/test/", "en", "article",
                                          ["Python & Tools"])
        self.assertIn('content="A &quot;quoted&quot; title"', rendered)
        self.assertIn('content="Python &amp; Tools"', rendered)
        self.assertIn('name="twitter:card"', rendered)
        self.assertIn('property="og:image"', rendered)


if __name__ == "__main__":
    unittest.main()
