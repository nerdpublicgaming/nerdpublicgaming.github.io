// Zeigt die neuesten Instagram-Posts aus data/insta.json (wird von der GitHub Action erzeugt).
(async () => {
  const grid = document.getElementById('instaGrid');
  if (!grid) return;
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let posts = [];
  try {
    const r = await fetch('data/insta.json', { cache: 'no-cache' });
    if (r.ok) posts = (await r.json()).posts || [];
  } catch (e) { /* noch keine Daten */ }
  if (!posts.length) {
    grid.outerHTML = '<p class="empty-cat parchment">Die ersten Posts (und Hundebilder) tauchen hier auf, sobald Instagram verbunden ist. Bis dahin: schau direkt auf <a href="https://www.instagram.com/nerdpublicgaming/" rel="noopener">@nerdpublicgaming</a> vorbei.</p>';
    return;
  }
  const fmt = d => new Date(d).toLocaleDateString('de-AT', { day: 'numeric', month: 'short', year: 'numeric' });
  const icon = { VIDEO: '▶', CAROUSEL_ALBUM: '❐' };
  grid.innerHTML = posts.map(p => {
    const cap = (p.caption || '').split('\n')[0];
    const short = cap.length > 90 ? cap.slice(0, 88) + '…' : cap;
    return `<a class="insta" href="${esc(p.permalink)}" rel="noopener">
      <img src="${esc(p.img)}" alt="${esc(short || 'Instagram-Post')}" loading="lazy">
      ${icon[p.type] ? `<span class="insta-type" aria-hidden="true">${icon[p.type]}</span>` : ''}
      <span class="insta-cap"><time datetime="${esc(p.date)}">${fmt(p.date)}</time>${short ? `<span>${esc(short)}</span>` : ''}</span>
    </a>`;
  }).join('');
})();
