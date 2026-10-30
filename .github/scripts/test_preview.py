"""Offline checks for preview source watching and recovery."""
import contextlib
import importlib.util
import io
from http import HTTPStatus
from pathlib import Path
import subprocess
import tempfile
from threading import Event, Thread
import time
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
        with patch.object(preview.sys, "prefix", "venv"), \
                patch.object(preview.sys, "base_prefix", "system"), \
                patch.object(preview, "version", side_effect={"Markdown": "3.10.3", "pagefind": "1.5.2"}.get), \
                patch.object(preview.subprocess, "run") as install:
            preview.ensure_dependencies()
        install.assert_not_called()

    def test_existing_environment_with_dependencies_skips_installation(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(preview, "ROOT", Path(directory)), \
                patch.object(preview.sys, "platform", "win32"), \
                patch.object(preview.sys, "prefix", "system"), \
                patch.object(preview.sys, "base_prefix", "system"), \
                patch.object(preview.sys, "argv", ["preview.py"]), \
                patch.object(preview.venv, "EnvBuilder") as environment, \
                patch.object(preview.subprocess, "run") as check, \
                patch.object(preview.subprocess, "call", return_value=0) as restart, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            interpreter = Path(directory) / ".venv" / "Scripts/python.exe"
            interpreter.parent.mkdir(parents=True)
            interpreter.touch()
            check.return_value.returncode = 0
            with self.assertRaises(SystemExit) as result:
                preview.ensure_dependencies()
        self.assertEqual(result.exception.code, 0)
        environment.assert_not_called()
        check.assert_called_once_with([str(interpreter), str(Path(preview.__file__).resolve()), preview.CHECK_FLAG],
                                      capture_output=True)
        restart.assert_called_once()
        self.assertEqual(output.getvalue(), "")

    def test_successful_requests_are_not_logged_but_failures_are(self):
        handler = object.__new__(preview.PreviewHandler)
        with patch.object(preview.SimpleHTTPRequestHandler, "log_request") as logged:
            handler.log_request(200, "-")
            handler.log_request(304, "-")
            handler.log_request("-", "-")
            logged.assert_not_called()
            handler.log_request(404, "-")
            handler.log_request(HTTPStatus.NOT_FOUND, "-")
            handler.log_request(500, "-")
        self.assertEqual([call.args[0] for call in logged.call_args_list],
                         [404, HTTPStatus.NOT_FOUND, 500])

    def test_orphaned_build_directories_are_discarded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(preview, "ROOT", Path(directory)):
            root = Path(directory)
            orphan = root / ".preview-orphan" / "_site"
            orphan.mkdir(parents=True)
            (orphan / "index.html").write_text("stale")
            (root / ".previews-kept").mkdir()
            preview.discard_stale_builds()
            self.assertFalse((root / ".preview-orphan").exists())
            self.assertTrue((root / ".previews-kept").exists())

    def test_unusable_dependency_metadata_counts_as_missing(self):
        with patch.object(preview, "version", side_effect={"Markdown": "not-a-version", "pagefind": "1.5.2"}.get):
            self.assertFalse(preview.dependencies_valid())
        with patch.object(preview, "version", side_effect={"Markdown": "3.10.3", "pagefind": "1.4.0"}.get):
            self.assertFalse(preview.dependencies_valid())
        with patch.object(preview, "version", side_effect={"Markdown": "4.0.0", "pagefind": "1.5.2"}.get):
            self.assertFalse(preview.dependencies_valid())

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
                self.assertEqual(install.call_args_list[0].args[0],
                                 [str(interpreter), str(Path(preview.__file__).resolve()), preview.CHECK_FLAG])
                pip_calls = [call for call in install.call_args_list if "pip" in call.args[0]]
                self.assertEqual(len(pip_calls), 1)
                self.assertEqual(pip_calls[0].args[0], [str(interpreter), "-m", "pip", "install", *preview.REQUIREMENTS])
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
                patch.object(preview, "build", side_effect=[subprocess.CalledProcessError(1, "build"), (["2 articles"], [])]) as build, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(KeyboardInterrupt):
                preview.watch({})
        self.assertEqual(build.call_count, 2)
        self.assertIn("Build failed", output.getvalue())
        self.assertIn("Build complete", output.getvalue())
        self.assertIn("2 articles", output.getvalue())
        self.assertIn("Refresh your browser", output.getvalue())

    def test_build_output_is_reduced_to_counts_without_losing_warnings(self):
        log = "\n".join([
            "Blog: generated 30 article(s)",
            "Profile README already matches.",
            "Injected latest blog posts into deployed homepage.",
            "::warning::Public activity unavailable (HTTPError); retaining previous snapshot.",
            "Rendered 6 public contribution repositories.",
            "Verified 33 HTML pages, 30 posts, 1804 references and sitemap.",
            "",
        ])
        summary, notes = preview.summarize(log)
        self.assertEqual(summary, ["30 articles", "33 pages verified", "6 repositories"])
        self.assertEqual(notes, ["::warning::Public activity unavailable (HTTPError); retaining previous snapshot."])

    def test_unrecognized_output_without_counts_is_still_reported(self):
        summary, notes = preview.summarize("Something changed unexpectedly\n")
        self.assertEqual(summary, [])
        self.assertEqual(notes, ["Something changed unexpectedly"])

    def test_colors_are_omitted_when_output_is_not_a_terminal(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(preview.paint("ok", preview.GREEN), "ok")

    def test_colors_wrap_text_when_the_terminal_supports_them(self):
        with patch.object(preview, "color_enabled", return_value=True):
            self.assertEqual(preview.paint("ok", preview.GREEN), "\033[32mok\033[0m")

    def test_progress_line_is_silent_when_output_is_redirected(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with preview.Progress("Building preview..."):
                time.sleep(0.05)
        self.assertEqual(output.getvalue(), "")

    def test_progress_line_animates_and_clears_on_a_terminal(self):
        class Terminal:
            def __init__(self):
                self.text = ""

            def isatty(self):
                return True

            def write(self, text):
                self.text += text

            def flush(self):
                pass

        terminal = Terminal()
        with patch.object(preview.sys, "stdout", terminal):
            with preview.Progress("Building preview..."):
                time.sleep(0.3)
        self.assertIn("Building preview...", terminal.text)
        frames = [part for part in terminal.text.split("\r") if part.strip()]
        self.assertTrue(all(part.endswith(" Building preview...") for part in frames))
        self.assertGreaterEqual(len(frames), 2)
        erased = terminal.text.split("\r")[-2]  # Spaces overwrite the finished spinner line.
        self.assertEqual(erased, " " * (len("Building preview...") + 4))

    def test_glyphs_fall_back_when_the_console_encoding_cannot_print_them(self):
        class Console:
            def __init__(self, encoding):
                self.encoding = encoding

        def mark(encoding, preferred, fallback):
            with patch.object(preview.sys, "stdout", Console(encoding)):
                return preview.mark(preferred, fallback)

        self.assertEqual(mark("gbk", "✓", "OK"), "OK")
        self.assertEqual(mark("gbk", "✗", "x"), "x")
        self.assertEqual(mark("gbk", "→", "->"), "→")  # GBK can print arrows and middle dots.
        self.assertEqual(mark("ascii", "→", "->"), "->")
        self.assertEqual(mark("ascii", "·", "-"), "-")
        self.assertEqual(mark("utf-8", "✓", "OK"), "✓")
        self.assertEqual(mark(None, "✓", "OK"), "OK")


if __name__ == "__main__":
    unittest.main()
