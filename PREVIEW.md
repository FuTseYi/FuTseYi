# Development & Preview

The website is built from source into a portable static directory, `_site/`. The current local preview uses Python 3.10 or newer.

## Getting Started

From the repository root:

```powershell
# Windows
py -3 preview.py
```

```sh
# macOS / Linux
python3 preview.py
```

Open <http://127.0.0.1:8765/> or <http://127.0.0.1:8765/blog/>. Saving a source file triggers a rebuild; refresh your browser to see the result. Stop with Ctrl+C, and run only one preview process per checkout.

Dependencies come from `requirements.txt`. If needed, the command installs them into a project-local `.venv` (or the active virtual environment), not the system Python. Initial setup requires internet access and working `venv`/`pip` support. The preview retains the previous successful build if a rebuild fails.

## Building & Output

```sh
python3 preview.py --build-only
python3 preview.py --build-only --refresh-activity
```

On Windows, substitute `py -3` for `python3`.

- `--build-only`: Generate and verify `_site/` without serving it.
- `--refresh-activity`: Fetch fresh public contribution data instead of reusing an available snapshot.
- `--port 8766`: Choose another local preview port.

The private source repository runs `preview.py` once on `main` pushes and twice-monthly scheduled refreshes. After tests and build verification, its publisher copies the complete `_site/` to the public `FuTseYi/futseyi.github.io` repository. GitHub Pages publishes that repository's root; Vercel serves the same root as a static site with no build command. PRs run validation only and never publish.

The publisher uses a GitHub App installation token limited to the public output repository with Contents write permission. Configure `PUBLISH_APP_ID` as a source-repository variable and `PUBLISH_APP_PRIVATE_KEY` as a source-repository secret. Install the App only on the output and profile repositories. Do not use a personal access token for site publishing. `build-info.json` in each release records the source commit and Actions run; the output repository's Git history preserves prior releases for rollback. The published `vercel.json` enables deployments only from `main`, so output-repository PR branches do not deploy. Before changing Pages or Vercel settings, verify the first output commit and keep the prior deployment available.
The Profile README synchronization workflow requests a separate short-lived token scoped to `FuTseYi/FuTseYi`. That repository must also be selected in the App installation before enabling this workflow.

The same build entry point is used for verification and the current publishing workflow. It generates the blog and search index, synchronizes staged homepage content, and checks the output. Generated `blog/`, `_site/`, and `sitemap.xml` are ignored by Git.

The canonical origin in `index.html` determines generated article URLs, sitemap entries, and profile README links. Internal navigation uses root-relative paths. Hosting, domain, and credential settings belong outside the portable build.

## Writing & Publishing

Create `posts/my-note/index.md`:

```markdown
---
title: My note
date: 2026-10-28
tags: Notes, Website
---

Article text goes here.
```

`title` and `date` are required; `tags` and `lang` (`zh-CN` or `en`) are optional. The article title becomes the page H1; headings in the body are shifted down one level while retaining their anchors. Dates determine display order, not scheduled publication.

Keep article media beside its source in `posts/my-note/assets/` and link to files such as `assets/example.webp`. Use meaningful alt text for informative images, empty alt text for decorative images, and `<figure>`/`<figcaption>` when a caption is needed. The folder name forms the public URL (`/blog/my-note/`), so avoid changing it after publishing.

Under the current workflows, relevant changes reaching source `main` publish the site and trigger GitHub profile README synchronization. The source repository's technical README is edited directly; `PUBLISHED_README.md` is copied into the public artifact as its README.

## Browser Verification

Run the build check above for site or publishing changes. The repository's PR workflow additionally runs Python unit tests and Chromium and WebKit browser smoke tests.

Static checks cover generated pages and links but cannot establish visual or interaction correctness. For relevant changes, verify narrow and wide layouts, both color themes, keyboard use, reduced motion, and direct page loads. Exercise same-page and cross-page links, browser Back/Forward, the mobile menu, Blog search, article contents, and code copying. Inspect representative image-, table-, and code-heavy articles when rendering changes.

## Implementation Notes

The generated blog reuses header/footer markup from `index.html`, while `style.css` and `site.js` serve the site as a whole. When Swup is available, same-origin navigation replaces `#main` while shared UI and the WebGL atmosphere remain mounted. Ordinary document navigation remains the fallback if Swup is unavailable.

Page-specific interactions in `site.js` must initialize for incoming content and clean up when that content is replaced. Review listeners, observers, timers, and dialogs for lifecycle leaks when changing navigation. Refer to the source for pinned dependency versions and implementation details rather than duplicating them here.

Preview, article, README, activity and browser regression checks live in `tests/`; generation and validation stay in `scripts/`. The homepage is edited directly in root `index.html`; generated blog pages reuse its header/footer. `scripts/site_build.py` owns this site's isolated content pipeline. No separate template directory or cross-repository runtime is required.
