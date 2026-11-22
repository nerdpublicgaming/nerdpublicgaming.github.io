# NerdPublic Gaming – Homepage

Statische Seite (HTML/CSS/JS). Videos, Clips und Live-Status kommen aus `data/feed.json`,
die eine GitHub Action alle 20 Minuten neu schreibt. Guides stehen in `data/guides.json`.

## Einrichtung (einmalig)
1. Neues Repository auf GitHub anlegen und alle Dateien hochladen (inkl. Ordner `.github`).
2. **Twitch-App registrieren:** https://dev.twitch.tv/console/apps → „Register Your Application“
   - Name: z. B. `npg-homepage`, OAuth Redirect URL: `http://localhost`, Kategorie: Website Integration
   - Client-ID kopieren, „New Secret“ erzeugen und kopieren.
3. Im Repository: **Settings → Secrets and variables → Actions → New repository secret**
   - `TWITCH_CLIENT_ID` und `TWITCH_CLIENT_SECRET` eintragen.
4. **Settings → Pages:** bei Source „GitHub Actions“ wählen.
5. **Actions → „Videos, Clips und Live-Status aktualisieren“ → Run workflow** – einmal manuell starten.

## Inhalte pflegen
- Neuer Guide: Eintrag in `data/guides.json` ergänzen (`url` zeigt auf die Guide-Seite).
- Impressum und Datenschutz in `impressum.html` / `datenschutz.html` ausfüllen.

## GW2-Guides (Fraktale, Strikes, Raids)
- Übersicht aller Guides: `guides/index.html`; je Kategorie `fraktale/`, `strikes/`, `raids/` mit eigener Übersicht.
- Welcher Guide in welche Kategorie gehört, steht oben in `scripts/build-guides.py` (CATS).
- Die Texte stehen in `content/fraktale/<name>.json`. Nach einer Änderung im Hauptordner
  `python scripts/build-guides.py` ausführen, dann werden die Seiten neu erzeugt.
- Die PDFs liegen weiter unter `guides/fraktale/` und sind auf jeder Guide-Seite als Download verlinkt.

## Seite aktualisieren (GitHub Desktop)
1. Zuerst **Fetch origin** und dann **Pull origin** klicken – die Automatik speichert regelmäßig neue Videos/Clips, die müssen erst geholt werden.
2. Dateien im Repository-Ordner ändern.
3. Summary eintragen → **Commit to main** → **Push origin**. Die Seite ist 1–2 Minuten später aktuell.

## SC-Logs (passwortgeschützt)
- Seite: `sc-logs/index.html`, Inhalte verschlüsselt in `sc-logs/data/` (AES-256-GCM, Schlüssel per PBKDF2 aus dem Passwort).
- Die **unverschlüsselten Quellen** liegen NICHT im Repository, sondern privat in `D:\downloads\homepage\sc-logs-quelle`
  (`abende/*.json`, `lese-guide.json`, `bilder/`, `pdf/`). Diesen Ordner nie ins Repository kopieren!
- Neu verschlüsseln (z. B. neuer Abend oder neues Passwort):
  `pip install cryptography` und dann `python scripts/build-logs.py "D:\downloads\homepage\sc-logs-quelle"` – das Passwort wird abgefragt.
