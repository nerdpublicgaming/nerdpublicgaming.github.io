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
4. **Settings → Pages:** Source „Deploy from a branch“, Branch `main`, Ordner `/ (root)`.
5. **Actions → „Videos, Clips und Live-Status aktualisieren“ → Run workflow** – einmal manuell starten.

## Inhalte pflegen
- Neuer Guide: Eintrag in `data/guides.json` ergänzen (`url` zeigt auf die Guide-Seite).
- Impressum und Datenschutz in `impressum.html` / `datenschutz.html` ausfüllen.

## Fraktal-CM-Guides
- Übersicht: `fraktale/index.html`, jeder Guide hat eine eigene Seite unter `fraktale/`.
- Die Texte stehen in `content/fraktale/<name>.json`. Nach einer Änderung im Hauptordner
  `python scripts/build-guides.py` ausführen, dann werden die Seiten neu erzeugt.
- Die PDFs liegen weiter unter `guides/fraktale/` und sind auf jeder Guide-Seite als Download verlinkt.
