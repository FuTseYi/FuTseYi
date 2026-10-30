"""Chromium smoke checks for generated article interactions and responsive layout."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[2] / "_site"


def check(page, name, width):
    page.goto(f"http://127.0.0.1:8766/blog/{name}/", wait_until="networkidle")
    assert page.locator("article.article").count() == 1
    assert page.locator("h1").count() == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), f"Page overflow at {width}px"
    code = page.locator(".article-code")
    if code.count():
        assert code.first.locator("button.code-copy").count() == 1
        assert code.first.locator("pre").evaluate("(e) => e.scrollWidth >= e.clientWidth")
    if width < 1600:
        contents = page.locator(".article-toc-inline")
        if contents.count():
            assert contents.is_visible()
            contents.locator("summary").click()
            assert contents.locator("nav a").first.is_visible()
            contents.locator("summary").click()
    images = page.locator("article.article img[data-zoom]")
    if images.count():
        img = images.first
        img.scroll_into_view_if_needed()
        img.evaluate("(e) => e.decode()")
        original_box = img.bounding_box()
        for _ in range(3):
            img.click()
            dialog = page.locator("dialog.image-lightbox")
            assert dialog.evaluate("(el) => el.open")
            page.mouse.wheel(0, 200)
            assert dialog.evaluate("(el) => el.open"), "Scrolling must not close preview"
            page.keyboard.press("Escape")
            assert not dialog.evaluate("(el) => el.open")
            assert img.evaluate("(el) => document.activeElement === el")
        assert img.bounding_box() == original_box, "Opening preview must not shift article image"
    tables = page.locator(".article-table")
    if tables.count():
        assert tables.first.evaluate("(e) => getComputedStyle(e).overflowX === 'auto'")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8766), partial(SimpleHTTPRequestHandler, directory=str(SITE)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            for width in (390, 1024, 1700):
                for theme in ("light", "dark"):
                    context = browser.new_context(viewport={"width": width, "height": 850}, reduced_motion="reduce")
                    context.add_init_script(f"localStorage.setItem('site-theme', '{theme}')")
                    page = context.new_page()
                    for slug in ("astro-waline-comments", "pytorch-quickstart-neural-networks", "hkust-elpa-serverless-github-native-cms"):
                        check(page, slug, width)
                    context.close()
            context = browser.new_context(viewport={"width": 390, "height": 850}, java_script_enabled=False)
            page = context.new_page()
            page.goto("http://127.0.0.1:8766/blog/astro-waline-comments/")
            pre = page.locator("article.article pre").first
            assert pre.is_visible()
            assert pre.evaluate("(e) => getComputedStyle(e).borderTopStyle !== 'none'")
            context.close()
            context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            page.goto("http://127.0.0.1:8766/blog/astro-waline-comments/")
            copy = page.locator(".code-copy").first
            assert copy.count() == 1
            expected = page.locator(".article-code").first.locator("pre").inner_text()
            copy.click()
            actual = page.evaluate("navigator.clipboard.readText()")
            assert actual.strip() == expected.strip()
            context.close()
            browser.close()
            print("Chromium article smoke checks passed: responsive, themes, contents, zoom, tables, no-JS, clipboard.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
