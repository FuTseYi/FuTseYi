# Repository Guide

A lightweight static personal website built with HTML, CSS, JavaScript, and a Python-generated blog.

**Core principles: Every line of code should justify its existence. Define once. Reuse everywhere.**

Treat the site as one coherent system. Prefer sound architecture, consistent design, performance, accessibility, and long-term maintainability over isolated fixes or artificially small diffs.

## Architecture

- `index.html`: Homepage and source of shared header/footer markup for generated pages.
- `assets/css/style.css`: Shared presentation, themes, and responsive styles.
- `assets/js/site.js`: Navigation, themes, search, and page interactions.
- `assets/js/atmosphere.js`: WebGL atmosphere and reduced-motion behavior.
- `posts/<slug>/index.md`: Article source; keep accompanying media in each post's `assets/`.
- `scripts/`: Generation, synchronization, verification, and tests.
- `.github/workflows/`: Current CI, publication, and README synchronization adapters.
- `preview.py`: Shared local preview and verified static-build entry point.

See [PREVIEW.md](PREVIEW.md) for commands, publishing, and browser checks. Do not commit generated `blog/`, `_site/`, `sitemap.xml`, or activity snapshots.

## Engineering Principles

- Read relevant code, dependencies, and established behavior before editing; assess effects across pages, themes, devices, and workflows.
- Fix root causes. Reorganize inadequate implementations when warranted instead of stacking patches, overrides, or special cases.
- Establish one authoritative source for shared information, rules, configuration, and behavior. Reuse it or generate dependent outputs rather than maintaining parallel copies; prefer automatic propagation over repeated manual synchronization.
- Reuse implementations when their responsibilities and semantics genuinely match. Preserve intentional duplication when it improves clarity, isolation, or independence.
- Prefer the simplest effective design. Do not introduce abstractions, dependencies, or indirection merely to eliminate superficial repetition.
- Remove redundant or obsolete code when addressing related areas; avoid speculative abstractions, defensive complexity without evidence, and unrelated refactoring.
- Preserve existing functionality, accessibility, visual consistency, and compatibility unless explicitly changing them.
- Keep site generation portable. Treat hosts, deployment credentials, and optional integrations as replaceable adapters, not core build dependencies.

## Change Management

- Group work by coherent objectives. Use PRs when review, validation, or a durable engineering record is useful; use direct commits for routine, low-risk updates where permitted.
- Keep history meaningful; avoid fragmented PRs and procedural overhead. Verify before publishing and clean up merged temporary branches when appropriate.
- Follow explicit task instructions. Never rewrite shared history or discard existing work without authorization.

## Verification

- Match checks to the change's scope and risk; inspect affected code paths and report what was actually tested.
- For Python script changes: `python -m unittest discover -s scripts -p 'test_*.py' -v`.
- For site, asset, generation, or deployment changes: `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`).
- For relevant UI changes, review responsive layouts, light/dark modes, keyboard accessibility, browser navigation, and reduced-motion behavior.
- Confirm no obsolete implementation remains. Never claim a check passed unless it ran successfully.

## Documentation

Each document has one authoritative responsibility. Keep rules in their owning document and reference them elsewhere instead of maintaining parallel versions:

- `AGENTS.md` governs repository-wide engineering principles, architecture, change management, verification, and document boundaries.
- [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md) governs editorial purpose, writing, research, article metadata decisions, privacy, and content review.
- [PREVIEW.md](PREVIEW.md) explains development, preview, build, publishing, and operational procedures.
- `BLOG_INDEX.json` is a generated discovery index, not an independent source of editorial policy or article content.

When behavior, commands, or architecture change, update the implementation and the relevant owning guidance. Keep cross-document references concise and update them only when their meaning or destination changes. Do not duplicate instructions simply to make each document self-contained.

- Preserve homepage-to-README generation: edit source content rather than generated sections.
- Keep published claims factual and protect private information and credentials.

## Blog Content

- For tasks that create, edit, review, reorganize, or classify articles under `posts/`, read [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md) and [BLOG_INDEX.json](BLOG_INDEX.json) before making editorial decisions.
- Use the index for quick topic and tag discovery, then read relevant Markdown sources before relying on their details. The archive is context, not a limit on future subjects, formats, or depth.
- `BLOG_INDEX.json` is generated from Markdown sources. Never edit it manually; regenerate with `python scripts/blog_index.py --write` and verify with `python scripts/blog_index.py --check`.
- Website engineering tasks that do not touch blog content do not need to load the editorial guide. Mixed tasks must follow both documents within their respective scopes: repository engineering and verification follow this file; editorial decisions follow [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md).
- Follow explicit user instructions where applicable, without overriding factual accuracy, privacy, licensing, or publication safeguards.
