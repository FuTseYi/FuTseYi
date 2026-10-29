/* Minimal progressive enhancement: menu, active section, and scroll state. */
(() => {
  document.documentElement.classList.add('js');
  const header = document.getElementById('site-header');
  if (!header) return;
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
  const links = [...document.querySelectorAll('.nav-links a[href^="#"]'), ...tocLinks];
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
      const visible = toc.classList.contains('article-toc') || targets[0].getBoundingClientRect().bottom <= navHeight + 28;
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
  const images = [...document.querySelectorAll('.article img')].filter((img) => !img.closest('a, button'));
  if (images.length) {
    let activeImage = null;
    let overlay = null;
    let pendingCleanup = null;
    const finishPending = () => { pendingCleanup?.(); pendingCleanup = null; };
    const closeZoom = () => {
      if (!activeImage) return;
      const image = activeImage;
      const layer = overlay;
      activeImage = null;
      overlay = null;
      image.style.transform = '';
      image.classList.remove('is-zoomed');
      layer.classList.remove('is-open');
      const timer = setTimeout(finishPending, 360);
      pendingCleanup = () => {
        clearTimeout(timer);
        image.style.position = '';
        image.style.zIndex = '';
        image.style.willChange = '';
        layer.remove();
      };
    };
    images.forEach((img) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'image-zoom-trigger';
      button.setAttribute('aria-label', `Enlarge image: ${img.alt || 'Article image'}`);
      img.replaceWith(button);
      button.append(img);
      button.addEventListener('click', () => {
        if (activeImage === img) { closeZoom(); return; }
        finishPending();
        const rect = img.getBoundingClientRect();
        const scale = Math.min((innerWidth - 48) / rect.width, (innerHeight - 48) / rect.height,
          img.naturalWidth / rect.width, img.naturalHeight / rect.height);
        const x = innerWidth / 2 - rect.left - rect.width / 2;
        const y = innerHeight / 2 - rect.top - rect.height / 2;
        const layer = document.createElement('div');
        layer.className = 'image-zoom-overlay';
        layer.setAttribute('aria-hidden', 'true');
        layer.addEventListener('click', closeZoom);
        document.body.append(layer);
        overlay = layer;
        activeImage = img;
        img.style.position = 'relative';
        img.style.zIndex = '1001';
        img.style.willChange = 'transform';
        img.classList.add('is-zoomed');
        requestAnimationFrame(() => {
          if (activeImage !== img) return;
          layer.classList.add('is-open');
          img.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
        });
      });
    });
    document.addEventListener('keydown', (event) => {
      if (['Escape', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) closeZoom();
    });
    window.addEventListener('wheel', closeZoom, { passive: true });
    window.addEventListener('touchmove', closeZoom, { passive: true });
  }
  schedule();
})();
