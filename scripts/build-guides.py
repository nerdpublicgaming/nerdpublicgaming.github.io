#!/usr/bin/env python3
"""Erzeugt die Fraktal-CM-Guide-Seiten aus content/fraktale/*.json.

Aufruf (im Hauptordner der Seite):  python scripts/build-guides.py
Texte ändern: in content/fraktale/<name>.json bearbeiten und das Skript neu starten.
"""
import json, html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "fraktale")
OUT = os.path.join(ROOT, "fraktale")

ORDER = ["aetherblade-hideout", "nightmare", "shattered-observatory", "sunqua-peak", "silent-surf", "lonely-tower", "kinfall"]
SHORT = {"aetherblade-hideout": "Ätherklingen-Versteck", "nightmare": "Nightmare", "shattered-observatory": "Shattered Observatory",
         "sunqua-peak": "Sunqua Peak", "silent-surf": "Silent Surf", "lonely-tower": "Lonely Tower", "kinfall": "Kinfall"}
PROF_COLOR = {"Wächter": "#72c1d9", "Widergänger": "#d16e5a", "Krieger": "#ffd166", "Ingenieur": "#d09c59", "Waldläufer": "#8cdc82",
              "Dieb": "#c08f95", "Elementarmagier": "#f68a87", "Mesmer": "#b679d5", "Nekromant": "#52a76f"}
BADGE = {"DPS": "red", "Heal-Support": "green", "Boon-Support": "blue", "Boon-DPS": "blue", "Support": "blue", "Heal": "green"}

e = lambda t: html.escape(str(t or ""), quote=True)

def webify(h):
    """PDF-Verweise an die Webseite anpassen."""
    h = h.replace("(Details S. 2)", "(Details weiter unten)").replace("Details S. 2", "Details weiter unten")
    h = h.replace("Dann reicht diese Seite.", "Dann reicht der erste Abschnitt.")
    return h

def header(prefix, active=""):
    cur = ' aria-current="page"'
    items = "".join(f'<a href="{prefix}fraktale/{s}.html"{cur if s == active else ""}>{e(SHORT[s])} CM</a>' for s in ORDER)
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
        <p class="dd-head">Fraktal-CMs</p>
        <a class="dd-all" href="{prefix}fraktale/index.html">Alle Fraktal-Guides</a>
        {items}
      </div>
    </div>
    <a href="{prefix}index.html#about">Über mich</a>
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

def guide_html(g, prev, nxt):
    s = g["slug"]; P = "../"
    img = lambda n: f"{P}assets/fraktale/{n}"
    pdf = f"{P}guides/fraktale/{s}-cm.pdf"
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
    pn = ""
    if prev: pn += f'<a class="pn prev" href="{prev}.html"><small>Vorheriger Guide</small>{e(SHORT[prev])} CM</a>'
    else: pn += "<span></span>"
    if nxt: pn += f'<a class="pn next" href="{nxt}.html"><small>Nächster Guide</small>{e(SHORT[nxt])} CM</a>'
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <a href="index.html">Fraktal-CMs</a> › <span>{e(g["title"])}</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2 · Fraktal Challenge Mode</p>
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

def overview(guides):
    cards = ""
    for g in guides:
        s = g["slug"]
        cards += f'''<a class="ov parchment" href="{s}.html">
  <div class="cover"><img src="../assets/guides/{s}.jpg" alt="" loading="lazy"></div>
  <div class="ov-top"><p class="kicker">Fraktal-CM</p><h3>{e(g["title"])}</h3><p class="sub">{e(g["bosses"])}</p></div>
  <p>{e(g["summary"])}</p>
  <ul class="chips dark">{"".join(f"<li>{e(c)}</li>" for c in g["chips"])}</ul>
  <span class="open">Guide öffnen →</span>
</a>'''
    body = f'''
<div class="crumbs band"><a href="../index.html">Start</a> › <span>Fraktal-CMs</span></div>
<section class="g-hero band">
  <div class="g-hero-in">
    <p class="kick">Guild Wars 2 · Guides</p>
    <h1>Fraktal-CM-Guides</h1>
    <p class="sub">Für alle, die den Normal Mode kennen und nur wissen wollen, was im Challenge Mode neu ist.
      Jeder Guide beginnt mit dem Wichtigsten auf einen Blick, danach kommen alle Mechaniken im Detail und Klassentipps.</p>
  </div>
</section>
<section class="band">
  <div class="ovs">{cards}</div>
  <p class="fine srcs">Mechaniken nach den Guides von <a href="https://hardstuck.gg/gw2/guides/" rel="noopener">Hardstuck</a>,
    Klassendaten von <a href="https://gw2wingman.nevermindcreations.de/" rel="noopener">GW2 Wingman</a>.</p>
</section>'''
    return page("Fraktal-CM-Guides", "Alle Guild Wars 2 Fraktal-CMs kompakt auf Deutsch: Was ist neu im Challenge Mode, Mechaniken, Klassentipps.", "../", body)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    meta = {x["pdf"].split("/")[-1].replace("-cm.pdf", ""): x for x in json.load(open(os.path.join(ROOT, "data", "guides.json"), encoding="utf-8"))}
    gs = []
    for s in ORDER:
        g = json.load(open(os.path.join(CONTENT, s + ".json"), encoding="utf-8"))
        g["bosses"] = meta.get(s, {}).get("bosses", "")
        g["summary"] = meta.get(s, {}).get("summary", "")
        gs.append(g)
    for i, g in enumerate(gs):
        prev = ORDER[i - 1] if i > 0 else None
        nxt = ORDER[i + 1] if i + 1 < len(ORDER) else None
        open(os.path.join(OUT, g["slug"] + ".html"), "w", encoding="utf-8").write(guide_html(g, prev, nxt))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(overview(gs))
    print("OK:", len(gs), "Guides + Übersicht")
