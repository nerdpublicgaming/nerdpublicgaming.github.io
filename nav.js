{
  // Dropdown "GW2 Guides" im Menü
  const dd = document.querySelector('.dd');
  if (dd) {
    const btn = dd.querySelector('.dd-btn');
    const set = open => { dd.classList.toggle('is-open', open); btn.setAttribute('aria-expanded', open); };
    let hoverAt = 0;
    btn.addEventListener('click', e => { e.stopPropagation(); if (Date.now() - hoverAt < 600) return; set(!dd.classList.contains('is-open')); });
    document.addEventListener('click', e => { if (!dd.contains(e.target)) set(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { set(false); btn.focus(); } });
    if (matchMedia('(hover:hover)').matches) {
      let t;
      dd.addEventListener('mouseenter', () => { clearTimeout(t); if (!dd.classList.contains('is-open')) hoverAt = Date.now(); set(true); });
      dd.addEventListener('mouseleave', () => { t = setTimeout(() => set(false), 250); });
    }
  }
  for (const y of document.querySelectorAll('.year')) y.textContent = new Date().getFullYear();
}
