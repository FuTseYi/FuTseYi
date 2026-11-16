"""Markdown image ALT follows the same explicit-first, fallback-second contract as Description."""
import unittest
from html.parser import HTMLParser

import build


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attributes):
        if tag == "img":
            self.images.append(dict(attributes))


class ImageAltTests(unittest.TestCase):
    def render(self, source):
        parsed = Images()
        parsed.feed(build.markdown_parser().convert(source))
        return parsed.images

    def test_existing_markdown_alt_is_preserved(self):
        image, = self.render('![My precise screenshot](assets/rk3588-edge-ai.png)')
        self.assertEqual(image["alt"], "My precise screenshot")

    def test_filename_fallback_normalizes_hyphens_and_underscores(self):
        image, = self.render('![](assets/cloudflare_email-routing.webp)')
        self.assertEqual(image["alt"], "cloudflare email routing")

    def test_filename_supports_unicode_spaces_and_mixed_language(self):
        image, = self.render('![](assets/港科大-RK3588_测试结果.png)')
        self.assertEqual(image["alt"], "港科大 RK3588 测试结果")

    def test_filename_decodes_url_escapes_and_ignores_query_fragment(self):
        image, = self.render('![](assets/edge%20AI-workflow.png?v=1#zoom)')
        self.assertEqual(image["alt"], "edge AI workflow")

    def test_generic_filenames_receive_a_simple_fallback(self):
        image, = self.render('![](assets/IMG_1234.jpg)')
        self.assertEqual(image["alt"], "IMG 1234")

    def test_raw_html_explicit_empty_alt_remains_untouched(self):
        image, = self.render('<img src="assets/decorative-background.png" alt="">')
        self.assertEqual(image["alt"], "")

    def test_raw_html_without_alt_is_not_modified(self):
        image, = self.render('<img src="assets/custom-figure.png">')
        self.assertNotIn("alt", image)

    def test_markdown_fallback_escapes_special_characters(self):
        image, = self.render('![](assets/r%26d-design.png)')
        self.assertEqual(image["alt"], "r&d design")

    def test_parser_reuse_applies_fallback_across_articles(self):
        parser = build.markdown_parser()
        first, second = Images(), Images()
        first.feed(parser.convert('![](assets/first-image.png)'))
        parser.reset()
        second.feed(parser.convert('![Manual ALT](assets/second-image.png)'))
        self.assertEqual(first.images[0]["alt"], "first image")
        self.assertEqual(second.images[0]["alt"], "Manual ALT")


if __name__ == "__main__":
    unittest.main()
