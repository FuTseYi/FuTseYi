"""Chromium and WebKit regressions for generated content and navigation."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "_site"


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

    page.evaluate("""() => {
        window.__persistentHeader = document.querySelector('#site-header');
        window.__persistentCanvas = document.querySelector('.atmosphere canvas');
    }""")
    page.evaluate("""() => {
        window.__scrollHistory = [];
        window.addEventListener('scroll', () => window.__scrollHistory.push(window.scrollY), {passive: true});
    }""")
    page.evaluate("window.scrollTo({top: 700, behavior: 'instant'})")
    assert page.evaluate("window.scrollY > 100")
    page.locator('#site-header .brand').click()
    page.wait_for_function('window.scrollY < 2')
    assert page.evaluate("document.querySelector('#site-header') === window.__persistentHeader")
    if page.evaluate("!matchMedia('(prefers-reduced-motion: reduce)').matches"):
        assert page.evaluate("(window.__scrollHistory || []).some(y => y > 15 && y < 600)"), "Homepage logo must scroll smoothly instead of being overridden by navigation"
    page.evaluate("window.scrollTo({top: 700, behavior: 'instant'}); window.__scrollHistory = []")
    assert page.evaluate("window.scrollY > 100")
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
    page.locator(".blog-entry").first.wait_for()
    page.wait_for_function("window.scrollY < 2")
    assert page.evaluate("""() => {
        const samples = window.__scrollHistory || [];
        return !samples.some(y => y > 15 && y < 600);
    }"""), "Cross-page navigation visibly animated the scroll position"
    page.wait_for_function("""() => {
        const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
        return !document.documentElement.classList.contains('is-navigating') &&
            getComputedStyle(document.documentElement).scrollBehavior === (reduced ? 'auto' : 'smooth');
    }""")
    assert page.evaluate("""() => Boolean(window.Swup) &&
        document.querySelector('#site-header') === window.__persistentHeader &&
        document.querySelector('.atmosphere canvas') === window.__persistentCanvas
    """)
    if width <= 860:
        assert page.locator(".nav-toggle").get_attribute("aria-expanded") == "false"
    page.go_back()
    page.wait_for_url("http://127.0.0.1:8766/")
    page.locator("main h1").wait_for()
    assert page.evaluate("""() => !window.Swup || (
        document.querySelector('#site-header') === window.__persistentHeader &&
        document.querySelector('.atmosphere canvas') === window.__persistentCanvas
    )""")
    page.go_forward()
    page.wait_for_url("**/blog/")
    page.locator(".blog-entry").first.wait_for()
    assert page.evaluate("document.querySelector('#site-header') === window.__persistentHeader")
    for _ in range(2):
        page.locator("#site-header .brand").click()
        page.wait_for_url("http://127.0.0.1:8766/")
        page.locator("main h1").wait_for()
        page.evaluate("window.scrollTo({top: 700, behavior: 'instant'})")
        page.wait_for_function("window.scrollY > 100")
        page.evaluate("window.__scrollHistory = []")
        if width <= 860:
            page.locator(".nav-toggle").click()
        page.locator("#primary-navigation a[href='/blog/']").click()
        page.wait_for_url("**/blog/")
        page.locator(".blog-entry").first.wait_for()
        page.wait_for_function("window.scrollY < 2")
        assert page.evaluate("""() => !(window.__scrollHistory || []).some(y => y > 15 && y < 600)"""), "Repeated navigation animated the scroll position"


def check_contribution_year_expansion(page):
    page.goto("http://127.0.0.1:8766/", wait_until="networkidle")
    list_items = page.locator("#contribution-list .project-item")
    assert list_items.count() >= 29
    toggle = page.locator("#contribution-list + .list-toggle")
    assert toggle.count() == 1
    assert toggle.get_attribute("aria-expanded") == "false"
    assert toggle.inner_text() == "Show more · 2026"
    assert page.locator("#contribution-list .project-item:not([hidden])").count() == 3
    toggle.click()
    assert toggle.inner_text() == "Show more · 2025"
    assert toggle.get_attribute("data-has-more") == "true"
    assert page.locator("#contribution-list .project-item:not([hidden])").count() == 22
    toggle.click()
    assert toggle.inner_text() == "Show less"
    assert toggle.get_attribute("data-has-more") == "false"
    assert page.locator("#contribution-list .project-item:not([hidden])").count() >= 29
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "false"
    assert toggle.inner_text() == "Show more · 2026"
    assert page.locator("#contribution-list .project-item:not([hidden])").count() == 3


def check_search(page):
    page.goto("http://127.0.0.1:8766/blog/", wait_until="networkidle")
    page.locator(".search-open").click()
    dialog = page.locator("#search-dialog")
    assert dialog.evaluate("(el) => el.open")
    search = page.locator("#blog-search")
    assert search.evaluate("(el) => document.activeElement === el")
    assert not page.locator("#search-results").is_visible()
    assert not dialog.locator(".scroll-hint").is_visible()
    assert dialog.evaluate("(el) => el.getBoundingClientRect().height <= 58")
    search.fill("PyTorch")
    result = page.locator("#search-results a")
    result.first.wait_for(timeout=15000)
    assert result.first.get_attribute("href").startswith("/blog/")
    assert page.locator("#search-results").is_visible()
    assert page.locator(".search-summary").is_visible()
    assert page.locator("#search-results .link-label mark").first.inner_text() == "PyTorch"
    search.fill("GitHub README")
    page.locator("#search-results a").first.wait_for(timeout=15000)
    assert page.locator("#search-results a").first.locator(".link-label mark").all_inner_texts() == ["GitHub", "README"]
    search.fill("Anaconda")
    body_match = page.locator("#search-results .search-match mark").first
    body_match.wait_for(timeout=15000)
    assert "anaconda" in body_match.inner_text().casefold()
    page.keyboard.press("Escape")
    assert not dialog.evaluate("(el) => el.open")
    assert search.input_value() == ""
    assert not page.locator("#search-results").is_visible()
    page.keyboard.press("Control+k")
    assert dialog.evaluate("(el) => el.open")
    assert dialog.evaluate("(el) => el.getBoundingClientRect().height <= 58")
    dialog.locator(".search-close").click()
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
                    check_contribution_year_expansion(page)
                    for slug in ("astro-waline-comments", "pytorch-quickstart-neural-networks", "hkust-elpa-serverless-github-native-cms"):
                        check(page, slug, width)
                    context.close()
            context = browser.new_context(viewport={"width": 390, "height": 850}, reduced_motion="no-preference")
            check_site_navigation(context.new_page(), 390)
            context.close()
            context = browser.new_context(viewport={"width": 1024, "height": 850}, reduced_motion="reduce")
            check_search(context.new_page())
            context.close()
            context = browser.new_context(viewport={"width": 390, "height": 850}, reduced_motion="reduce")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for route in ("/#%E0%A4%A", "/blog/astro-waline-comments/#%E0%A4%A"):
                page.goto("http://127.0.0.1:8766" + route, wait_until="networkidle")
                assert page.locator("#site-header").count() == 1
            assert not errors, f"Malformed URL fragments must not break navigation: {errors}"
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
            assert actual.replace("\r\n", "\n").strip() == expected.strip()
            context.close()
            browser.close()
            # WebKit covers the mobile/desktop navigation and article path used by Safari.
            safari = playwright.webkit.launch(headless=True)
            try:
                for width in (390, 1024):
                    context = safari.new_context(viewport={"width": width, "height": 850},
                                                 reduced_motion="reduce")
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    check_site_navigation(page, width)
                    page.goto("http://127.0.0.1:8766/blog/astro-waline-comments/",
                              wait_until="networkidle")
                    assert page.locator("article.article").count() == 1
                    assert page.locator(".article-code button.code-copy").count() > 0
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
                    assert not errors, f"WebKit {width}px browser errors: {errors}"
                    context.close()
            finally:
                safari.close()
            print("Chromium and WebKit smoke checks passed: navigation, mobile layout, search, themes and articles.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
