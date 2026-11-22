// Holt neueste YouTube-Videos, Twitch-Live-Status und Clips und schreibt data/feed.json.
// Vorschaubilder werden lokal gespeichert (data/thumbs), damit Besucher keine Verbindung
// zu YouTube/Twitch aufbauen, solange sie nichts anklicken (DSGVO).
// Läuft per GitHub Action (Node 20+, keine Abhängigkeiten).
import { writeFile, readFile, mkdir, readdir, unlink } from 'node:fs/promises';

const YT_CHANNEL_ID = 'UCP52-QScf7y3ZtHUzGdFelQ';
const TWITCH_LOGIN = 'nerdpublicgaming';
const { TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, INSTAGRAM_TOKEN, BEHOLD_FEED_URL, FETCH_INSTA } = process.env;
const OUT = 'data/feed.json';
const THUMBS = 'data/thumbs';

const old = await readFile(OUT, 'utf8').then(JSON.parse).catch(() => ({}));
await mkdir(THUMBS, { recursive: true });
const keep = new Set();

async function saveThumb(url, name) {
  if (!url) return '';
  const file = `${THUMBS}/${name}.jpg`;
  keep.add(`${name}.jpg`);
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    await writeFile(file, Buffer.from(await r.arrayBuffer()));
    return file;
  } catch (e) {
    console.warn('Thumbnail fehlgeschlagen:', url, e.message);
    return '';
  }
}

const unxml = s => s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");

// ---------- YouTube (RSS, kein API-Key nötig) ----------
async function youtube() {
  const r = await fetch(`https://www.youtube.com/feeds/videos.xml?channel_id=${YT_CHANNEL_ID}`);
  if (!r.ok) throw new Error('YouTube-Feed: ' + r.status);
  const xml = await r.text();
  const entries = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(m => m[1]);
  const vids = [];
  for (const e of entries.slice(0, 8)) {
    const id = e.match(/<yt:videoId>(.*?)<\/yt:videoId>/)?.[1];
    if (!id) continue;
    const title = unxml(e.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? '');
    const published = e.match(/<published>(.*?)<\/published>/)?.[1];
    const views = Number(e.match(/<media:statistics views="(\d+)"/)?.[1] || 0);
    // Shorts ausfiltern? -> hier bei Bedarf: if (/#shorts/i.test(title)) continue;
    const thumb = await saveThumb(`https://i.ytimg.com/vi/${id}/hqdefault.jpg`, `yt-${id}`);
    vids.push({ id, title, published, views, thumb });
  }
  return vids;
}

// ---------- Twitch (Helix-API) ----------
async function twitch() {
  if (!TWITCH_CLIENT_ID || !TWITCH_CLIENT_SECRET) {
    console.warn('Keine Twitch-Zugangsdaten gesetzt – Twitch wird übersprungen.');
    return null;
  }
  const tok = await fetch('https://id.twitch.tv/oauth2/token', {
    method: 'POST',
    body: new URLSearchParams({ client_id: TWITCH_CLIENT_ID, client_secret: TWITCH_CLIENT_SECRET, grant_type: 'client_credentials' })
  }).then(r => r.json());
  if (!tok.access_token) throw new Error('Twitch-Token: ' + JSON.stringify(tok));
  const h = { 'Client-Id': TWITCH_CLIENT_ID, Authorization: `Bearer ${tok.access_token}` };
  const api = p => fetch('https://api.twitch.tv/helix/' + p, { headers: h }).then(r => r.json());

  const user = (await api(`users?login=${TWITCH_LOGIN}`)).data?.[0];
  if (!user) throw new Error('Twitch-User nicht gefunden');

  const s = (await api(`streams?user_id=${user.id}`)).data?.[0];
  const live = s
    ? { isLive: true, title: s.title, game: s.game_name, viewers: s.viewer_count, startedAt: s.started_at, lastSeen: new Date().toISOString() }
    : { isLive: false, lastSeen: old.live?.isLive ? new Date().toISOString() : old.live?.lastSeen };

  const since = new Date(Date.now() - 180 * 864e5).toISOString();
  const raw = (await api(`clips?broadcaster_id=${user.id}&started_at=${since}&first=50`)).data ?? [];
  raw.sort((a, b) => b.created_at.localeCompare(a.created_at)); // neueste zuerst
  const clips = [];
  for (const c of raw.slice(0, 10)) {
    clips.push({
      id: c.id, url: c.url, title: c.title, views: c.view_count, created: c.created_at,
      duration: c.duration, creator: c.creator_name,
      thumb: await saveThumb(c.thumbnail_url, `clip-${c.id}`)
    });
  }
  return { live, clips };
}

const feed = { updated: new Date().toISOString(), live: old.sample ? null : old.live, videos: old.sample ? [] : old.videos, clips: old.sample ? [] : old.clips };
try { feed.videos = await youtube(); } catch (e) { console.error(e.message); }
try { const t = await twitch(); if (t) Object.assign(feed, t); } catch (e) { console.error(e.message); }

// ---------- Instagram ----------
// Zwei Wege, je nachdem welches Secret gesetzt ist:
//  * BEHOLD_FEED_URL – Feed-Adresse von behold.so (kein Meta-Entwicklerkonto nötig, gratis: 6 Posts, 1x täglich neu)
//  * INSTAGRAM_TOKEN – offizieller Schlüssel aus dem Meta-App-Dashboard
// Schreibt data/insta.json + Bilder nach data/insta. Ohne Secret oder bei Fehlern bleibt der letzte Stand stehen.
// Behold zählt jeden Abruf (gratis 1.200/Monat) – darum nur alle 4 Stunden abfragen (FETCH_INSTA, siehe Workflow).
async function instaPosts() {
  if (BEHOLD_FEED_URL) {
    const r = await fetch(BEHOLD_FEED_URL);
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !Array.isArray(j.posts)) throw new Error('Behold: ' + (j.message || r.status));
    return j.posts.filter(m => m.visibility !== 'hidden').map(m => ({
      id: m.id, type: m.mediaType, caption: m.prunedCaption ?? m.caption ?? '', permalink: m.permalink, date: m.timestamp,
      src: m.sizes?.medium?.mediaUrl || m.sizes?.large?.mediaUrl || (m.mediaType === 'VIDEO' ? m.thumbnailUrl : m.mediaUrl),
    })).map(m => ({ ...m, ext: (m.src?.split('?')[0].match(/\.(jpe?g|png|webp)$/i)?.[1] || 'jpg').toLowerCase() }));
  }
  if (INSTAGRAM_TOKEN) {
    const fields = 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp';
    const r = await fetch(`https://graph.instagram.com/me/media?fields=${fields}&limit=24&access_token=${encodeURIComponent(INSTAGRAM_TOKEN)}`);
    const j = await r.json();
    if (!r.ok || !Array.isArray(j.data)) throw new Error('Instagram: ' + (j.error?.message || r.status));
    return j.data.map(m => ({
      id: m.id, type: m.media_type, caption: m.caption || '', permalink: m.permalink, date: m.timestamp,
      src: m.media_type === 'VIDEO' ? m.thumbnail_url : m.media_url, ext: 'jpg'
    }));
  }
  return null;
}

async function instagram() {
  if (FETCH_INSTA === 'false') return;
  const list = await instaPosts();
  if (!list) { console.warn('Kein BEHOLD_FEED_URL / INSTAGRAM_TOKEN gesetzt – Instagram wird übersprungen.'); return; }
  const DIR = 'data/insta', OUTI = 'data/insta.json';
  const before = await readFile(OUTI, 'utf8').then(JSON.parse).catch(() => ({ posts: [] }));
  const known = new Set((before.posts || []).map(p => p.img));
  await mkdir(DIR, { recursive: true });
  const keepI = new Set(), posts = [];
  for (const m of list) {
    if (!m.src || !m.permalink) continue;
    const name = `ig-${m.id}.${m.ext}`, file = `${DIR}/${name}`;
    let ok = known.has(file) && await readFile(file).then(() => true, () => false);
    if (!ok) {  // Bild nur beim ersten Mal laden – das Bild eines Posts ändert sich nicht
      try {
        const b = await fetch(m.src);
        if (!b.ok) throw new Error(b.status);
        await writeFile(file, Buffer.from(await b.arrayBuffer()));
        ok = true;
      } catch (e) { console.warn('Instagram-Bild fehlgeschlagen:', m.id, e.message); }
    }
    if (!ok) continue;
    keepI.add(name);
    posts.push({ id: m.id, type: m.type, caption: m.caption, permalink: m.permalink, date: m.date, img: file });
  }
  for (const f of await readdir(DIR)) if (!keepI.has(f)) await unlink(`${DIR}/${f}`).catch(() => {});
  // nur schreiben, wenn sich wirklich etwas geändert hat (sonst gäbe es ständig Commits)
  if (JSON.stringify(before.posts || []) !== JSON.stringify(posts)) {
    await writeFile(OUTI, JSON.stringify({ updated: new Date().toISOString(), posts }, null, 2));
    console.log(`Instagram: ${posts.length} Posts aktualisiert`);
  } else console.log('Instagram: nichts Neues');
}
try { await instagram(); } catch (e) { console.error(e.message); }

// alte Vorschaubilder aufräumen
for (const f of await readdir(THUMBS)) if (!keep.has(f) && f !== '.gitkeep') await unlink(`${THUMBS}/${f}`).catch(() => {});

await writeFile(OUT, JSON.stringify(feed, null, 2));
console.log(`OK: ${feed.videos?.length ?? 0} Videos, ${feed.clips?.length ?? 0} Clips, live=${!!feed.live?.isLive}`);
