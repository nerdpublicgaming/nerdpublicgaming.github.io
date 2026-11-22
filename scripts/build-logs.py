#!/usr/bin/env python3
"""Baut den passwortgeschützten Bereich „SC-Logs“.

Die Auswertungen (Texte, Bilder, PDFs) liegen NICHT im Repository, sondern in einem
privaten Quellordner. Dieses Skript verschlüsselt sie (AES-256-GCM, Schlüssel per
PBKDF2-SHA256 aus dem Passwort) und schreibt nur die verschlüsselten Dateien nach
sc-logs/data/. Ohne Passwort kann niemand die Inhalte lesen – auch nicht, wer die
Dateien direkt herunterlädt.

Aufruf im Hauptordner der Seite:
    pip install cryptography
    python scripts/build-logs.py "D:\\downloads\\homepage\\sc-logs-quelle"
Das Passwort wird abgefragt (oder per Umgebungsvariable SC_LOGS_PASSWORD).

Quellordner:
    abende/<datum-boss>.json   eine Auswertung pro Abend
    lese-guide.json            der Lese-Guide
    bilder/                    Bilder, die in den JSON-Dateien vorkommen
    pdf/                       die Original-PDFs (werden nur gelesen, nie verändert)
"""
import base64, getpass, glob, hashlib, html, json, os, re, shutil, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sc-logs")
DATA = os.path.join(OUT, "data")
ITER = 600_000

e = lambda t: html.escape(str(t if t is not None else ""), quote=True)

# ---------------------------------------------------------------- Verschlüsselung
def derive(password, salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(password.encode("utf-8"))

def seal(key, data: bytes) -> bytes:
    iv = os.urandom(12)
    return iv + AESGCM(key).encrypt(iv, data, None)

# ---------------------------------------------------------------- Bausteine
def tone(p):
    if p is None: return ""
    return "g" if p >= 90 else "y" if p >= 70 else "r"

def bar(p, cls=""):
    if p is None: return ""
    w = min(p, 130) / 130 * 100
    return f'<span class="mbar {cls}"><i class="{tone(p) if not cls else ""}" style="width:{w:.0f}%"></i><b style="left:{100 / 130 * 100:.1f}%"></b></span>'

def pill(t):
    k = {"Top": "top", "Kill": "top", "Okay": "okay", "Reset": "okay", "Baustelle": "bau", "Wipe": "bau"}.get(t, "okay")
    return f'<span class="pill {k}">{e(t)}</span>'

def img_uri(src, name):
    p = os.path.join(src, "bilder", name)
    with open(p, "rb") as f: b = f.read()
    mime = "image/png" if name.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(b).decode()}"

def file_id(slug):
    return "p-" + hashlib.sha256(("page:" + slug).encode()).hexdigest()[:16]

def pdf_id(fname):
    return "pdf-" + hashlib.sha256(fname.encode()).hexdigest()[:16]

def pdf_buttons(pdfs):
    return "".join(f'<button type="button" class="btn btn-gold dl" data-pdf="{pdf_id(p["file"])}" data-name="{e(p["file"])}"><svg class="btn-bg" aria-hidden="true" viewBox="0 0 400 60" preserveAspectRatio="none"><path d="M6 34 C40 14 90 10 150 12 C230 8 300 6 352 14 C380 18 396 26 392 36 C386 48 330 52 260 50 C190 52 110 54 50 50 C20 48 2 44 6 34Z"/></svg>{e(p["label"])}</button>' for p in pdfs)

# ---------------------------------------------------------------- Abend-Seite
def evening_html(a, src):
    kl = " · ".join(f'<a href="{e(k["u"])}" rel="noopener">{e(k["t"])}</a>' for k in a.get("kill_links", []))
    tiles = "".join(f'<div class="tile parchment {t.get("tone", "")}"><span class="tl">{e(t["label"])}</span><span class="tv">{e(t["value"])}</span><span class="ts">{e(t["sub"])}</span></div>' for t in a["tiles"])
    top3 = "".join(f"<li>{x}</li>" for x in a["top3"])
    praise = "".join(f"<p>{x}</p>" for x in a["praise"])
    kt = a["kill_table"]
    krows = ""
    for r in kt["rows"]:
        med = f'{bar(r["pct"])}<span class="mv">{e(r["median"])} / {r["pct"]} %</span>' if r["pct"] is not None else '<span class="muted">–</span>'
        bw = f'<span class="up">{e(r["best"])}</span> <span class="down">{e(r["worst"])}</span>' if r["worst"] else f'<span class="muted">{e(r["best"])}</span>'
        krows += f'''<tr><td data-l="Spieler"><b>{e(r["name"])}</b><small>{e(r["cls"])}</small></td><td data-l="Note">{pill(r["note"])}</td>
<td data-l="Schaden" class="nw">{e(r["dmg"])}</td><td data-l="vs. Median" class="medc">{med}</td><td data-l="▲/▼ Versuch" class="nw">{bw}</td><td data-l="Kurz">{e(r["kurz"])}</td></tr>'''
    att = "".join(f'''<tr><td data-l="Zeit" class="nw">{e(x["time"])}</td><td data-l="Ergebnis">{pill(x["result"])}</td><td data-l="Dauer" class="nw">{e(x["dur"])}</td>
<td data-l="Erreicht">{e(x["reached"])}</td><td data-l="Erster Tod">{e(x["first"])}</td><td data-l="Ursache">{e(x["cause"])}</td><td data-l="Log"><a href="{e(x["log"])}" rel="noopener">Log</a></td></tr>''' for x in a["attempts"])
    slowed = "".join(f"<li>{x}</li>" for x in a["slowed"])
    d = a["development"]
    dhead = "".join(f"<th>{e(c)}</th>" for c in d["cols"])
    drows = ""
    for r in d["rows"]:
        cells = ""
        for i, v in enumerate(r["v"]):
            c = "best" if r.get("best") == i else "worst" if r.get("worst") == i else ""
            cells += f'<td class="num {c}">{e(v)}</td>'
        t = r["trend"]
        tc = "up" if t.startswith("+") else "down" if t.startswith("-") or t.startswith("−") else "muted"
        drows += f'<tr><td><b>{e(r["name"])}</b><small>{e(r["cls"])}</small></td>{cells}<td class="num {tc}">{e(t)}</td></tr>'
    dt = a["detail"]
    drs = ""
    for r in dt["rows"]:
        if r.get("heal"):
            mp = '<span class="muted">– (Heal)</span>'
        else:
            mp = f'''<div class="mp"><span class="lab">Median</span>{bar(r["mpct"])}<span class="mv">{e(r["median"])} / {r["mpct"]} %</span></div>
<div class="mp"><span class="lab">Potenzial</span>{bar(r["ppct"], "pot")}<span class="mv">{e(r["pot"])} / {r["ppct"]} %</span></div>'''
        bw = f'<span class="up">{e(r["best"])}</span><br><span class="down">{e(r["worst"])}</span>' if r["worst"] else f'<span class="muted">{e(r["best"])}</span>'
        drs += f'''<tr><td data-l="Spieler"><b>{e(r["name"])}</b><small>{e(r["cls"])}</small></td><td data-l="Schaden">{e(r["dmg"])}<small>alle Ziele: {e(r["all"])}</small></td>
<td data-l="Median / Potenzial" class="medc">{mp}</td><td data-l="Bester / Schwächster">{bw}</td><td data-l="Anmerkung">{e(r["note"])}</td></tr>'''
    b = a["boons"]
    def bt(v): return f'<span class="{"up" if v >= 90 else "down"}">{v} %</span>'
    brows = "".join(f'<tr><td data-l="Gruppe"><b>{e(r["group"])}</b><small>{e(r["members"])}</small></td><td data-l="Quickness" class="num">{bt(r["quick"])}</td><td data-l="Alacrity" class="num">{bt(r["alac"])}</td><td data-l="Might (Ø Stacks)" class="num">{e(r["might"])}</td></tr>' for r in b["rows"])
    tm = a["time"]
    trows = ""
    for r in tm["rows"]:
        diff = r[3]; dc = "down" if diff.startswith("+") and diff != "+0 s" else "muted"
        bold = ' class="bold"' if len(r) > 4 else ""
        trows += f'<tr{bold}><td data-l="Phase">{e(r[0])}</td><td data-l="Wir" class="num">{e(r[1])}</td><td data-l="Wingman-Median" class="num">{e(r[2])}</td><td data-l="Differenz" class="num {dc}">{e(diff)}</td></tr>'
    bests = "".join(f"<li>{x}</li>" for x in a["bests"])
    shame = "".join(f"<li>{x}</li>" for x in a["shame"])
    guides = "".join(f"<li>{x}</li>" for x in a["guides"])
    kob = img_uri(src, "kobold.jpg")
    return f'''
<section class="g-hero band"><div class="g-hero-in">
  <p class="kick">{e(a["kicker"])}</p>
  <h1>{e(a["title"])}</h1>
  <p class="sub">{e(a["sub"])} · {kl}</p>
  <div class="g-actions">{pdf_buttons(a["pdfs"])}</div>
</div></section>
<nav class="toc scroll band" aria-label="Abschnitte"><a href="#s-kurz">Kurzfassung</a><a href="#s-kill">Spieler im Kill</a><a href="#s-versuche">Alle Versuche</a><a href="#s-entw">Entwicklung</a><a href="#s-detail">Spieler im Detail</a><a href="#s-boons">Boons &amp; Zeit</a><a href="#s-ende">Bestwerte &amp; Guides</a></nav>

<section class="band" id="s-kurz">
  <div class="tiles">{tiles}</div>
  <p class="lead-note">{e(a["note"])}</p>
  <div class="two">
    <div class="parchment card"><h3>Top 3 fürs nächste Mal</h3><ol>{top3}</ol><p class="goal"><strong>Ziel fürs nächste Mal:</strong> {a["goal"]}</p></div>
    <div class="parchment card">{praise}</div>
  </div>
</section>

<section class="band band-dark" id="s-kill">
  <h2 class="brush">{e(kt["title"])}</h2>
  <div class="panel"><table class="tbl lt stack"><thead><tr><th>Spieler</th><th>Note</th><th>Schaden</th><th>vs. Klassen-Median</th><th>▲/▼ Versuch</th><th>Kurz</th></tr></thead><tbody>{krows}</tbody></table>
  <p class="legend">{e(kt["legend"])}</p></div>
</section>

<section class="band" id="s-versuche">
  <h2 class="brush">Alle Versuche</h2>
  <div class="panel"><table class="tbl lt stack"><thead><tr><th>Zeit</th><th>Ergebnis</th><th>Dauer</th><th>Erreicht</th><th>Erster Tod</th><th>Ursache</th><th>Log</th></tr></thead><tbody>{att}</tbody></table></div>
  <h3 class="sub-h">Was gebremst hat</h3>
  <ul class="facts">{slowed}</ul>
</section>

<section class="band band-dark" id="s-entw">
  <h2 class="brush">Entwicklung über die Versuche</h2>
  <p class="lead-note dark">{d["text"]}</p>
  <div class="panel"><div class="scroll"><table class="tbl lt dev"><thead><tr><th>Spieler</th>{dhead}<th>Trend</th></tr></thead><tbody>{drows}</tbody></table></div>
  <p class="legend">{e(d["legend"])}</p></div>
</section>

<section class="band" id="s-detail">
  <h2 class="brush">Spieler im Detail</h2>
  <div class="panel"><table class="tbl lt stack det"><thead><tr><th>Spieler</th><th>Schaden</th><th>Median / Potenzial</th><th>Bester / Schwächster</th><th>Anmerkung</th></tr></thead><tbody>{drs}</tbody></table>
  <p class="legend">{e(dt["legend"])}</p></div>
</section>

<section class="band band-dark" id="s-boons">
  <h2 class="brush">{e(b["title"])}</h2>
  <p class="lead-note dark">{e(b["text"])}</p>
  <div class="panel"><table class="tbl lt stack"><thead><tr><th>Gruppe</th><th>Quickness</th><th>Alacrity</th><th>Might (Ø Stacks)</th></tr></thead><tbody>{brows}</tbody></table>
  <p class="legend">{e(b["legend"])}</p></div>
  <h2 class="brush mt">{e(tm["title"])}</h2>
  <p class="lead-note dark">{tm["text"]}</p>
  <div class="panel"><table class="tbl lt stack"><thead><tr><th>Phase</th><th>Wir</th><th>Wingman-Median</th><th>Differenz</th></tr></thead><tbody>{trows}</tbody></table></div>
</section>

<section class="band" id="s-ende">
  <h2 class="brush">Bestwerte &amp; Schande</h2>
  <div class="two">
    <div class="parchment card"><h3>Persönliche Bestwerte</h3><ul>{bests}</ul></div>
    <div class="parchment card shame"><h3>Wall of Shame</h3><ul>{shame}</ul></div>
  </div>
  <h2 class="brush mt">Guides &amp; Tipps</h2>
  <ul class="facts">{guides}</ul>
  <figure class="kobold"><img src="{kob}" alt="Kobold-Zauberer mit Stab: „{e(a["quote"])}“ – {e(a["quote_by"])}"></figure>
  <p class="thanks">{a["thanks"]}</p>
  <p class="fine center">{e(a["footer"])}</p>
</section>'''

# ---------------------------------------------------------------- Lese-Guide
def guide_html(g, src):
    boxes = "".join(f'<div class="parchment card"><h3>{e(b["title"])}</h3><p>{b["html"]}</p></div>' for b in g["intro_boxes"])
    quick = "".join(f"<li>{x}</li>" for x in g["quick"]["items"])
    parts = ""
    for i, p in enumerate(g["parts"]):
        imgs = "".join(f'<figure class="lgfig"><img src="{img_uri(src, n)}" alt="Beispiel aus der PDF-Auswertung mit nummerierten Pfeilen"></figure>' for n in p["imgs"])
        items = "".join(f"<li>{x}</li>" for x in p["items"])
        extra = ""
        if p.get("callout"): extra += f'<p class="lead-note">{p["callout"]}</p>'
        if p.get("after"):
            extra += f'<h3 class="sub-h">{e(p["after"]["title"])}</h3><ol class="steps">' + "".join(f"<li>{x}</li>" for x in p["after"]["items"]) + "</ol>"
        band = " band-dark" if i % 2 == 0 else ""
        parts += f'''<section class="band{band}" id="teil-{i + 1}">
  <p class="kick">{e(p["kicker"])}</p><h2 class="brush">{e(p["title"])}</h2>
  {f'<p class="lg-intro">{e(p["intro"])}</p>' if p["intro"] else ""}
  {imgs}
  <ol class="numlist">{items}</ol>
  {extra}
</section>'''
    gl = "".join(f"<tr><td data-l=\"Begriff\"><b>{e(a)}</b></td><td data-l=\"Bedeutung\">{e(b)}</td></tr>" for a, b in g["glossary"])
    faq = "".join(f'<div class="parchment card"><h3>{e(q)}</h3><p>{a}</p></div>' for q, a in g["faq"])
    toc = "".join(f'<a href="#teil-{i + 1}">{e(p["title"].split("–")[-1].strip())}</a>' for i, p in enumerate(g["parts"]))
    return f'''
<section class="g-hero band"><div class="g-hero-in">
  <p class="kick">{e(g["kicker"])}</p>
  <h1>{e(g["title"])}</h1>
  <p class="sub">{e(g["sub"])}</p>
  <div class="g-actions">{pdf_buttons([g["pdf"]])}</div>
</div></section>
<nav class="toc scroll band" aria-label="Abschnitte"><a href="#start">Überblick</a>{toc}<a href="#glossar">Begriffe &amp; Fragen</a></nav>
<section class="band" id="start">
  <div class="two">{boxes}</div>
  <h2 class="brush mt">{e(g["quick"]["title"])}</h2>
  <ol class="steps">{quick}</ol>
  <h2 class="brush mt">{e(g["source"]["title"])}</h2>
  <p class="lg-intro">{g["source"]["html"]}</p>
  <figure class="lgfig"><img src="{img_uri(src, g["source"]["img"])}" alt="Kopf der Auswertung als Beispiel"></figure>
  <p class="fine">Die Bilder in diesem Guide zeigen die PDF-Fassung. Auf der Webseite sind die Abschnitte genauso aufgebaut.</p>
</section>
{parts}
<section class="band" id="glossar">
  <p class="kick">Teil 6 · Glossar</p><h2 class="brush">Begriffe &amp; häufige Fragen</h2>
  <div class="panel"><table class="tbl lt stack gloss"><thead><tr><th>Begriff</th><th>Bedeutung</th></tr></thead><tbody>{gl}</tbody></table></div>
  <h3 class="sub-h">Häufige Fragen</h3>
  <div class="two">{faq}</div>
  <p class="thanks">{g["closing"]}</p>
</section>'''

# ---------------------------------------------------------------- Hauptprogramm
def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    pw = os.environ.get("SC_LOGS_PASSWORD") or getpass.getpass("Passwort für SC-Logs: ")
    if len(pw) < 8: sys.exit("Passwort zu kurz (mindestens 8 Zeichen).")

    salt = os.urandom(16)
    key = derive(pw, salt)
    if os.path.isdir(DATA): shutil.rmtree(DATA)
    os.makedirs(DATA)

    def write(name, obj_or_bytes):
        data = obj_or_bytes if isinstance(obj_or_bytes, bytes) else json.dumps(obj_or_bytes, ensure_ascii=False).encode("utf-8")
        with open(os.path.join(DATA, name + ".enc"), "wb") as f: f.write(seal(key, data))

    entries, pdfs = [], set()
    for p in sorted(glob.glob(os.path.join(src, "abende", "*.json")), reverse=True):
        a = json.load(open(p, encoding="utf-8"))
        write(file_id(a["slug"]), {"title": a["title"], "html": evening_html(a, src)})
        entries.append({"slug": a["slug"], "file": file_id(a["slug"]), "date": a["date"], "boss": a["boss"], "title": a["title"], "sub": a["sub"],
                        "tiles": a["tiles"], "goal": re.sub("<[^>]+>", "", a["goal"])})
        pdfs.update(x["file"] for x in a.get("pdfs", []))
    g = None
    lg = os.path.join(src, "lese-guide.json")
    if os.path.exists(lg):
        g = json.load(open(lg, encoding="utf-8"))
        write(file_id("lese-guide"), {"title": g["title"], "html": guide_html(g, src)})
        pdfs.add(g["pdf"]["file"])
    for fname in sorted(pdfs):
        with open(os.path.join(src, "pdf", fname), "rb") as f:   # Original nur lesen
            write(pdf_id(fname), f.read())
    write("index", {"entries": entries, "guide": {"slug": "lese-guide", "file": file_id("lese-guide"), "title": g["title"], "sub": g["sub"]} if g else None})
    meta = {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": base64.b64encode(salt).decode(), "cipher": "AES-256-GCM"}
    json.dump(meta, open(os.path.join(DATA, "meta.json"), "w"), indent=1)
    print(f"OK: {len(entries)} Abend(e), Lese-Guide: {'ja' if g else 'nein'}, {len(pdfs)} PDF(s) verschlüsselt → sc-logs/data/")

if __name__ == "__main__":
    main()
