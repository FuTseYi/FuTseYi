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

    def test_markdown_alt_uses_authored_text_or_filename(self):
        for source, alt in (
            ('![My precise screenshot](assets/example-image.png)', "My precise screenshot"),
            ('![](assets/sample_image-name.webp)', "sample image name"),
            ('![](assets/示例-image_结果.png)', "示例 image 结果"),
            ('![](assets/sample%20image-name.png?v=1#zoom)', "sample image name"),
            ('![](assets/IMG_1234.jpg)', "IMG 1234"),
            ('![](assets/r%26d-design.png)', "r&d design"),
        ):
            with self.subTest(source=source):
                image, = self.render(source)
                self.assertEqual(image["alt"], alt)

    def test_raw_html_explicit_empty_alt_remains_untouched(self):
        image, = self.render('<img src="assets/decorative-background.png" alt="">')
        self.assertEqual(image["alt"], "")

    def test_raw_html_without_alt_is_not_modified(self):
        image, = self.render('<img src="assets/custom-figure.png">')
        self.assertNotIn("alt", image)

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
