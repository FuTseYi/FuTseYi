"""Offline checks for preview source watching and recovery."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("preview", Path(__file__).resolve().parents[2] / "preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def test_installed_renderer_needs_no_setup(self):
        with patch.object(preview, "version", return_value="3.10.3"), \
                patch.object(preview.subprocess, "run") as install:
            preview.ensure_markdown()
        install.assert_not_called()

    def test_missing_renderer_bootstraps_platform_specific_environment(self):
        for platform, executable in (("win32", "Scripts/python.exe"), ("darwin", "bin/python"), ("linux", "bin/python")):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as directory, \
                    patch.object(preview, "ROOT", Path(directory)), \
                    patch.object(preview, "version", side_effect=preview.PackageNotFoundError), \
                    patch.object(preview.sys, "platform", platform), \
                    patch.object(preview.sys, "prefix", preview.sys.base_prefix), \
                    patch.object(preview.sys, "argv", ["preview.py", "--port", "8766"]), \
                    patch.object(preview.venv, "EnvBuilder") as environment, \
                    patch.object(preview.subprocess, "run") as install, \
                    patch.object(preview.subprocess, "call", return_value=0) as restart, \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    preview.ensure_markdown()
                self.assertEqual(result.exception.code, 0)
                interpreter = Path(directory) / ".venv" / executable
                environment.return_value.create.assert_called_once_with(Path(directory) / ".venv")
                install.assert_called_once_with([str(interpreter), "-m", "pip", "install", "Markdown>=3.7,<4"], check=True)
                self.assertEqual(restart.call_args.args[0][-2:], ["--port", "8766"])

    def test_source_changes_include_additions_deletions_but_not_outputs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(preview, "ROOT", Path(directory)):
            root = Path(directory)
            for folder in ("posts", "assets", ".github/scripts", "_site", "blog", ".venv", ".git"):
                (root / folder).mkdir(parents=True, exist_ok=True)
            (root / "index.html").write_text("home")
            original = preview.source_state()
            for filename in ("_site/index.html", "blog/index.html", "sitemap.xml", ".git/config", ".venv/test.py"):
                (root / filename).write_text("generated")
            self.assertEqual(preview.source_state(), original)
            for filename in ("posts/new.md", "assets/css/style.css", ".github/scripts/build.py", "robots.txt"):
                file = root / filename
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("source")
                added = preview.source_state()
                self.assertIn(file, added)
                file.write_text("changed source")
                self.assertNotEqual(preview.source_state(), added)
                file.unlink()
                self.assertEqual(preview.source_state(), original)

    def test_consecutive_saves_are_combined_and_changes_during_build_are_seen(self):
        states = [{"file": 1}, {"file": 2}, {"file": 2}, {"file": 3}, {"file": 3}]
        with patch.object(preview, "source_state", side_effect=states), \
                patch.object(preview.time, "sleep", side_effect=[None] * 5 + [KeyboardInterrupt]), \
                patch.object(preview, "rebuild") as rebuild:
            with self.assertRaises(KeyboardInterrupt):
                preview.watch({})
        self.assertEqual(rebuild.call_count, 2)

    def test_failed_build_does_not_stop_next_rebuild(self):
        with patch.object(preview, "source_state", side_effect=[{1: 1}, {1: 1}, {1: 2}, {1: 2}]), \
                patch.object(preview.time, "sleep", side_effect=[None] * 4 + [KeyboardInterrupt]), \
                patch.object(preview, "build", side_effect=[subprocess.CalledProcessError(1, "build"), None]) as build, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(KeyboardInterrupt):
                preview.watch({})
        self.assertEqual(build.call_count, 2)
        self.assertIn("Build failed", output.getvalue())
        self.assertIn("Build complete", output.getvalue())


if __name__ == "__main__":
    unittest.main()
