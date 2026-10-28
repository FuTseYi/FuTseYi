# Local preview

Requires Python 3.10 or later. Run these commands from the repository directory.

Windows:

```powershell
py -3 -m pip install "Markdown>=3.7,<4"
py -3 preview.py
```

macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "Markdown>=3.7,<4"
python3 preview.py
```

Open <http://127.0.0.1:8765/> or <http://127.0.0.1:8765/blog/>.
Press Ctrl+C to stop. Re-run the preview command after changing articles, HTML,
CSS or JavaScript; files are not watched automatically.

For automatic rebuilding, use `py -3 preview.py --watch` on Windows or
`python3 preview.py --watch` on macOS. Refresh the browser manually after the
terminal reports a successful build. No extra dependency is required.
The watcher checks source HTML, `robots.txt`, Markdown posts, assets and Python
build scripts every half second, and rebuilds after a quiet scan to combine
consecutive saves. Added and deleted files are detected; generated files,
Git files and virtual environments are excluded. Build errors are reported
without stopping the watcher; fix the source and save again to retry.
During rebuilding, the served files may be temporarily incomplete.
`--watch` cannot be combined with `--build-only`.

The script builds the blog, stages the website in `_site/`, injects latest posts
and public activity, and verifies local links before serving. Local preview reuses the existing snapshot,
with the deployed JSON as a backup, and queries GitHub only if neither is valid.
Deployments always request fresh activity.
If a query fails, the previous snapshot and its timestamp are preserved; without
a valid snapshot, the static GitHub link remains available. Website and Profile
repository activity is excluded.

Only navigation links in the preview copy are converted from the production
origin to local paths. Source HTML and deployment behavior are unchanged.
Generated files remain ignored by Git. No README is generated or published.

Use `--port 8766` if the default port is occupied, or `--build-only` to build and
verify without starting a server.
