/* Minimal progressive enhancement: menu, active section, and scroll state. */
(() => {
  document.documentElement.classList.add('js');
  const header = document.getElementById('site-header');
  if (!header) return;
  header.classList.toggle('is-scrolled', window.scrollY > 6);
  const navigationProgress = document.createElement('div');
  navigationProgress.className = 'navigation-progress';
  navigationProgress.setAttribute('aria-hidden', 'true');
  document.body.prepend(navigationProgress);
  const article = document.querySelector('.article');
  const readingProgress = article && document.createElement('div');
  if (readingProgress) {
    readingProgress.className = 'reading-progress';
    readingProgress.setAttribute('aria-hidden', 'true');
    document.body.prepend(readingProgress);
  }
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    if (link.origin === location.origin && (link.pathname !== location.pathname || link.search !== location.search)) navigationProgress.classList.add('is-loading');
  }, true);
  window.addEventListener('pageshow', () => {
    navigationProgress.classList.remove('is-loading');
    requestAnimationFrame(() => {
      header.classList.toggle('is-scrolled', window.scrollY > 6);
      document.documentElement.classList.add('is-ready');
    });
  });
  const toggle = header.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-navigation');
  const setOpen = (open) => {
    header.classList.toggle('menu-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
    toggle?.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
  };
  toggle?.addEventListener('click', () => setOpen(!header.classList.contains('menu-open')));
  nav?.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => setOpen(false)));
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
    if (window.innerWidth > 860) setOpen(false);
  }, { passive: true });

  const toc = document.querySelector('.page-toc');
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
  window.addEventListener('wheel', releaseTarget, { passive: true });
  window.addEventListener('touchstart', releaseTarget, { passive: true });
  document.addEventListener('keydown', (event) => {
    if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) releaseTarget();
  });
  let scheduled = false;
  const sync = () => {
    scheduled = false;
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
    tocLinks.forEach((link) => {
      const current = decodeURIComponent(link.hash.slice(1)) === active;
      link.classList.toggle('is-active', current);
      if (current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  };
  const schedule = () => {
    if (!scheduled) {
      scheduled = true;
      window.requestAnimationFrame(sync);
    }
  };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', releaseTarget, { passive: true });
  window.addEventListener('hashchange', () => selectTarget(decodeURIComponent(location.hash.slice(1))));
  window.addEventListener('load', () => {
    if (location.hash) selectTarget(decodeURIComponent(location.hash.slice(1)));
    else schedule();
  });
  document.querySelectorAll('[data-expandable]').forEach((list) => {
    const extra = [...list.querySelectorAll(':scope > .project-item')].slice(3);
    if (!extra.length) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'list-toggle';
    button.setAttribute('aria-controls', list.id);
    const setExpanded = (expanded) => {
      extra.forEach((item) => { item.hidden = !expanded; });
      button.setAttribute('aria-expanded', String(expanded));
      button.textContent = expanded ? 'Show less ↑' : 'Show more ↓';
    };
    setExpanded(false);
    button.addEventListener('click', () => {
      const expanded = button.getAttribute('aria-expanded') !== 'true';
      setExpanded(expanded);
      releaseTarget();
      if (expanded) extra[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    list.after(button);
  });
  const searchInput = document.getElementById('blog-search');
  if (searchInput) {
    const dialog = document.getElementById('search-dialog');
    const openButton = document.querySelector('.search-open');
    const results = document.getElementById('search-results');
    let engine;
    let sequence = 0;
    const loadSearch = () => engine ??= import('/pagefind/pagefind.js');
    const openSearch = () => {
      dialog.showModal();
      searchInput.focus();
      loadSearch();
    };
    openButton.addEventListener('click', openSearch);
    dialog.querySelector('.search-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    document.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (dialog.open) dialog.close(); else openSearch();
      }
    });
    searchInput.addEventListener('input', async () => {
      const query = searchInput.value.trim();
      const request = ++sequence;
      results.replaceChildren();
      if (!query) return;
      results.textContent = 'Searching…';
      try {
        const pagefind = await loadSearch();
        const found = await pagefind.debouncedSearch(query);
        if (request !== sequence || !found) return;
        results.replaceChildren();
        if (!found.results.length) { results.textContent = 'No articles found.'; return; }
        const items = await Promise.all(found.results.map((item) => item.data()));
        if (request !== sequence) return;
        const list = document.createElement('ul');
        items.forEach((item) => {
          const row = document.createElement('li');
          const link = document.createElement('a');
          link.href = item.url;
          link.textContent = item.meta.title;
          row.append(link);
          list.append(row);
        });
        results.append(list);
      } catch (error) {
        if (request === sequence) results.textContent = 'Search is unavailable. Please refresh and try again.';
      }
    });
  }
  const images = [...document.querySelectorAll('.article img')].filter((img) => !img.closest('a, button'));
  if (images.length) {
    let activeImage = null;
    let overlay = null;
    let cleanupTimer = null;
    let pendingImage = null;
    let pendingOverlay = null;
    const finishPending = () => {
      clearTimeout(cleanupTimer);
      if (pendingImage) {
        pendingImage.style.position = '';
        pendingImage.style.zIndex = '';
        pendingImage.style.willChange = '';
      }
      pendingOverlay?.remove();
      cleanupTimer = pendingImage = pendingOverlay = null;
    };
    const closeZoom = () => {
      if (!activeImage) return;
      const image = activeImage;
      const layer = overlay;
      image.style.transform = '';
      image.classList.remove('is-zoomed');
      layer.classList.remove('is-open');
      pendingImage = image;
      pendingOverlay = layer;
      cleanupTimer = setTimeout(finishPending, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 300);
      activeImage = null;
      overlay = null;
    };
    images.forEach((img) => {
      img.dataset.zoom = '';
      img.tabIndex = 0;
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', `Enlarge image: ${img.alt || 'Article image'}`);
      img.addEventListener('click', () => {
        if (activeImage === img) { closeZoom(); return; }
        closeZoom();
        finishPending();
        const rect = img.getBoundingClientRect();
        // A quick reopen can interrupt the return transition; measure its layout box.
        const transform = new DOMMatrix(getComputedStyle(img).transform);
        const width = rect.width / transform.a;
        const height = rect.height / transform.d;
        rect.x += (rect.width - width) / 2 - transform.e;
        rect.y += (rect.height - height) / 2 - transform.f;
        rect.width = width;
        rect.height = height;
        const top = document.querySelector('.site-header')?.getBoundingClientRect().bottom || 0;
        const scale = Math.min((innerWidth - 48) / rect.width, (innerHeight - top - 48) / rect.height);
        const x = innerWidth / 2 - rect.left - rect.width / 2;
        const y = (innerHeight + top) / 2 - rect.top - rect.height / 2;
        const layer = document.createElement('div');
        layer.className = 'image-zoom-overlay';
        layer.setAttribute('aria-hidden', 'true');
        layer.addEventListener('click', closeZoom);
        document.body.append(layer);
        overlay = layer;
        activeImage = img;
        img.style.position = 'relative';
        // Keep the image below the fixed header throughout both transitions.
        img.style.zIndex = '90';
        img.style.willChange = 'transform';
        img.classList.add('is-zoomed');
        requestAnimationFrame(() => {
          if (activeImage !== img) return;
          layer.classList.add('is-open');
          img.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
        });
      });
      img.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          img.click();
        }
      });
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeZoom();
    });
    window.addEventListener('scroll', closeZoom, { passive: true });
    window.addEventListener('resize', closeZoom, { passive: true });
  }
  schedule();
})();
