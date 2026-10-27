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
  const targets = [...(nav?.querySelectorAll('a[href^="#"]') || [])]
    .map((link) => document.getElementById(link.hash.slice(1)))
    .filter(Boolean);
  const links = [...document.querySelectorAll('.nav-links a[href^="#"], .page-toc a[href^="#"]')];
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
  links.forEach((link) => link.addEventListener('click', () => selectTarget(link.hash.slice(1))));
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
    targets.forEach((target) => target.classList.toggle('is-current', target.id === active));
    if (toc) {
      const visible = targets[0].getBoundingClientRect().bottom <= navHeight + 28;
      toc.classList.toggle('is-visible', visible);
      toc.setAttribute('aria-hidden', String(!visible));
      toc.inert = !visible;
    }
    links.forEach((link) => {
      const current = link.getAttribute('href') === '#' + active;
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
  window.addEventListener('hashchange', () => selectTarget(location.hash.slice(1)));
  window.addEventListener('load', () => {
    if (location.hash) selectTarget(location.hash.slice(1));
    else schedule();
  });
  document.querySelector('details')?.addEventListener('toggle', releaseTarget);
  schedule();
})();
