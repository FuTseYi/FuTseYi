(() => {
  const root = document.documentElement;
  const siteName = document.querySelector('meta[property="og:site_name"]')?.content;
  const sourceUrl = document.querySelector('.footer-brand')?.href;
  if (siteName && sourceUrl) {
    const styles = getComputedStyle(root);
    const accent = styles.getPropertyValue('--accent').trim();
    console.info(`%c ${siteName} %c ${sourceUrl}`,
      `background:${accent};color:${styles.getPropertyValue('--bg').trim()};font-weight:700;padding:5px 8px;border-radius:6px 0 0 6px`,
      `background:${styles.getPropertyValue('--accent-soft').trim()};color:${accent};padding:5px 8px;border-radius:0 6px 6px 0`);
  }
  const themeControl = document.querySelector('.theme-control');
  const themes = ['system', 'light', 'dark'];
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  const syncTheme = () => {
    const theme = root.dataset.theme || 'system';
    const next = themes[(themes.indexOf(theme) + 1) % themes.length];
    if (themeControl) {
      themeControl.dataset.mode = theme;
      themeControl.setAttribute('aria-label', `Color theme: ${theme}. Switch to ${next}`);
      themeControl.title = `${theme[0].toUpperCase() + theme.slice(1)} theme. Click for ${next}`;
    }
  };
  themeControl?.addEventListener('click', () => {
    const theme = themes[(themes.indexOf(root.dataset.theme || 'system') + 1) % themes.length];
    if (theme === 'system') delete root.dataset.theme;
    else root.dataset.theme = theme;
    try { localStorage.setItem('site-theme', theme); } catch {}
    syncTheme();
  });
  systemTheme.addEventListener('change', syncTheme);
  window.addEventListener('storage', (event) => {
    if (event.key !== 'site-theme' && event.key !== null) return;
    if (event.newValue === 'light' || event.newValue === 'dark') root.dataset.theme = event.newValue;
    else delete root.dataset.theme;
    syncTheme();
  });
  syncTheme();
  const hashTargetId = () => {
    try { return decodeURIComponent(location.hash.slice(1)); }
    catch { return ''; }
  };
  const currentYear = String(new Date().getFullYear());
  document.querySelectorAll('[data-current-year]').forEach((element) => {
    element.dateTime = currentYear;
    element.textContent = currentYear;
  });
  const header = document.getElementById('site-header');
  if (!header) return;
  header.classList.toggle('is-scrolled', window.scrollY > 6);
  const navigationProgress = document.createElement('div');
  navigationProgress.className = 'navigation-progress';
  navigationProgress.setAttribute('aria-hidden', 'true');
  document.body.prepend(navigationProgress);
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    if (link.origin === location.origin && (link.pathname !== location.pathname || link.search !== location.search)) {
      navigationProgress.classList.add('is-loading');
      // Swup owns menu closure for persistent visits; native navigation keeps its fallback.
      if (!window.Swup && header.classList.contains('menu-open')) {
        header.classList.add('nav-reset');
        setOpen(false);
      }
    }
  }, true);
  window.addEventListener('pageshow', () => {
    navigationProgress.classList.remove('is-loading');
    requestAnimationFrame(() => {
      header.classList.toggle('is-scrolled', window.scrollY > 6);
      header.classList.remove('nav-reset');
      requestAnimationFrame(() => document.documentElement.classList.add('is-ready'));
    });
  });
  const toggle = header.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-navigation');
  const setOpen = (open) => {
    header.classList.toggle('menu-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
    toggle?.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
    if (nav) nav.inert = window.innerWidth <= 860 && !open;
  };
  setOpen(false);
  toggle?.addEventListener('click', () => setOpen(!header.classList.contains('menu-open')));
  header.querySelector('.brand')?.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (location.pathname === '/' || location.pathname === '/index.html') {
      event.preventDefault();
      header.classList.add('nav-reset');
      setOpen(false);
      if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
      window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
      requestAnimationFrame(() => header.classList.remove('nav-reset'));
    }
  });
  nav?.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || (link.target && link.target !== '_self')) return;
    if (link.origin !== location.origin || link.pathname !== location.pathname || link.search !== location.search) return;
    setOpen(false);
    if (link.hash || window.scrollY < 1) return;
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  });
  window.addEventListener('pagehide', () => {
    header.classList.add('nav-reset');
    setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && header.classList.contains('menu-open')) {
      setOpen(false);
      toggle?.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (header.classList.contains('menu-open') && !header.contains(event.target)) setOpen(false);
  });
  window.addEventListener('resize', () => {
    setOpen(window.innerWidth <= 860 && header.classList.contains('menu-open'));
  }, { passive: true });

  const initPage = () => {
    const controller = new AbortController();
    const observers = [];
    const timers = new Set();
    const listen = (target, type, callback, options = {}) =>
      target.addEventListener(type, callback, { ...options, signal: controller.signal });
    const article = document.querySelector('.article');
    const readingProgress = article && document.createElement('div');
    if (readingProgress) {
      readingProgress.className = 'reading-progress';
      readingProgress.setAttribute('aria-hidden', 'true');
      document.body.prepend(readingProgress);
    }

    const addScrollHint = (content, container, isEnabled = () => true) => {
      const hint = document.createElement('div');
      hint.className = 'scroll-hint';
      hint.setAttribute('aria-hidden', 'true');
      container.append(hint);
      const syncHint = () => {
        hint.classList.toggle('is-visible', isEnabled() && content.scrollHeight - content.clientHeight - content.scrollTop > 2);
      };
      content.addEventListener('scroll', syncHint, { passive: true });
      const observer = new ResizeObserver(syncHint);
      observer.observe(content);
      observers.push(observer);
      return syncHint;
    };
    const scrollExpandedIntoView = (element) => {
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const overflow = element.getBoundingClientRect().bottom - (window.innerHeight - 24);
      if (overflow > 0) window.scrollBy({ top: overflow, behavior: 'smooth' });
    };
    const setupDisclosure = (container, toggleSelector, panelSelector, onChange) => {
      if (!container) return;
      const button = container.querySelector(toggleSelector);
      const panel = container.querySelector(panelSelector);
      const setOpen = (open) => {
        container.classList.toggle('is-open', open);
        button.setAttribute('aria-expanded', String(open));
        panel.inert = !open;
        onChange?.();
      };
      setOpen(false);
      button.addEventListener('click', () => setOpen(!container.classList.contains('is-open')));
      panel.addEventListener('transitionend', (event) => {
        if (event.target !== panel || event.propertyName !== 'grid-template-rows' || !container.classList.contains('is-open')) return;
        onChange?.();
        scrollExpandedIntoView(container);
      });
    };
    const inlineToc = document.querySelector('.article-toc-inline');
    if (inlineToc) {
      const syncInlineHint = addScrollHint(inlineToc.querySelector('nav'), inlineToc, () => inlineToc.classList.contains('is-open'));
      setupDisclosure(inlineToc, '.article-toc-toggle', '.article-toc-panel', syncInlineHint);
    }
    setupDisclosure(document.querySelector('.web-evolution'), '.web-evolution-toggle', '.web-evolution-panel');
    const toc = document.querySelector('.page-toc');
    const tocContent = toc && document.createElement('div');
    if (toc) {
      tocContent.className = 'toc-content';
      tocContent.append(...toc.childNodes);
      toc.append(tocContent);
      addScrollHint(tocContent, toc);
    }
    if (toc?.classList.contains('article-toc')) {
      const observer = new ResizeObserver(() => toc.style.setProperty('--toc-height', `${toc.offsetHeight}px`));
      observer.observe(toc);
      observers.push(observer);
    }
    const tocLinks = [...document.querySelectorAll('.page-toc a[href^="#"]')];
    const links = toc?.classList.contains('archive-toc') ? tocLinks : [...document.querySelectorAll('.nav-links a[href^="#"]'), ...tocLinks];
    const targets = [...new Set(links
      .map((link) => document.getElementById(decodeURIComponent(link.hash.slice(1))))
      .filter(Boolean))];
    let clickedTarget = null;
    const selectTarget = (id) => {
      const target = document.getElementById(id);
      if (!targets.includes(target)) {
        clickedTarget = null;
        schedule();
        return;
      }
      const offset = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      clickedTarget = { id, top: Math.max(0, Math.min(top, document.documentElement.scrollHeight - window.innerHeight)), settled: false };
      schedule();
    };
    links.forEach((link) => link.addEventListener('click', () => selectTarget(decodeURIComponent(link.hash.slice(1)))));
    const releaseTarget = () => { clickedTarget = null; schedule(); };
    listen(window, 'wheel', releaseTarget, { passive: true });
    listen(window, 'touchstart', releaseTarget, { passive: true });
    listen(document, 'keydown', (event) => {
      if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) releaseTarget();
    });
    let scheduled = false;
    const sync = () => {
      scheduled = false;
      if (controller.signal.aborted) return;
      if (readingProgress) {
        const remaining = document.documentElement.scrollHeight - window.innerHeight;
        readingProgress.style.transform = `scaleX(${remaining > 0 ? Math.max(0, Math.min(1, window.scrollY / remaining)) : 1})`;
      }
      header.classList.toggle('is-scrolled', window.scrollY > 6);
      if (!targets.length) return;
      const navHeight = header.getBoundingClientRect().height;
      const probe = window.scrollY + navHeight + 28;
      let active = targets[0].id;
      const ordered = [...targets].sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
      for (const el of ordered) {
        if (el.getBoundingClientRect().top + window.scrollY <= probe) active = el.id;
      }
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6) active = ordered[ordered.length - 1].id;
      // Keep the clicked section selected through smooth scrolling and bottom clamping.
      if (clickedTarget) {
        if (Math.abs(window.scrollY - clickedTarget.top) <= 2) clickedTarget.settled = true;
        else if (clickedTarget.settled) clickedTarget = null;
        if (clickedTarget) active = clickedTarget.id;
      }
      if (toc) {
        const visible = toc.classList.contains('article-toc') || (toc.classList.contains('archive-toc')
          ? targets[0].getBoundingClientRect().top <= navHeight + 28
          : targets[0].getBoundingClientRect().bottom <= navHeight + 28);
        toc.classList.toggle('is-visible', visible);
        toc.setAttribute('aria-hidden', String(!visible));
        toc.inert = !visible;
      }
      if (toc?.classList.contains('archive-toc')) {
        const period = clickedTarget?.id.replace(/^(year|month)-/, '');
        document.querySelectorAll('.blog-entry .post-date').forEach((date) => {
          date.classList.toggle('is-active', Boolean(period && date.dateTime.startsWith(`${period}-`)));
        });
      }
      tocLinks.forEach((link) => {
        const current = decodeURIComponent(link.hash.slice(1)) === active;
        const changed = current && !link.classList.contains('is-active');
        link.classList.toggle('is-active', current);
        if (current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
        if (changed && tocContent.clientHeight) {
          const item = link.getBoundingClientRect();
          const bounds = tocContent.getBoundingClientRect();
          if (item.top < bounds.top || item.bottom > bounds.bottom) {
            tocContent.scrollTop += item.top - bounds.top - (tocContent.clientHeight - item.height) / 2;
          }
        }
      });
    };
    const schedule = () => {
      if (!scheduled && !controller.signal.aborted) {
        scheduled = true;
        window.requestAnimationFrame(sync);
      }
    };
    listen(window, 'scroll', schedule, { passive: true });
    listen(window, 'resize', releaseTarget, { passive: true });
    listen(window, 'hashchange', () => selectTarget(hashTargetId()));
    if (location.hash) selectTarget(hashTargetId());
    else schedule();
    document.querySelectorAll('[data-expandable]').forEach((list) => {
      const extra = [...list.querySelectorAll(':scope > .project-item')].slice(3);
      if (!extra.length) return;
      const dated = list.id === 'contribution-list';
      const yearOf = (item) => dated ? item.querySelector('time[datetime]').getAttribute('datetime').slice(0, 4) : 'all';
      const years = [...new Set(extra.map(yearOf))];
      const panel = document.createElement('div');
      panel.className = 'expandable-panel';
      panel.id = `${list.id}-extra`;
      const clip = document.createElement('div');
      clip.className = 'expandable-clip';
      clip.append(...extra);
      panel.append(clip);
      list.insertBefore(panel, list.querySelector(':scope > .activity-note'));
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'list-toggle';
      button.setAttribute('aria-controls', panel.id);
      let revealed = 0;
      const sync = () => {
        const expanded = revealed > 0;
        list.classList.toggle('is-open', expanded);
        panel.inert = !expanded;
        extra.forEach((item) => { item.hidden = years.indexOf(yearOf(item)) >= revealed; });
        button.setAttribute('aria-expanded', String(expanded));
        button.dataset.hasMore = String(revealed < years.length);
        button.textContent = revealed === years.length ? 'Show less' : dated ? `Show more · ${years[revealed]}` : 'Show more';
      };
      sync();
      button.addEventListener('click', () => {
        revealed = revealed === years.length ? 0 : revealed + 1;
        sync();
        if (revealed > 0) requestAnimationFrame(() => scrollExpandedIntoView(list));
        releaseTarget();
      });
      panel.addEventListener('transitionend', (event) => {
        if (event.target === panel && event.propertyName === 'grid-template-rows' && list.classList.contains('is-open')) {
          scrollExpandedIntoView(list);
        }
      });
      list.after(button);
    });
    const tagGroups = [...document.querySelectorAll('.tag-group')];
    if (tagGroups.length) {
      tagGroups.forEach((group) => { group.open = false; });
      const openTag = () => {
        const group = document.getElementById(hashTargetId());
        if (!tagGroups.includes(group)) return;
        group.open = true;
        requestAnimationFrame(() => group.scrollIntoView({ behavior: 'instant', block: 'start' }));
      };
      listen(window, 'hashchange', openTag);
      listen(window, 'pageshow', openTag);
      openTag();
    }
    const searchInput = document.getElementById('blog-search');
    if (searchInput) {
      const dialog = document.getElementById('search-dialog');
      dialog.tabIndex = -1;
      dialog.autofocus = true;
      const openButton = document.querySelector('.search-open');
      const results = document.getElementById('search-results');
      const syncScrollHint = addScrollHint(results, dialog);
      let engine;
      let sequence = 0;
      const loadSearch = () => engine ??= import('/pagefind/pagefind.js').then(async pagefind => {
        await pagefind.options({ excerptLength: 18, excerptEllipsis: '…' });
        return pagefind;
      });
      const positionSearch = () => {
        dialog.style.setProperty('--search-top', `${Math.round(openButton.getBoundingClientRect().bottom + 12)}px`);
      };
      const openSearch = () => {
        positionSearch();
        dialog.showModal();
        searchInput.focus({ preventScroll: true });
        syncScrollHint();
      };
      openButton.addEventListener('click', openSearch);
      listen(window, 'resize', () => { if (dialog.open) positionSearch(); });
      dialog.addEventListener('close', () => {
        ++sequence;
        searchInput.value = '';
        results.replaceChildren();
        syncScrollHint();
        openButton.focus({ preventScroll: true });
      });
      dialog.querySelector('.search-close').addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
      listen(document, 'keydown', (event) => {
        if (event.key === 'Escape' && dialog.open) {
          event.preventDefault();
          dialog.close();
        } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
          event.preventDefault();
          if (dialog.open) dialog.close(); else openSearch();
        }
      });
      searchInput.addEventListener('input', async () => {
        const query = searchInput.value.trim();
        const request = ++sequence;
        results.replaceChildren();
        results.scrollTop = 0;
        syncScrollHint();
        if (!query) return;
        results.textContent = 'Searching…';
        try {
          const pagefind = await loadSearch();
          const found = await pagefind.debouncedSearch(query);
          if (controller.signal.aborted || request !== sequence || !found) return;
          results.replaceChildren();
          if (!found.results.length) { results.textContent = 'No articles found.'; return; }
          const items = await Promise.all(found.results.map((item) => item.data()));
          if (controller.signal.aborted || request !== sequence) return;
          const titleQuery = query.normalize('NFKC').toLowerCase();
          const titleMatch = (item) => item.meta.title.normalize('NFKC').toLowerCase().includes(titleQuery);
          items.sort((a, b) => Number(titleMatch(b)) - Number(titleMatch(a)));
          const list = document.createElement('ul');
          items.forEach((item) => {
            const row = document.createElement('li');
            const link = document.createElement('a');
            link.href = item.url;
            const label = document.createElement('span');
            label.className = 'link-label';
            const title = item.meta.title;
            const terms = [...new Set(query.split(/\s+/))].sort((a, b) => b.length - a.length);
            const pattern = new RegExp(terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'giu');
            let end = 0;
            for (const match of title.matchAll(pattern)) {
              label.append(title.slice(end, match.index));
              const mark = document.createElement('mark');
              mark.textContent = match[0];
              label.append(mark);
              end = match.index + match[0].length;
            }
            label.append(title.slice(end));
            link.append(label);
            if (item.excerpt?.includes('<mark>')) {
              const excerpt = document.createElement('span');
              excerpt.className = 'search-match';
              excerpt.innerHTML = item.excerpt;
              link.append(excerpt);
            }
            row.append(link);
            list.append(row);
          });
          const summary = document.createElement('p');
          summary.className = 'search-summary';
          summary.textContent = `${items.length} ${items.length === 1 ? 'article' : 'articles'} found`;
          results.append(summary, list);
          syncScrollHint();
        } catch (error) {
          if (!controller.signal.aborted && request === sequence) results.textContent = 'Search is unavailable. Please refresh and try again.';
        }
      });
    }
    document.querySelectorAll('.article pre').forEach((pre) => {
      const source = pre.querySelector('code') || pre;
      const original = source.textContent;
      const highlighted = pre.parentElement.classList.contains('codehilite') ? pre.parentElement : pre;
      const container = document.createElement('div');
      container.className = 'article-code';
      highlighted.before(container);
      container.append(highlighted);
      const toolbar = document.createElement('div');
      toolbar.className = 'article-code-header';
      const copy = document.createElement('button');
      copy.type = 'button';
      copy.className = 'code-copy';
      copy.textContent = 'Copy';
      copy.setAttribute('aria-label', 'Copy code');
      let resetTimer;
      copy.addEventListener('click', async () => {
        clearTimeout(resetTimer);
        timers.delete(resetTimer);
        try {
          await navigator.clipboard.writeText(original);
          if (controller.signal.aborted) return;
          copy.textContent = 'Copied';
        } catch {
          if (controller.signal.aborted) return;
          copy.textContent = 'Copy failed';
        }
        copy.setAttribute('aria-label', copy.textContent);
        resetTimer = setTimeout(() => {
          timers.delete(resetTimer);
          if (controller.signal.aborted) return;
          copy.textContent = 'Copy';
          copy.setAttribute('aria-label', 'Copy code');
        }, 2000);
        timers.add(resetTimer);
      });
      toolbar.append(copy);
      container.prepend(toolbar);
    });
    return () => {
      controller.abort();
      observers.forEach(observer => observer.disconnect());
      timers.forEach(clearTimeout);
      const dialog = document.getElementById('search-dialog');
      if (dialog?.open) dialog.close();
      readingProgress?.remove();
    };
  };
  let cleanupPage = initPage();
  let pendingPage = false;
  const syncNavigation = () => {
    const home = location.pathname === '/' || location.pathname === '/index.html';
    header.querySelector('.brand')?.toggleAttribute('data-no-swup', home);
    header.querySelectorAll('.nav-links a').forEach(link => {
      const active = link.pathname === '/blog/' && !home;
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  };
  syncNavigation();
  if (window.Swup) {
    const swup = new Swup({ containers: ['#main'] });
    // Swup's cross-page reset must never inherit the site's in-page smooth-scroll rule.
    swup.hooks.replace('scroll:top', () => {
      window.scrollTo({ top: 0, behavior: 'instant' });
      return true;
    });
    swup.hooks.on('visit:start', async (visit) => {
      root.classList.add('is-navigating');
      visit.animation.animate = false;
      visit.scroll.animate = false;
      header.classList.remove('nav-reset');
      if (!header.classList.contains('menu-open')) return;
      const bar = header.querySelector('.header-inner');
      setOpen(false);
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      await new Promise(resolve => {
        const done = (event) => {
          if (event && (event.target !== bar || event.propertyName !== 'grid-template-rows')) return;
          bar.removeEventListener('transitionend', done);
          clearTimeout(timeout);
          resolve();
        };
        const timeout = setTimeout(() => done(), 320);
        bar.addEventListener('transitionend', done);
      });
    });
    const finishVisit = () => {
      root.classList.remove('is-navigating');
      navigationProgress.classList.remove('is-loading');
      header.classList.toggle('is-scrolled', window.scrollY > 6);
    };
    swup.hooks.on('visit:abort', finishVisit);
    swup.hooks.on('content:scroll', () => {
      // Keep cross-page scrolling instant until the browser has applied Swup's target.
      requestAnimationFrame(() => requestAnimationFrame(finishVisit));
    }, { after: true });
    swup.hooks.on('content:replace', (visit) => {
      cleanupPage();
      pendingPage = true;
      const incoming = visit.to.document;
      if (incoming) {
        document.body.className = incoming.body.className;
        document.documentElement.lang = incoming.documentElement.lang;
        for (const selector of ['link[rel="canonical"]', 'meta[name="description"]']) {
          const current = document.head.querySelector(selector);
          const next = incoming.head.querySelector(selector);
          if (current && next) current.replaceWith(next.cloneNode(true));
        }
      }
    }, { before: true });
    swup.hooks.on('page:view', () => {
      if (!pendingPage) return;
      pendingPage = false;
      cleanupPage = initPage();
      syncNavigation();
      header.classList.toggle('is-scrolled', window.scrollY > 6);
    });
  }
})();
