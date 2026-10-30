"""Offline checks for preview source watching and recovery."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("preview", Path(__file__).resolve().parents[2] / "preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def preview_root(self, root):
        for name in ("assets", "posts", ".github/scripts", "_site"):
            (root / name).mkdir(parents=True)
        (root / "index.html").write_text("source")
        (root / "robots.txt").write_text("robots")
        (root / "_site/index.html").write_text("last good build")

    def test_failed_build_keeps_last_good_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.preview_root(root)
            with patch.object(preview, "ROOT", root), patch.object(preview, "SITE", root / "_site"), \
                    patch.object(preview, "assemble", side_effect=ValueError("invalid post")):
                with self.assertRaises(ValueError):
                    preview.build()
            self.assertEqual((root / "_site/index.html").read_text(), "last good build")
            self.assertEqual(list(root.glob(".preview-*")), [])

    def test_publish_waits_for_readers_and_replaces_stale_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.preview_root(root)
            (root / "_site/stale.txt").write_text("old resource")
            ready = Event()
            errors = []

            def assemble(candidate):
                (candidate / "_site").mkdir(exist_ok=True)
                (candidate / "_site/index.html").write_text("new build")
                ready.set()

            def build():
                try:
                    preview.build()
                except Exception as error:
                    errors.append(error)

            with patch.object(preview, "ROOT", root), patch.object(preview, "SITE", root / "_site"), \
                    patch.object(preview, "assemble", side_effect=assemble):
                worker = Thread(target=build)
                try:
                    with preview.SERVING_LOCK:
                        worker.start()
                        self.assertTrue(ready.wait(2))
                        self.assertEqual((root / "_site/index.html").read_text(), "last good build")
                finally:
                    worker.join(3)
                self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual((root / "_site/index.html").read_text(), "new build")
            self.assertFalse((root / "_site/stale.txt").exists())
            self.assertEqual(list(root.glob(".preview-*")), [])

    def test_installed_dependencies_need_no_setup(self):
        with patch.object(preview, "version", side_effect={"Markdown": "3.10.3", "pagefind": "1.5.2"}.get), \
                patch.object(preview.subprocess, "run") as install:
            preview.ensure_dependencies()
        install.assert_not_called()

    def test_missing_dependencies_bootstrap_platform_specific_environment(self):
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
                    preview.ensure_dependencies()
                self.assertEqual(result.exception.code, 0)
                interpreter = Path(directory) / ".venv" / executable
                environment.return_value.create.assert_called_once_with(Path(directory) / ".venv")
                install.assert_called_once_with([str(interpreter), "-m", "pip", "install", "Markdown>=3.7,<4", "pagefind[extended]==1.5.2"], check=True)
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
            for filename in ("posts/new/index.md", "posts/new/assets/image.png", "assets/css/style.css", ".github/scripts/build.py", "robots.txt"):
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
