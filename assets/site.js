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

  const targets = ['about', 'education', 'interests', 'projects', 'writing', 'contact']
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  const links = [...document.querySelectorAll('.nav-links a[href^="#"], .page-toc a[href^="#"]')];
  let scheduled = false;
  const sync = () => {
    scheduled = false;
    header.classList.toggle('is-scrolled', window.scrollY > 6);
    if (!targets.length) return;
    const navHeight = header.getBoundingClientRect().height;
    const probe = window.scrollY + navHeight + 28;
    let active = targets[0].id;
    for (const el of targets) {
      if (el.getBoundingClientRect().top + window.scrollY <= probe) active = el.id;
    }
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6) active = targets[targets.length - 1].id;
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
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('hashchange', schedule);
  schedule();
})();
