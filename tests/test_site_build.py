import unittest
from scripts import site_build as preview


class SiteBuildTests(unittest.TestCase):
    def test_build_output_is_reduced_to_counts_without_losing_warnings(self):
        log = "\n".join([
            "Blog: generated 30 article(s)",
            "Profile README already matches.",
            "Injected latest blog posts into deployed homepage.",
            "::warning::Public activity unavailable (HTTPError); retaining previous snapshot.",
            "Rendered 6 public contribution repositories.",
            "Verified 33 HTML pages, 30 posts, 1804 references and sitemap.",
            "",
        ])
        summary, notes = preview.summarize(log)
        self.assertEqual(summary, ["30 篇文章 / articles", "33 个页面检查通过 / pages verified", "6 个贡献仓库 / contribution repositories"])
        self.assertEqual(notes, ["::warning::Public activity unavailable (HTTPError); retaining previous snapshot."])

    def test_unrecognized_output_without_counts_is_still_reported(self):
        summary, notes = preview.summarize("Something changed unexpectedly\n")
        self.assertEqual(summary, [])
        self.assertEqual(notes, ["Something changed unexpectedly"])
