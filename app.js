{
  const CHANNEL = 'nerdpublicgaming';
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate = iso => { try { return new Date(iso).toLocaleDateString('de-AT', {day:'numeric', month:'short', year:'numeric'}); } catch { return ''; } };
  const ago = iso => {
    const d = (Date.now() - new Date(iso)) / 864e5;
    if (d < 1) return 'heute';
    if (d < 2) return 'gestern';
    if (d < 30) return `vor ${Math.floor(d)} Tagen`;
    return fmtDate(iso);
  };
  const dur = s => { s = Math.round(s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const num = n => new Intl.NumberFormat('de-AT').format(n || 0);
  const thumb = (src, label) => src
    ? `<img src="${esc(src)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'ph',textContent:'${esc(label)}'}))">`
    : `<div class="ph">${esc(label)}</div>`;

  $('year').textContent = new Date().getFullYear();

  // ---- Twitch-Player erst nach Klick laden (DSGVO) ----
  $('loadPlayer').addEventListener('click', () => {
    const host = location.hostname || 'localhost';
    const f = document.createElement('iframe');
    f.src = `https://player.twitch.tv/?channel=${CHANNEL}&parent=${encodeURIComponent(host)}&muted=true&autoplay=true`;
    f.allowFullscreen = true;
    f.title = 'Twitch-Stream von NerdPublic Gaming';
    $('player').replaceChildren(f);
    const c = document.createElement('iframe');
    c.src = `https://www.twitch.tv/embed/${CHANNEL}/chat?parent=${encodeURIComponent(host)}&darkpopout`;
    c.title = 'Twitch-Chat von NerdPublic Gaming';
    $('chat').replaceChildren(c);
  });

  // ---- Live-Status ----
  function renderLive(live) {
    const st = $('liveState');
    if (live && live.isLive) {
      st.textContent = `Jetzt live · ${num(live.viewers)} Zuschauer`;
      st.classList.add('on');
      $('liveTitle').textContent = [live.title, live.game && `(${live.game})`].filter(Boolean).join(' ');
      $('navStatus').hidden = false;
      $('playerHead').textContent = 'Gerade live auf Twitch!';
    } else {
      st.textContent = 'Gerade offline';
      $('liveTitle').textContent = live && live.lastSeen ? `Zuletzt live: ${ago(live.lastSeen)}` : 'Folge auf Twitch, dann verpasst du keinen Stream.';
    }
  }

  // ---- Videos ----
  function renderVideos(videos) {
    const g = $('videoGrid');
    if (!videos || !videos.length) { g.innerHTML = '<p class="empty">Noch keine Videos geladen.</p>'; return; }
    g.innerHTML = videos.slice(0, 6).map((v, i) => `
      <article class="video parchment${i === 0 ? ' featured' : ''}">
        <button class="thumb" type="button" data-id="${esc(v.id)}" aria-label="Video abspielen: ${esc(v.title)}">
          ${thumb(v.thumb, 'YouTube')}<span class="play" aria-hidden="true"></span>
        </button>
        <div class="body">
          <h3><a href="https://www.youtube.com/watch?v=${esc(v.id)}" rel="noopener">${esc(v.title)}</a></h3>
          <span class="meta">${ago(v.published)}${v.views ? ' · ' + num(v.views) + ' Aufrufe' : ''} · <a href="https://www.youtube.com/watch?v=${esc(v.id)}" rel="noopener">Auf YouTube öffnen</a></span>
        </div>
      </article>`).join('');
  }

  // Video direkt im Kasten abspielen (Verbindung zu YouTube erst nach Klick)
  $('videoGrid').addEventListener('click', e => {
    const b = e.target.closest('button.thumb'); if (!b || !b.dataset.id) return;
    for (const p of document.querySelectorAll('.video.playing')) stopVideo(p);
    const card = b.closest('.video');
    const f = document.createElement('iframe');
    f.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(b.dataset.id)}?autoplay=1&rel=0`;
    f.title = card.querySelector('h3').textContent;
    f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.allowFullscreen = true;
    const box = document.createElement('div'); box.className = 'thumb'; box.append(f);
    card._thumb = b; b.replaceWith(box); card.classList.add('playing');
  });
  function stopVideo(card) {
    const box = card.querySelector('div.thumb');
    if (box && card._thumb) box.replaceWith(card._thumb);
    card.classList.remove('playing');
  }

  // ---- Clips ----
  function renderClips(clips) {
    const r = $('clipRow');
    if (!clips || !clips.length) { r.innerHTML = '<p class="empty">Noch keine Clips – erstell im nächsten Stream einen!</p>'; return; }
    r.innerHTML = clips.slice(0, 10).map(c => `
      <a class="clip" href="${esc(c.url)}" rel="noopener">
        <div class="thumb">${thumb(c.thumb, 'Clip')}<span class="dur">${dur(c.duration)}</span></div>
        <div class="body">
          <h3>${esc(c.title)}</h3>
          <span class="meta">${num(c.views)} Aufrufe · ${ago(c.created)}${c.creator ? ' · von ' + esc(c.creator) : ''}</span>
        </div>
      </a>`).join('');
  }

  // ---- Guides (nach Kategorie gruppiert) ----
  const CATS = [
    {key: 'fraktale', name: 'Fraktale', note: '5 Spieler'},
    {key: 'strikes', name: 'Strikes', note: '10 Spieler'},
    {key: 'raids', name: 'Raids', note: '10 Spieler'}
  ];
  let guides = [];
  function renderGuides() {
    $('guideGrid').innerHTML = CATS.map(c => {
      const list = guides.filter(g => g.cat === c.key);
      const cards = list.map(g => `
        <a class="guide-mini parchment" href="${esc(g.url || g.pdf || '#guides')}">
          ${g.cover ? `<div class="cover"><img src="${esc(g.cover)}" alt="" loading="lazy"></div>` : ''}
          <div class="gbody"><h3>${esc(g.title)}</h3><p class="sub">${esc(g.bosses)}</p></div>
        </a>`).join('');
      return `<div class="gcat">
        <h3 class="gcat-h"><a href="${c.key}/index.html">${c.name}</a> <span>${list.length ? list.length + ' Guide' + (list.length > 1 ? 's' : '') : 'kommt bald'} · ${c.note}</span></h3>
        ${cards ? `<div class="guides mini">${cards}</div>` : ''}
      </div>`;
    }).join('');
  }

  // ---- Daten laden ----
  const get = p => fetch(p, {cache: 'no-cache'}).then(r => r.ok ? r.json() : Promise.reject(r.status));
  get('data/feed.json').then(d => {
    renderLive(d.live); renderVideos(d.videos); renderClips(d.clips);
    if (d.updated) $('updated').textContent = `Videos & Clips zuletzt aktualisiert: ${new Date(d.updated).toLocaleString('de-AT')}`;
    if (d.sample) $('updated').textContent = 'Videos und Clips sind Beispieldaten – nach der Einrichtung kommen sie automatisch von YouTube und Twitch.';
  }).catch(() => { renderLive(null); renderVideos([]); renderClips([]); });
  get('data/guides.json').then(d => { guides = d; renderGuides(); }).catch(() => { guides = []; renderGuides(); });
}
