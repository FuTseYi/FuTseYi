# Local preview

Requires Python 3.10 or later.

```powershell
# Windows
py -3 preview.py
```

```sh
# macOS / Linux
python3 preview.py
```

Open <http://127.0.0.1:8765/> for the homepage or <http://127.0.0.1:8765/blog/> for the Blog. The preview builds the site, indexes search, checks links, and watches for changes. Refresh the browser after each successful rebuild; stop with Ctrl+C.

Build dependencies are declared in `requirements.txt`. On first use, the script installs them in a project-local `.venv` (or an already active virtual environment). When the current interpreter already satisfies the requirements, no virtual environment is created. Internet access and Python's `venv`/`pip` support are required. It does not install packages into the system Python.

The preview serves generated files from `_site/`. A failed rebuild leaves the last working preview available. Local links are adjusted only in the temporary build; repository source files are unchanged. Public contributions come from a recent snapshot when available, otherwise from GitHub.

Useful options:

- `--build-only` builds and validates the full site without serving it. No HTTP port is opened.
- `--refresh-activity` updates public GitHub contribution data during a build (used for production releases).
- `--port 8766` uses a different port if the default is occupied when serving.

Run only one preview process per checkout. The build and generated files are excluded from Git.

## Portable production builds

Run `python3 preview.py --build-only --refresh-activity` to reproduce the GitHub Pages build locally, or omit `--refresh-activity` to reuse the latest available activity snapshot. GitHub Pages and Vercel both publish the resulting `_site/` directory; generated output is not committed.

The homepage canonical URL in `index.html` is the production origin for generated blog pages, sitemap, robots sitemap declaration, README links and site validation. Internal navigation uses root-relative paths. A future custom domain or renamed/private source repository does not require changing the core generators; hosting access, DNS, and optional cross-repository README permissions are deployment settings.

## PR preview deployment

Vercel uses `vercel.json` to build `_site/` for GitHub pull requests; the `main` branch is not deployed there. Its isolated build installs the same `requirements.txt` dependencies using a version-pinned uv installer without requiring the host Python's `ensurepip`. The resulting preview is marked `noindex`. GitHub Pages remains the production host.

## Publishing an article

Create `posts/my-note/index.md`:

```markdown
---
title: My note
date: 2026-10-28
tags: Notes, Website
---

Article text goes here.
```

`title` and `date` are required; `tags` and `lang` (`zh-CN` or `en`) are optional. The frontmatter title is the sole page H1; body headings render one level lower without changing their source anchors. Every post is published when its changes reach `main`; dates control display order, not publication scheduling.

Put images and other files in `posts/my-note/assets/`, referencing them as `assets/example.webp`. Describe informative images with meaningful alt text; use empty alt text only for decorative images. For a captioned image, use semantic HTML `<figure>` and `<figcaption>`. The folder name is the public URL slug (`/blog/my-note/`); keep it stable after publication.

The same push deploys the Blog and updates the website/Profile READMEs.

## Article regression checks

Run `python3 preview.py --build-only` (Windows: `py -3 preview.py --build-only`) before publishing layout or rendering changes. The existing build verification checks generated article language, one page-level H1, code markup, table scroll containers, image loading hints and in-page contents links, in addition to local links and the sitemap.

The static checks do not replace browser testing. Review a code-heavy post, an image-heavy post and a table-heavy post at narrow and wide widths, in light and dark themes. Verify keyboard access to the contents, code copying and image enlargement in a secure browser context before merging interaction changes.
