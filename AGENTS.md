# Repository Guide

**Every line of code should justify its existence. Define once. Reuse everywhere.**

Maintain this as a lightweight, portable static personal website. Favor correct architecture, accessibility, performance, consistency, and long-term maintainability over isolated patches or needless abstractions.

## Ownership and boundaries

- **Source** (`FuTseYi/FuTseYi-Site-Source`) is authoritative for code, articles, configurations, and build logic.
- **Published** (`FuTseYi/FuTseYi.github.io`) contains only generated static output; never edit it directly. `PUBLISHED_README.md` becomes Published's `README.md`.
- `index.html` owns the homepage and shared page chrome; `assets/css/style.css`, `assets/js/site.js`, and `assets/js/atmosphere.js` own presentation and interaction.
- `posts/<slug>/index.md` owns article content and its adjacent `assets/`; `scripts/site_build.py` orchestrates article generation, activity rendering, search indexing, and verification through `preview.py`.
- `contributions.json` is a **tracked, verified** GitHub contribution snapshot; do not confuse it with untracked generated site output.
- `BLOG_INDEX.json` is a tracked discovery index generated from Markdown metadata. Update via `python scripts/blog_index.py --write` and verify via `--check`; never edit JSON by hand.
- Do not commit generated `_site/`, `blog/`, or `sitemap.xml` to Source.

See [README.md](README.md) for the architecture and canonical flow; [PREVIEW.md](PREVIEW.md) for commands and operating procedures.

## Engineering principles

- Read the relevant implementation and established behavior before editing. Consider linked pages, themes, viewport sizes, accessibility, and workflows.
- Fix underlying causes. Refactor an inadequate design when necessary instead of layering overrides and special cases.
- Define shared data and behavior once where responsibilities truly match; avoid parallel hand-maintained sources. Do not abstract merely to eliminate superficial repetition.
- Keep framework and dependency choices deliberate. Preserve portable static output and treat hosting and credentials as deployment adapters.
- Remove obsolete code within the scope of a change; avoid speculative complexity or unrelated refactoring.
- Respect existing behavior and user intent. Do not overwrite shared history or delete content without authorization.

## Change management and verification

- Prefer one coherent change and meaningful commits/PRs over fragmented procedural work; verify before merging and report only checks that actually ran.
- Python logic: `python -m unittest discover -s tests -t . -p 'test_*.py' -v`.
- Site, assets, generation, or deployment: `python preview.py --build-only`.
- UI changes: inspect relevant responsive layouts, light/dark themes, keyboard use, reduced motion, and Chromium/WebKit regression checks.
- Preserve the distinction between Source's data snapshots and generated Published files. Never publish secrets, private data, or unlicensed material.

## Document ownership

- [README.md](README.md): overview, repository topology, and the single authoritative publishing diagram.
- [PREVIEW.md](PREVIEW.md): executable development, testing, and operational steps.
- [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md): editorial policy, metadata, fact-checking, and blog index upkeep.
- [LICENSING.md](LICENSING.md): reuse rights and third-party attribution.
- [PUBLISHED_README.md](PUBLISHED_README.md): Published repository's generated notice.

For an article task, read [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md) and [BLOG_INDEX.json](BLOG_INDEX.json), then consult the relevant Markdown sources. The homepage's Recent Blog and the GitHub Profile README must reuse the canonical `scripts/blog_index.py` ordering; do not build another independent index. Update only the document that owns a changed rule and link to it elsewhere.
