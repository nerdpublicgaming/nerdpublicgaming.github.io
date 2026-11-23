#!/usr/bin/env python3
"""Erzeugt die GW2-Guide-Seiten (Fraktale, Strikes, Raids) aus content/fraktale/*.json und content/raids/*.json.

Aufruf (im Hauptordner der Seite):  python scripts/build-guides.py
Texte ändern: in content/fraktale/<name>.json bearbeiten und das Skript neu starten.
Neuen Guide einer Kategorie zuordnen: Namen unten in CATS eintragen.
Das Skript aktualisiert außerdem das Menü in index.html, impressum.html, datenschutz.html und sc-logs/index.html.
"""
import json, html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "fraktale")
RAIDS = os.path.join(ROOT, "content", "raids")

# Kategorien: Ordner, Name, Schild auf den Karten, Untertitel, Guides
CATS = [
    {"key": "fraktale", "name": "Fraktale", "label": "Fraktal-CM", "mode": "Fraktal Challenge Mode", "players": "5 Spieler",
     "intro": "Die Challenge Modes der Fraktale (5 Spieler).",
     "guides": ["nightmare", "shattered-observatory", "sunqua-peak", "silent-surf", "lonely-tower", "kinfall"]},
    {"key": "strikes", "name": "Strikes", "label": "Strike-CM", "mode": "Strike Challenge Mode", "players": "10 Spieler",
     "intro": "Die Challenge Modes der Strike Missions (10 Spieler).",
     "guides": ["aetherblade-hideout"]},
    {"key": "raids", "name": "Raids", "label": "Raid", "mode": "Raid", "players": "10 Spieler",
     "intro": "Alle Raid-Wings mit jedem Boss (10 Spieler).",
     "guides": ["wing-1-spirit-vale", "wing-2-salvation-pass", "wing-3-stronghold-of-the-faithful", "wing-4-bastion-of-the-penitent",
                "wing-5-hall-of-chains", "wing-6-mythwright-gambit", "wing-7-key-of-ahdashim", "wing-8-mount-balrior"]},
]
CAT_OF = {g: c for c in CATS for g in c["guides"]}
ABOUT = {"cm": "Für alle, die den Normal Mode kennen: Jeder Guide beginnt mit dem, was im Challenge Mode neu ist, danach kommen alle Mechaniken im Detail und Klassentipps.",
         "raids": "Ein Guide pro Wing: zu jedem Boss erst das Wichtigste, dann die Details zum Nachschlagen – bei Bossen mit Challenge Mode zusätzlich, was im CM neu ist. Am Ende Klassen, Rollen und Klassentipps."}
ORDER = [g for c in CATS for g in c["guides"]]
SHORT = {"aetherblade-hideout": "Ätherklingen-Versteck", "nightmare": "Nightmare", "shattered-observatory": "Shattered Observatory",
         "sunqua-peak": "Sunqua Peak", "silent-surf": "Silent Surf", "lonely-tower": "Lonely Tower", "kinfall": "Kinfall",
         "wing-1-spirit-vale": "Wing 1 · Spirit Vale", "wing-2-salvation-pass": "Wing 2 · Salvation Pass",
         "wing-3-stronghold-of-the-faithful": "Wing 3 · Stronghold of the Faithful", "wing-4-bastion-of-the-penitent": "Wing 4 · Bastion of the Penitent",
         "wing-5-hall-of-chains": "Wing 5 · Hall of Chains", "wing-6-mythwright-gambit": "Wing 6 · Mythwright Gambit",
         "wing-7-key-of-ahdashim": "Wing 7 · Key of Ahdashim", "wing-8-mount-balrior": "Wing 8 · Mount Balrior"}
# Name im Menü und bei "Vorheriger/Nächster Guide"
def NAME(s): return SHORT[s] if s.startswith("wing-") else SHORT[s] + " CM"
PROF_COLOR = {"Wächter": "#72c1d9", "Widergänger": "#d16e5a", "Krieger": "#ffd166", "Ingenieur": "#d09c59", "Waldläufer": "#8cdc82",
              "Dieb": "#c08f95", "Elementarmagier": "#f68a87", "Mesmer": "#b679d5", "Nekromant": "#52a76f"}
BADGE = {"DPS": "red", "Heal-Support": "green", "Boon-Support": "blue", "Boon-DPS": "blue", "Support": "blue", "Heal": "green"}
# Rollen-Schilder in den Raid-Guides (Stichwort im Namen -> Farbe)
RBADGE = [("heal", "green"), ("support", "blue"), ("quick", "blue"), ("alac", "blue"), ("stabi", "blue"), ("reflect", "blue"), ("projektil", "blue"),
          ("dps", "red"), ("power", "red"), ("condi", "red"), ("burst", "red"), ("confusion", "red")]

e = lambda t: html.escape(str(t or ""), quote=True)
SUPPORT = "https://www.paypal.com/paypalme/nerdpublicgaming93"   # Spendenlink (Menüpunkt "Unterstütze mich gerne!")

def webify(h):
    """PDF-Verweise an die Webseite anpassen."""
    h = h.replace("(Details S. 2)", "(Details weiter unten)").replace("Details S. 2", "Details weiter unten")
    h = h.replace("Dann reicht diese Seite.", "Dann reicht der erste Abschnitt.")
    return h

def header(prefix, active=""):
    cur = ' aria-current="page"'
    groups = ""
    for c in CATS:
        links = "".join(f'<a href="{prefix}{c["key"]}/{s}.html"{cur if s == active else ""}>{e(NAME(s))}</a>' for s in c["guides"])
        if not links: links = '<span class="dd-empty">kommt bald</span>'
        groups += f'<div class="dd-group"><a class="dd-head" href="{prefix}{c["key"]}/index.html">{e(c["name"])}</a>{links}</div>'
    return f'''<header class="nav">
  <a class="brand" href="{prefix}index.html" aria-label="NerdPublic Gaming – Start">
    <img src="{prefix}assets/logo-round.png" alt="" width="44" height="44">
    <span>NerdPublic <b>Gaming</b></span>
  </a>
  <nav class="links" aria-label="Hauptmenü">
    <a href="{prefix}index.html#stream">Stream</a>
    <a href="{prefix}index.html#videos">Videos</a>
    <a href="{prefix}index.html#clips">Clips</a>
    <div class="dd">
      <button type="button" class="dd-btn" aria-expanded="false" aria-controls="ddMenu">GW2 Guides <span aria-hidden="true">▾</span></button>
      <div class="dd-menu" id="ddMenu">
        <a class="dd-all" href="{prefix}guides/index.html">Alle GW2-Guides</a>
        <div class="dd-groups">{groups}</div>
      </div>
    </div>
    <a class="lock-link" href="{prefix}sc-logs/index.html"><svg class="lk" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5zm-3 8V7a3 3 0 0 1 6 0v3H9z"/></svg>SC-Logs</a>
    <a href="{prefix}insta.html"{cur if active == "insta" else ""}><span class="nav-long">Phils </span>Insta<span class="nav-long"> inc. Dog-Pics!</span></a>
    <a href="{prefix}index.html#about">Über mich</a>
    <a class="support-link" href="{SUPPORT}" target="_blank" rel="noopener" title="Unterstütze mich gerne! (PayPal)"><svg class="lk" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 2.9 4.5 6.6 4.5c2.1 0 3.9 1.2 5.4 3.1 1.5-1.9 3.3-3.1 5.4-3.1 3.7 0 5.7 3.9 4.2 7.3C19.5 16.4 12 21 12 21z"/></svg><span class="nav-long">Unterstütze mich gerne!</span><span class="nav-short">Unterstützen</span></a>
  </nav>
</header>'''

def footer(prefix):
    return f'''<footer class="foot band">
  <p>© <span class="year">2026</span> NerdPublic Gaming · <a href="{prefix}impressum.html">Impressum</a> · <a href="{prefix}datenschutz.html">Datenschutz</a></p>
  <p class="fine">Guild Wars 2 ist eine Marke von ArenaNet, LLC. Diese Seite ist ein Fanprojekt und steht in keiner Verbindung zu ArenaNet oder NCSOFT.</p>
</footer>
<script src="{prefix}nav.js"></script>'''

def page(title, desc, prefix, body, active=""):
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} – NerdPublic Gaming</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="{prefix}assets/favicon.png">
<link rel="stylesheet" href="{prefix}style.css">
<link rel="stylesheet" href="{prefix}guide.css">
</head>
<body class="guide-page">
{header(prefix, active)}
<main>
{body}
</main>
{footer(prefix)}
</body>
</html>
'''

def table_html(t, kind):
    head = "".join(f"<th>{e(h)}</th>" for h in t["head"])
    rows = ""
    if kind == "popular":
        vals = [float(re.sub(r"[^\d,]", "", r[1]).replace(",", ".") or 0) for r in t["rows"]]
        mx = max(vals) or 1
        for r, v in zip(t["rows"], vals):
            rows += f'<tr><td>{e(r[0])}</td><td class="num">{e(r[1])}</td><td class="barcell"><span class="bar" style="width:{v / mx * 100:.0f}%"></span></td></tr>'
        return f'<table class="tbl pop"><thead><tr>{head}<th aria-hidden="true"></th></tr></thead><tbody>{rows}</tbody></table>'
    if kind == "roles":
        for r in t["rows"]:
            b = r[0]
            col = next((v for k, v in BADGE.items() if b["badge"].startswith(k)), "gold")
            rows += f'<tr><td data-l="Rolle"><span class="badge {col}">{e(b["badge"])}</span> {e(b["text"])}</td><td data-l="Specs">{e(r[1])}</td><td data-l="Warum">{e(r[2])}</td></tr>'
        return f'<table class="tbl roles stack"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
    for r in t["rows"]:
        rows += "<tr>" + "".join(f'<td{" class=num" if i else ""}>{e(c)}</td>' for i, c in enumerate(r)) + "</tr>"
    return f'<div class="scroll"><table class="tbl dps"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'

def prevnext(prev, nxt):
    pn = f'<a class="pn prev" href="{prev}.html"><small>Vorheriger Guide</small>{e(NAME(prev))}</a>' if prev else "<span></span>"
    if nxt: pn += f'<a class="pn next" href="{nxt}.html"><small>Nächster Guide</small>{e(NAME(nxt))}</a>'
    return pn

def guide_html(g, prev, nxt):
    s = g["slug"]; P = "../"
    img = lambda n: f"{P}assets/fraktale/{n}"
    cat = CAT_OF[s]
    pdf = f"{P}guides/{cat['key']}/{s}-cm.pdf"
    hard = next((x["url"] for x in g["sources"] if "hardstuck" in x["url"]), "")
    chips = "".join(f"<li>{e(c)}</li>" for c in g["chips"])
    tl = "".join(f'<li style="--c:{t["color"]}"><b>{e(t["label"])}</b><span>{e(t["desc"])}</span></li>' for t in g["timeline"])
    rules = "".join(f'<article class="rule parchment{" wide" if r["wide"] else ""}"><span class="rn">{r["n"]}</span><div><h3>{e(r["title"])}</h3><p>{webify(r["html"])}</p></div></article>' for r in g["rules"])
    figs = "".join(f'<figure><img src="{img(f["img"])}" alt="{e(f["caption"])}" loading="lazy"><figcaption>{e(f["caption"])}</figcaption></figure>' for f in g["figures"])
    det = ""
    for i, d in enumerate(g["details"]):
        ims = "".join(f'<figure><img src="{img(x["img"])}" alt="{e(x["caption"])}" loading="lazy"><figcaption>{e(x["caption"])}</figcaption></figure>' for x in d["imgs"])
        body, ul = "", []
        def flush():
            nonlocal body, ul
            if ul: body += "<ul>" + "".join(f"<li>{webify(x)}</li>" for x in ul) + "</ul>"; ul = []
        boxes = []
        for it in d["items"]:
            if it["t"] == "li":
                if boxes: body += '<div class="boxes">' + "".join(f'<div class="box">{b}</div>' for b in boxes) + "</div>"; boxes = []
                ul.append(it["html"])
            elif it["t"] == "h":
                flush()
                if boxes: body += '<div class="boxes">' + "".join(f'<div class="box">{b}</div>' for b in boxes) + "</div>"; boxes = []
                body += f'<h4>{re.sub("</?strong>", "", it["html"])}</h4>'
            else:
                flush(); boxes.append(it["html"])
        flush()
        if boxes: body += '<div class="boxes">' + "".join(f'<div class="box">{b}</div>' for b in boxes) + "</div>"
        det += f'''<section class="det parchment" id="det-{i + 1}"><h3>{e(d["title"])}</h3>
  <div class="det-grid{" noimg" if not ims else ""}">{f'<div class="det-imgs">{ims}</div>' if ims else ""}<div class="det-body">{body}</div></div></section>'''
    c = g["classes"]
    tabs = c["tables"]
    pop = next((t for t in tabs if t["title"].startswith("Am häufigsten")), None)
    dps = next((t for t in tabs if t["title"].startswith("Höchster")), None)
    roles = next((t for t in tabs if t["title"].startswith("Rollen")), None)
    profs = "".join(f'''<article class="prof" style="--pc:{PROF_COLOR.get(p["name"], "#e3b75a")}"><h3>{e(p["name"])}</h3><p class="specs">{e(p["specs"])}</p>
      <ul>{"".join(f"<li>{x}</li>" for x in p["items"])}</ul></article>''' for p in c["profs"])
    srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener">{e(x["text"])}</a>' for x in g["sources"])
    pn = prevnext(prev, nxt)
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <a href="../guides/index.html">GW2 Guides</a> › <a href="index.html">{e(cat["name"])}</a> › <span>{e(g["title"])}</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2 · {e(cat["mode"])} · {e(cat["players"])}</p>
    <h1>{e(g["title"])}</h1>
    <p class="sub">{e(webify(g["subtitle"]))}</p>
    <ul class="chips">{chips}</ul>
    <div class="g-actions">
      <a class="btn btn-gold" href="{pdf}" target="_blank" rel="noopener"><svg class="btn-bg" aria-hidden="true" viewBox="0 0 400 60" preserveAspectRatio="none"><path d="M6 34 C40 14 90 10 150 12 C230 8 300 6 352 14 C380 18 396 26 392 36 C386 48 330 52 260 50 C190 52 110 54 50 50 C20 48 2 44 6 34Z"/></svg>Als PDF (zum Ausdrucken)</a>
      {f'<a class="ghost" href="{e(hard)}" rel="noopener">Ganzer Guide auf Hardstuck →</a>' if hard else ""}
    </div>
  </div>
</section>
<nav class="toc scroll band" aria-label="Abschnitte">
  <a href="#neu">Nur das Neue</a><a href="#details">Details</a><a href="#klassen">Klassen & Rollen</a><a href="#tipps">Klassentipps</a>
</nav>

<section class="band" id="neu">
  <h2 class="brush">Nur das Neue im CM</h2>
  <ol class="timeline">{tl}</ol>
  <div class="rules">{rules}</div>
  {f'<div class="figs">{figs}</div>' if figs else ""}
</section>

<section class="band band-dark" id="details">
  <h2 class="brush">Details zum Nachschlagen</h2>
  <div class="dets">{det}</div>
</section>

<section class="band" id="klassen">
  <h2 class="brush">Klassen & Rollen</h2>
  <p class="meta">{e(re.sub("<[^>]+>", "", c["meta"]).replace("M,A.M.A.", "M.A.M.A."))}</p>
  <div class="cl-grid">
    {f'<div class="panel"><h3>{e(pop["title"])}</h3>{table_html(pop, "popular")}</div>' if pop else ""}
    {f'<div class="panel"><h3>{e(dps["title"])}</h3>{table_html(dps, "dps")}</div>' if dps else ""}
  </div>
  {f'<div class="panel"><h3>{e(roles["title"])}</h3>{table_html(roles, "roles")}</div>' if roles else ""}
  {f'<p class="tip">{c["tip"]}</p>' if c["tip"] else ""}
</section>

<section class="band band-dark" id="tipps">
  <h2 class="brush">Klassentipps – worauf du achten musst</h2>
  <p class="meta">{e(c["intro"])}</p>
  <div class="profs">{profs}</div>
</section>

<section class="band">
  <p class="srcs fine">Bilder & Mechaniken: {srcs}</p>
  <div class="prevnext">{pn}</div>
</section>'''
    return page(g["title"] + " Guide", f'{g["title"]}: was im Challenge Mode neu ist, alle Mechaniken und Klassentipps – kompakt auf Deutsch.', P, body, s)

def rbadge(name):
    n = name.lower()
    return next((c for k, c in RBADGE if k in n), "gold")

def boss_id(b):
    return "b-" + re.sub(r"[^a-z0-9]+", "-", (b["title"] + (" cm" if b["cm"] else "")).lower()).strip("-")

def raid_html(g, prev, nxt):
    s = g["slug"]; P = "../"
    img = lambda n: f"{P}assets/raids/{n}"
    cat = CAT_OF[s]
    pdf = f"{P}guides/raids/{s}.pdf"
    bosses = g["boss_list"]
    names = [b["title"] for b in bosses if not b["cm"]]
    toc = "".join(f'<a href="#{boss_id(b)}">{e(b["title"])}{" CM" if b["cm"] else ""}</a>' for b in bosses)
    secs = ""
    for b in bosses:
        bid = boss_id(b)
        chips = "".join(f'<li{"" if c["hot"] else " class=cool"}>{e(c["text"])}</li>' for c in b["chips"])
        tl = "".join(f'<li style="--c:{t["color"]}"><b>{e(t["label"])}</b><span>{e(t["desc"])}</span></li>' for t in b["timeline"])
        rules = "".join(f'<article class="rule parchment{" wide" if r["wide"] else ""}"><span class="rn">{r["n"]}</span><div><h3>{e(r["title"])}</h3><p>{r["html"]}</p></div></article>' for r in b["rules"])
        figs = "".join(f'<figure><img src="{img(f["img"])}" alt="{e(f["caption"])}" loading="lazy"><figcaption>{e(f["caption"])}</figcaption></figure>' for f in b["figures"])
        srcs = e(b["note"]).replace("Klassentipps auf der letzten Seite", "Klassentipps weiter unten")
        for x in b["sources"]:
            srcs = srcs.replace(e(x["text"]), f'<a href="{e(x["url"])}" rel="noopener">{e(x["text"])}</a>', 1)
        kick = "Challenge Mode · nur das Neue" if b["cm"] else "Normal Mode · das Wichtigste"
        title = f'{e(b["title"])} <span class="cm-tag">CM</span>' if b["cm"] else e(b["title"])
        secs += f'''
<section class="band boss{" boss-cm" if b["cm"] else ""}" id="{bid}">
  <div class="boss-head">
    <p class="kick">{kick}</p>
    <h2 class="brush">{title}</h2>
    <p class="boss-sub">{e(b["subtitle"])}</p>
    <ul class="chips">{chips}</ul>
  </div>
  <ol class="timeline n" style="--n:{max(len(b["timeline"]), 1)}">{tl}</ol>
  <div class="rules">{rules}</div>
  {f'<div class="figs">{figs}</div>' if figs else ""}
  {f'<p class="srcs fine boss-src">{srcs}</p>' if srcs else ""}
</section>'''
        if b["details"]:
            dets = ""
            for d in b["details"]:
                ul = "".join(f'<li>{it["html"]}</li>' for it in d["items"])
                dets += f'<section class="det parchment"><h3>{e(d["title"])}</h3><ul>{ul}</ul></section>'
            secs += f'''
<section class="band band-dark boss-det">
  <h3 class="det-title">{e(b["title"])} – Details zum Nachschlagen</h3>
  <div class="det-cols">{dets}</div>
</section>'''
    c = g["classes"]
    t1, t2 = c["tables"]
    rows1 = "".join(f'<tr><td data-l="Boss"><b>{e(r[0]["name"])}</b><small>{e(r[0]["sub"])}</small></td><td data-l="{e(t1["head"][1])}">{e(r[1])}</td><td data-l="{e(t1["head"][2])}">{e(r[2])}</td></tr>' for r in t1["rows"])
    strip = lambda h: re.sub("</?strong>", "", h)
    rows2 = "".join(f'<tr><td data-l="Rolle"><span class="badge {rbadge(r[0]["badge"])}">{e(r[0]["badge"])}</span></td><td data-l="Specs"><b>{e(strip(r[1]))}</b></td><td data-l="Warum">{r[2]}</td></tr>' for r in t2["rows"])
    profs = "".join(f'''<article class="prof" style="--pc:{PROF_COLOR.get(p["name"], "#e3b75a")}"><h3>{e(p["name"])}</h3><p class="specs">{e(p["specs"])}</p>
      <ul>{"".join(f"<li>{x}</li>" for x in p["items"])}</ul></article>''' for p in c["profs"])
    sub = f'{", ".join(names[:-1])} und {names[-1]}' if len(names) > 1 else names[0]
    hchips = "".join(f'<li>{e(b["title"])}{" CM" if b["cm"] else ""}</li>' for b in bosses)
    th1 = "".join(f"<th>{e(h)}</th>" for h in t1["head"])
    th2 = "".join(f"<th>{e(h)}</th>" for h in t2["head"])
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <a href="../guides/index.html">GW2 Guides</a> › <a href="index.html">{e(cat["name"])}</a> › <span>{e(g["title"])}</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2 · Raid · Wing {g["wing"]} · {e(cat["players"])}</p>
    <h1>{e(g["title"])}</h1>
    <p class="sub">{e(sub)} – zu jedem Boss das Wichtigste, Details zum Nachschlagen und am Ende Klassen, Rollen und Klassentipps.</p>
    <ul class="chips">{hchips}</ul>
    <div class="g-actions">
      <a class="btn btn-gold" href="{pdf}" target="_blank" rel="noopener"><svg class="btn-bg" aria-hidden="true" viewBox="0 0 400 60" preserveAspectRatio="none"><path d="M6 34 C40 14 90 10 150 12 C230 8 300 6 352 14 C380 18 396 26 392 36 C386 48 330 52 260 50 C190 52 110 54 50 50 C20 48 2 44 6 34Z"/></svg>Als PDF (zum Ausdrucken)</a>
    </div>
  </div>
</section>
<nav class="toc scroll band" aria-label="Abschnitte">
  {toc}<a href="#klassen">Klassen & Rollen</a><a href="#tipps">Klassentipps</a>
</nav>
{secs}

<section class="band" id="klassen">
  <h2 class="brush">Klassen & Rollen</h2>
  <p class="meta">{e(c["meta"])}</p>
  <div class="panel"><h3>Was laut Wingman funktioniert</h3>
    <table class="tbl raid-bosses stack"><thead><tr>{th1}</tr></thead><tbody>{rows1}</tbody></table></div>
  <div class="panel"><h3>{e(c["title2"])}</h3>
    <table class="tbl roles stack"><thead><tr>{th2}</tr></thead><tbody>{rows2}</tbody></table></div>
  {f'<p class="tip">{c["tip"]}</p>' if c["tip"] else ""}
</section>

<section class="band band-dark" id="tipps">
  <h2 class="brush">Klassentipps – worauf du achten musst</h2>
  <p class="meta">{e(c["intro"])}</p>
  <div class="profs">{profs}</div>
</section>

<section class="band">
  <div class="prevnext">{prevnext(prev, nxt)}</div>
</section>'''
    return page(g["title"] + " – Raid-Guide", f'{g["title"]}: {sub} – Mechaniken, Details und Klassentipps für den Raid, kompakt auf Deutsch.', P, body, s)

def card(g, href):
    c = CAT_OF[g["slug"]]
    return f'''<a class="ov parchment" href="{href}">
  <div class="cover"><img src="../assets/guides/{g["slug"]}.jpg" alt="" loading="lazy"></div>
  <div class="ov-top"><p class="kicker">{e(c["label"])}</p><h3>{e(g["title"])}</h3><p class="sub">{e(g["bosses"])}</p></div>
  <p>{e(g["summary"])}</p>
  <ul class="chips dark">{"".join(f"<li>{e(x)}</li>" for x in g["chips"])}</ul>
  <span class="open">Guide öffnen →</span>
</a>'''

SRC_NOTE = '''<p class="fine srcs">Mechaniken nach den Guides von <a href="https://hardstuck.gg/gw2/guides/" rel="noopener">Hardstuck</a>,
    Klassendaten von <a href="https://gw2wingman.nevermindcreations.de/" rel="noopener">GW2 Wingman</a>.</p>'''

def empty_note(c):
    one = {"fraktale": "Fraktal", "strikes": "Strike", "raids": "Raid"}.get(c["key"], c["name"])
    return f'<p class="empty-cat parchment">Noch keine {e(one)}-Guides – die kommen bald.</p>'

def overview(c, gs):
    cards = "".join(card(g, f'{g["slug"]}.html') for g in gs) or empty_note(c)
    tabs = "".join(f'<a href="../{x["key"]}/index.html"{" aria-current=\"page\"" if x is c else ""}>{e(x["name"])}</a>' for x in CATS)
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <a href="../guides/index.html">GW2 Guides</a> › <span>{e(c["name"])}</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2 · Guides</p>
    <h1>{e(c["name"])}</h1>
    <p class="sub">{e(c["intro"])} {e(ABOUT.get(c["key"], ABOUT["cm"]))}</p>
  </div>
</section>
<nav class="toc scroll band cat-tabs" aria-label="Kategorien">{tabs}</nav>
<section class="band">
  <div class="ovs">{cards}</div>
  {SRC_NOTE if gs else ""}
</section>'''
    return page(f'{c["name"]} – GW2 Guides', f'Guild Wars 2 {c["name"]}: kompakte Guides auf Deutsch – was im Challenge Mode neu ist, Mechaniken, Klassentipps.', "../", body)

def hub(by_cat):
    secs = ""
    for c in CATS:
        gs = by_cat[c["key"]]
        cards = "".join(card(g, f'../{c["key"]}/{g["slug"]}.html') for g in gs) or empty_note(c)
        secs += f'''<section class="band" id="{c["key"]}">
  <div class="sec-head"><h2 class="brush">{e(c["name"])}</h2><a class="more" href="../{c["key"]}/index.html">Alle {e(c["name"])} →</a></div>
  <p class="cat-intro">{e(c["intro"])}</p>
  <div class="ovs">{cards}</div>
</section>'''
    tabs = "".join(f'<a href="#{c["key"]}">{e(c["name"])} ({len(by_cat[c["key"]])})</a>' for c in CATS)
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <span>GW2 Guides</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2</p>
    <h1>GW2 Guides</h1>
    <p class="sub">Kompakte Guides auf Deutsch – sortiert nach Fraktalen, Strikes und Raids.</p>
  </div>
</section>
<nav class="toc scroll band cat-tabs" aria-label="Kategorien">{tabs}</nav>
{secs}
<section class="band">{SRC_NOTE}</section>'''
    return page("GW2 Guides", "Guild Wars 2 Guides auf Deutsch: Fraktale, Strikes und Raids.", "../", body)

def redirect(target):
    return f'''<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>Weitergeleitet</title>
<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}"></head>
<body><p>Diese Seite ist umgezogen: <a href="{target}">{target}</a></p></body></html>
'''

def sync_headers():
    """Menü in den übrigen Seiten auf den aktuellen Stand bringen."""
    for f, prefix in [("index.html", ""), ("impressum.html", ""), ("datenschutz.html", ""), ("insta.html", ""), ("sc-logs/index.html", "../")]:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p): continue
        t = open(p, encoding="utf-8").read()
        t2 = re.sub(r'<header class="nav">.*?</header>', lambda m: header(prefix, "insta" if f == "insta.html" else ""), t, count=1, flags=re.S)
        if t2 != t: open(p, "w", encoding="utf-8").write(t2)

if __name__ == "__main__":
    meta = {re.sub(r"(-cm)?\.pdf$", "", x["pdf"].split("/")[-1]): x for x in json.load(open(os.path.join(ROOT, "data", "guides.json"), encoding="utf-8"))}
    by_cat = {c["key"]: [] for c in CATS}
    for c in CATS:
        os.makedirs(os.path.join(ROOT, c["key"]), exist_ok=True)
        for s in c["guides"]:
            g = json.load(open(os.path.join(RAIDS if c["key"] == "raids" else CONTENT, s + ".json"), encoding="utf-8"))
            if c["key"] == "raids":
                g["title"] = SHORT[s]
                g["boss_list"] = g["bosses"]
                g["chips"] = meta.get(s, {}).get("tags", [])
            g["bosses"] = meta.get(s, {}).get("bosses", "")
            g["summary"] = meta.get(s, {}).get("summary", "")
            by_cat[c["key"]].append(g)
        gs = by_cat[c["key"]]
        for i, g in enumerate(gs):
            prev = gs[i - 1]["slug"] if i > 0 else None
            nxt = gs[i + 1]["slug"] if i + 1 < len(gs) else None
            html_ = raid_html(g, prev, nxt) if c["key"] == "raids" else guide_html(g, prev, nxt)
            open(os.path.join(ROOT, c["key"], g["slug"] + ".html"), "w", encoding="utf-8").write(html_)
        open(os.path.join(ROOT, c["key"], "index.html"), "w", encoding="utf-8").write(overview(c, gs))
    os.makedirs(os.path.join(ROOT, "guides"), exist_ok=True)
    open(os.path.join(ROOT, "guides", "index.html"), "w", encoding="utf-8").write(hub(by_cat))
    # alte Adressen von Guides, die die Kategorie gewechselt haben, weiterleiten
    for c in CATS:
        if c["key"] != "strikes": continue  # nur Guides, die früher unter Fraktale lagen
        for s in c["guides"]:
            open(os.path.join(ROOT, "fraktale", s + ".html"), "w", encoding="utf-8").write(redirect(f"../{c['key']}/{s}.html"))
    sync_headers()
    print("OK:", ", ".join(f'{c["name"]} {len(by_cat[c["key"]])}' for c in CATS), "+ Übersichten, Menü aktualisiert")
