# Local preview

Requires Python 3.10 or later. Run these commands from the repository directory.

Windows:

```powershell
py -3 preview.py
```

macOS / Linux:

```sh
python3 preview.py
```

Open <http://127.0.0.1:8765/> or <http://127.0.0.1:8765/blog/>.
The same command builds, verifies, serves and watches the website. Refresh the
browser manually after the terminal reports a successful build. Press Ctrl+C to stop.

If a compatible Python-Markdown is missing, the script installs `Markdown>=3.7,<4`
into the active virtual environment, or creates a project-local `.venv` and restarts
itself there. Existing compatible installations require no download. First-time
setup requires network access and Python venv/pip support. Some Linux installations
need their distribution's `python3-venv` package installed first. System Python is
never modified by the automatic installer. Python itself must already be installed.

The watcher checks source HTML, `robots.txt`, Markdown posts, assets and Python
build scripts every half second, and rebuilds after a quiet scan to combine
consecutive saves. Added and deleted files are detected; generated files,
Git files and virtual environments are excluded. Build errors are reported
without stopping the watcher; fix the source and save again to retry.
The current preview stays available while a candidate is built and verified.
Only a successful candidate replaces `_site/`; failed builds leave the last good
preview intact. File serving and directory replacement are coordinated to avoid
Windows file-sharing errors.

The script copies source files into an automatically cleaned temporary directory,
builds the blog, stages the website, injects latest posts
and public activity, and verifies local links before serving. Local preview reuses the existing snapshot,
with the deployed JSON as a backup, and queries GitHub only if neither is valid.
Deployments always request fresh activity.
If a query fails, the previous snapshot and its timestamp are preserved; without
a valid snapshot, the static GitHub link remains available. Website and Profile
repository activity is excluded.

Only navigation links in the preview copy are converted from the production
origin to local paths. Source HTML and deployment behavior are unchanged.
Generated files remain ignored by Git. No README is generated or published.

Run one preview process per checkout. The port is checked before building, so a
second process using the same port exits without changing the preview. Use
`--port 8766` if another application occupies the default port, or `--build-only`
to build and verify without starting a server (stop the preview first).
Local responses disable browser caching; refresh manually after a successful build.

## Publishing articles

Create a file such as `posts/my-note/index.md`:

```markdown
---
title: My note
date: 2026-10-28
tags: Notes, Website
---

Article text goes here.
```

Only `title` and `date` are required; `tags` is optional. There is no description,
draft switch or date-based publication gate. All articles are published when you
push to `main` and deployment succeeds. Dates control display and newest-first
ordering; tags are metadata, not sorting rules. The same push triggers automatic
updates of both READMEs (Profile updates require the existing `PROFILE_README_TOKEN`).

Keep article resources in `posts/my-note/assets/` and reference them with relative
paths, for example `![Example](assets/example.webp)`. The directory name determines
the article URL (`/blog/my-note/`); keep it stable after publishing.
