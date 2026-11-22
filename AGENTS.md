# Repository Guide

Maintain a lightweight, portable static site.

## Ownership and boundaries

- **Source** (`FuTseYi/FuTseYi`) is authoritative for code, articles, configurations, and build logic.
- **Published** (`FuTseYi/FuTseYi.github.io`) contains only generated static output; never edit it directly. `PUBLISHED_README.md` becomes Published's `README.md`.
- `index.html` owns the homepage and shared page chrome. CSS and JavaScript own presentation and interaction. `preview.py` calls `scripts/site_build.py` to build and verify the site.
- Article content lives in `posts/<slug>/index.md`, with media in the adjacent `assets/`. Empty Markdown image alt text falls back to a readable filename stem. Preserve authored alt text, including decorative `alt=""` in raw HTML.
- `contributions.json` is the tracked, verified GitHub contribution snapshot used by the build.
- `BLOG_INDEX.json` is a tracked discovery index generated from Markdown metadata. Update via `python scripts/blog_index.py --write` and verify via `--check`; never edit JSON by hand.
- Do not commit generated `_site/`, `blog/`, `rss.xml`, or `sitemap.xml` to Source.
- The homepage canonical defines the public origin. Use `site_metadata.py` for URL mapping and keep hosting configuration in the publishing workflow.

## Engineering principles

- Inspect the relevant implementation before editing. Fix the cause in the source that owns the behavior and keep the change scoped.
- Reuse existing components and build paths. Give shared data and behavior one source when the responsibilities match.
- Respect existing behavior and user intent. Do not overwrite shared history or delete content without authorization.

## Change management and verification

- Report the checks actually run.
- Python logic: `python -m unittest discover -s tests -t . -p 'test_*.py' -v`.
- Local site build and artifact verification: `python preview.py --build-only`.
- UI changes: run the relevant Chromium and WebKit checks in [PREVIEW.md](PREVIEW.md#verification).
- Reuse existing checks. Add a focused regression test when they miss a concrete failure relevant to the change.
- Never publish secrets, private data, or unlicensed material.

## Document ownership

- [ARCHITECTURE.md](ARCHITECTURE.md): overview, repository topology, and the single authoritative publishing diagram.
- [PREVIEW.md](PREVIEW.md): executable development, testing, and operational steps.
- [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md): editorial policy, metadata, fact-checking, and blog index upkeep.
- [LICENSING.md](LICENSING.md): reuse rights and third-party attribution.
- [PUBLISHED_README.md](PUBLISHED_README.md): Published repository's generated notice.

For article work, start with [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md) and [BLOG_INDEX.json](BLOG_INDEX.json). The homepage, blog index, and GitHub Profile README share the article ordering from `scripts/post_metadata.py`. Maintain each rule in its owning document and link to it elsewhere.
