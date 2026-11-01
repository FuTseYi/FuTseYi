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
    atmosphere = page.locator(".atmosphere")
    if atmosphere.count():
        atmosphere.locator("canvas").wait_for(state="visible", timeout=5000)
        assert atmosphere.evaluate("(el) => el.classList.contains('is-ready')"), "WebGL atmosphere failed to render"
        assert atmosphere.evaluate("(el) => Math.abs(Number(getComputedStyle(el).opacity) - (document.documentElement.dataset.theme === 'dark' ? 0.68 : 1)) < 0.02"), "Atmosphere must match intended theme opacity"
        assert atmosphere.evaluate("(el) => getComputedStyle(el).pointerEvents === 'none'")

    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), f"Page overflow at {width}px"
    code = page.locator(".article-code")
    if code.count():
        assert code.first.locator("button.code-copy").count() == 1
        assert code.first.locator("pre").evaluate("(e) => e.scrollWidth >= e.clientWidth")
    if width < 1600:
        contents = page.locator(".article-toc-inline")
        if contents.count():
            assert contents.is_visible()
            toggle = contents.locator(".article-toc-toggle")
            panel = contents.locator(".article-toc-panel")
            assert toggle.get_attribute("aria-expanded") == "false"
            assert panel.get_attribute("inert") is not None
            toggle.click()
            assert toggle.get_attribute("aria-expanded") == "true"
            assert panel.get_attribute("inert") is None
            assert contents.locator("nav a").first.is_visible()
            toggle.click()
            assert toggle.get_attribute("aria-expanded") == "false"
            assert panel.get_attribute("inert") is not None
    images = page.locator("article.article img")
    if images.count():
        img = images.first
        img.scroll_into_view_if_needed()
        img.click()
        assert page.locator(".medium-zoom-overlay, .image-zoom-overlay, .image-lightbox").count() == 0
        assert img.evaluate("(e) => !e.hasAttribute('data-zoom') && getComputedStyle(e).cursor !== 'zoom-in'")
    tables = page.locator(".article-table")
    if tables.count():
        assert tables.first.evaluate("(e) => getComputedStyle(e).overflowX === 'auto'")



def check_site_navigation(page, width):
    page.goto("http://127.0.0.1:8766/", wait_until="networkidle")
    assert page.locator("h1").count() == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")

    theme = page.locator(".theme-control")
    assert theme.is_visible()
    initial = theme.get_attribute("data-mode")
    theme.click()
    assert theme.get_attribute("data-mode") != initial
    selected = theme.get_attribute("data-mode")
    assert page.evaluate("localStorage.getItem('site-theme')") == selected

    if width <= 860:
        toggle = page.locator(".nav-toggle")
        assert toggle.is_visible()
        assert toggle.get_attribute("aria-expanded") == "false"
        toggle.click()
        assert toggle.get_attribute("aria-expanded") == "true"
        assert page.locator("#primary-navigation").evaluate("(el) => !el.inert")
        page.keyboard.press("Escape")
        assert toggle.get_attribute("aria-expanded") == "false"
        assert page.locator("#primary-navigation").evaluate("(el) => el.inert")
        toggle.click()
        page.locator("#primary-navigation a[href='/blog/']").click()
    else:
        page.locator("#primary-navigation a[href='/blog/']").click()
    page.wait_for_url("**/blog/")
    assert page.locator(".blog-entry").count() > 0


def check_search(page):
    page.goto("http://127.0.0.1:8766/blog/", wait_until="networkidle")
    page.locator(".search-open").click()
    dialog = page.locator("#search-dialog")
    assert dialog.evaluate("(el) => el.open")
    search = page.locator("#blog-search")
    assert search.evaluate("(el) => document.activeElement === el")
    search.fill("PyTorch")
    result = page.locator("#search-results a")
    result.first.wait_for(timeout=15000)
    assert result.first.get_attribute("href").startswith("/blog/")
    page.keyboard.press("Escape")
    assert not dialog.evaluate("(el) => el.open")

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
                    check_site_navigation(page, width)
                    for slug in ("astro-waline-comments", "pytorch-quickstart-neural-networks", "hkust-elpa-serverless-github-native-cms"):
                        check(page, slug, width)
                    context.close()
            context = browser.new_context(viewport={"width": 1024, "height": 850}, reduced_motion="reduce")
            check_search(context.new_page())
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
            print("Chromium smoke checks passed: homepage navigation, mobile menu, search, themes, articles, no-JS, clipboard.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
