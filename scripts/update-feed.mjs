// Holt neueste YouTube-Videos, Twitch-Live-Status und Clips und schreibt data/feed.json.
// Vorschaubilder werden lokal gespeichert (data/thumbs), damit Besucher keine Verbindung
// zu YouTube/Twitch aufbauen, solange sie nichts anklicken (DSGVO).
// Läuft per GitHub Action (Node 20+, keine Abhängigkeiten).
import { writeFile, readFile, mkdir, readdir, unlink } from 'node:fs/promises';

const YT_CHANNEL_ID = 'UCP52-QScf7y3ZtHUzGdFelQ';
const TWITCH_LOGIN = 'nerdpublicgaming';
const { TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET } = process.env;
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

// alte Vorschaubilder aufräumen
for (const f of await readdir(THUMBS)) if (!keep.has(f) && f !== '.gitkeep') await unlink(`${THUMBS}/${f}`).catch(() => {});

await writeFile(OUT, JSON.stringify(feed, null, 2));
console.log(`OK: ${feed.videos?.length ?? 0} Videos, ${feed.clips?.length ?? 0} Clips, live=${!!feed.live?.isLive}`);
