{
  // SC-Logs: Inhalte liegen verschlüsselt in sc-logs/data/*.enc (AES-256-GCM).
  // Der Schlüssel wird im Browser aus dem Passwort abgeleitet (PBKDF2-SHA256).
  const D = 'data/';
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const fmtDate = d => { try { return new Date(d + 'T12:00:00').toLocaleDateString('de-AT', {weekday: 'short', day: 'numeric', month: 'long', year: 'numeric'}); } catch { return d; } };
  let key = null, meta = null, index = null;

  async function getMeta() {
    if (!meta) meta = await (await fetch(D + 'meta.json', {cache: 'no-cache'})).json();
    return meta;
  }
  async function derive(pw) {
    const m = await getMeta();
    const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({name: 'PBKDF2', salt: b64(m.salt), iterations: m.iter, hash: 'SHA-256'},
      base, {name: 'AES-GCM', length: 256}, true, ['decrypt']);
  }
  async function openFile(name) {
    const r = await fetch(D + name + '.enc', {cache: 'no-cache'});
    if (!r.ok) throw new Error('Datei fehlt: ' + name);
    const buf = new Uint8Array(await r.arrayBuffer());
    return crypto.subtle.decrypt({name: 'AES-GCM', iv: buf.slice(0, 12)}, key, buf.slice(12));
  }
  const openJSON = async n => JSON.parse(new TextDecoder().decode(await openFile(n)));

  // ---- angemeldet bleiben ----
  function stores() { const s = []; try { s.push(sessionStorage, localStorage); } catch {} return s; }
  async function tryStored() {
    for (const s of stores()) {
      try {
        const raw = s.getItem('sclogs'); if (!raw) continue;
        const o = JSON.parse(raw), m = await getMeta();
        if (o.salt !== m.salt) { s.removeItem('sclogs'); continue; }   // Passwort wurde geändert
        key = await crypto.subtle.importKey('raw', b64(o.k), 'AES-GCM', true, ['decrypt']);
        index = await openJSON('index');
        return true;
      } catch { key = null; }
    }
    return false;
  }
  async function remember(persist) {
    try {
      const raw = new Uint8Array(await crypto.subtle.exportKey('raw', key));
      const o = JSON.stringify({salt: meta.salt, k: btoa(String.fromCharCode(...raw))});
      sessionStorage.setItem('sclogs', o);
      if (persist) localStorage.setItem('sclogs', o);
    } catch {}
  }
  function logout() {
    for (const s of stores()) { try { s.removeItem('sclogs'); } catch {} }
    key = null; index = null; location.hash = ''; location.reload();
  }

  // ---- Ansichten ----
  const app = $('app'), gate = $('gate');
  function showApp() { gate.hidden = true; app.hidden = false; route(); }

  function listView() {
    document.title = 'SC-Logs – NerdPublic Gaming';
    const cards = index.entries.map(a => `
      <a class="ov parchment logcard" href="#${esc(a.slug)}">
        <div class="ov-top"><p class="kicker">${esc(fmtDate(a.date))}</p><h3>${esc(a.title)}</h3><p class="sub">${esc(a.sub)}</p></div>
        <div class="mini-tiles">${a.tiles.map(t => `<div class="${esc(t.tone || '')}"><span>${esc(t.label)}</span><b>${esc(t.value)}</b></div>`).join('')}</div>
        <p><strong>Ziel:</strong> ${esc(a.goal)}</p>
        <span class="open">Auswertung öffnen →</span>
      </a>`).join('');
    const g = index.guide ? `
      <a class="ov parchment logcard guidecard" href="#${esc(index.guide.slug)}">
        <div class="ov-top"><p class="kicker">Erst lesen</p><h3>${esc(index.guide.title)}</h3><p class="sub">${esc(index.guide.sub)}</p></div>
        <span class="open">Lese-Guide öffnen →</span>
      </a>` : '';
    app.innerHTML = `
      <section class="g-hero band"><div class="g-hero-in">
        <p class="kick">Geschützter Bereich · Static</p>
        <h1>SC-Logs</h1>
        <p class="sub">Unsere Log-Auswertungen pro Abend – nicht zum Runtermachen, sondern damit wir gemeinsam besser werden.</p>
        <div class="g-actions"><button type="button" class="ghost" id="logout">Abmelden</button></div>
      </div></section>
      <section class="band"><div class="ovs">${g}${cards || '<p class="empty">Noch keine Auswertungen.</p>'}</div></section>`;
    $('logout').onclick = logout;
    scrollTo(0, 0);
  }

  async function pageView(slug) {
    const entry = index.entries.find(a => a.slug === slug) || (index.guide && index.guide.slug === slug ? index.guide : null);
    app.innerHTML = '<section class="band"><p class="loading">Wird entschlüsselt …</p></section>';
    try {
      const p = await openJSON(entry.file);
      document.title = p.title + ' – SC-Logs';
      app.innerHTML = `<div class="crumbs band"><a href="#">SC-Logs</a> › <span>${esc(p.title)}</span>
        <button type="button" class="ghost small" id="logout">Abmelden</button></div>` + p.html +
        `<section class="band"><div class="prevnext"><a class="pn prev" href="#"><small>Zurück</small>Alle Auswertungen</a></div></section>`;
      $('logout').onclick = logout;
      scrollTo(0, 0);
    } catch (err) {
      app.innerHTML = `<section class="band"><p class="empty">Diese Auswertung gibt es nicht (mehr). <a href="#">Zur Übersicht</a></p></section>`;
    }
  }

  function route() {
    if (!key) return;
    const h = decodeURIComponent(location.hash.slice(1));
    const known = h && (index.entries.some(a => a.slug === h) || (index.guide && index.guide.slug === h));
    known ? pageView(h) : listView();
  }
  addEventListener('hashchange', route);

  // Sprunglinks innerhalb einer Auswertung (#s-…, #teil-…) ohne Seitenwechsel
  app.addEventListener('click', async ev => {
    const a = ev.target.closest('a[href^="#"]');
    if (a) {
      const id = a.getAttribute('href').slice(1);
      const el = id && document.getElementById(id);
      if (el && app.contains(el)) { ev.preventDefault(); el.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); }
      return;
    }
    // PDF entschlüsseln und herunterladen
    const b = ev.target.closest('button.dl');
    if (!b) return;
    const label = b.lastChild.textContent;
    b.disabled = true; b.lastChild.textContent = 'Wird vorbereitet …';
    try {
      const data = await openFile(b.dataset.pdf);
      const url = URL.createObjectURL(new Blob([data], {type: 'application/pdf'}));
      const dl = document.createElement('a'); dl.href = url; dl.download = b.dataset.name; document.body.append(dl); dl.click(); dl.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      b.lastChild.textContent = label;
    } catch { b.lastChild.textContent = 'Download fehlgeschlagen'; }
    b.disabled = false;
  });

  // ---- Anmeldung ----
  $('loginForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const btn = $('loginBtn'), msg = $('loginMsg');
    btn.disabled = true; msg.textContent = 'Wird geprüft …'; msg.className = 'msg';
    try {
      key = await derive($('pw').value);
      index = await openJSON('index');
      await remember($('stay').checked);
      $('pw').value = '';
      showApp();
    } catch {
      key = null;
      msg.textContent = 'Falsches Passwort.'; msg.className = 'msg err';
      $('pw').select();
    }
    btn.disabled = false;
  });

  if (!window.crypto || !crypto.subtle) {
    $('loginMsg').textContent = 'Dein Browser unterstützt die Entschlüsselung nicht. Bitte einen aktuellen Browser verwenden.';
  } else {
    tryStored().then(ok => ok ? showApp() : ($('pw').focus()));
  }
}
