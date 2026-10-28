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

The script builds the blog, stages the website in `_site/`, injects latest posts
and public activity, and verifies local links before serving. Activity snapshots
less than 24 hours old are reused; missing or older snapshots trigger a GitHub
query. The deployed snapshot is a backup when no valid local snapshot exists.
If a query fails, the previous snapshot and its timestamp are preserved; without
a valid snapshot, the static GitHub link remains available. Website and Profile
repository activity is excluded.

Only navigation links in the preview copy are converted from the production
origin to local paths. Source HTML and deployment behavior are unchanged.
Generated files remain ignored by Git. No README is generated or published.

Use `--port 8766` if the default port is occupied, or `--build-only` to build and
verify without starting a server.
