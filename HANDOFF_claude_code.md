# Projekt-Handoff für Claude Code – Bestandsaufnahme-Tool

## Repo
- Pfad: `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool`
- GitHub: `https://github.com/deMarcel97/bestandsaufnahme-tool` (Branch `main`)
- Stack: FastAPI + Jinja2 + Pydantic v2 + PyYAML, Storage als YAML/JSON-Dateien
- Gebaut wird der App-Code bisher über **Antigravity** aus Spezifikationen; Marcel selbst schreibt keinen Code.

## Was heute (13.08.2026) in der Cowork-Session passiert ist
1. **Aufräumen**: Im Projektordner lag ein kompletter zweiter Git-Klon desselben Repos verschachtelt in einem Unterordner (`bestandsaufnahme-tool/`). War identisch/vollständig gepusht, wurde gelöscht. Der äußere Ordner ist jetzt die einzige Arbeitskopie.
2. **Ist-Zustand-Audit**: Alle 10 Bausteine (Firewall, USV, Serverraum, Netzwerkschrank, Switch, Access Points, M365 Security, Clients, Backup/Storage, Server & Virtualisierung) haben bereits Schema, Regelwerk, Formular und Route. Architektur ist sauber generisch (ein `TechnikObjekt`-Modell, gesteuert über YAML-Schemas, kein Code pro Objekttyp). 54 Tests vorhanden (`tests/`). Fünf Beispiel-Word-Berichte in `exports/` beweisen, dass die Export-Pipeline schon lief.
3. **Bug gefixt** (`app/services/evaluator.py` + `tests/test_evaluator.py`): Unbeantwortete Felder (`unbekannt`, `rueckfrage`, leer, `nicht_relevant`) zählten fälschlich als 0 Punkte und blieben im Nenner – das verzerrte Scores bei Teil-Erfassungen unfair nach unten. Jetzt fallen sie korrekt aus Zähler UND Nenner raus (ursprüngliches Design-Prinzip). Marcel hat bestätigt: das war kein gewolltes Verhalten, sondern ein Bug (vermutlich durch eine spätere Antigravity-Iteration "Fix-Auftrag v6" eingeschlichen).
   - **Wichtig: noch nicht lokal mit `pytest` verifiziert** – im Cowork-Sandbox gab es keinen Internetzugriff, um die Dependencies zu installieren.

## Offene Todos
- **#9 Referenzpreis-Katalog für Massnahmen aufbauen**: Struktur existiert (`app/models/massnahme.py`, `app/web/routes_massnahmen.py`, Felder für Kosten/Priorität/Status), aber nirgends eine Preistabelle. `kosten_quelle` ist überall `"offen"`. Größter kommerzieller Hebel laut Projektziel.
- **#10 Themenblöcke** (organisatorische/prozessuale Interview-Themen, laut Referenzmaterial ~2/3 des echten Assessment-Inhalts) – im Code komplett nicht vorhanden. Für Tool-Version 2 geplant.
- **#11 Lokalen Testlauf verifizieren**: `PYTHONPATH=. pytest` im Projektordner ausführen (venv ist schon vorhanden: `source venv/bin/activate`), Ergebnis gegenchecken – v.a. die neuen/geänderten Tests in `tests/test_evaluator.py`.
- Offene Design-Frage (keine Aktion nötig, nur zur Kenntnis): Wenn ein Baustein aktiviert, aber gar kein Objekt davon erfasst wurde, zählt das weiterhin als 0 Punkte (nicht ausgeschlossen) – bewusst anders behandelt als ein einzelnes unbeantwortetes Feld. Falls das nicht gewünscht ist, separat entscheiden.

## Idee, die gerade getestet werden soll
Antigravity hat eine eigene Terminal-CLI (`agy`, siehe `antigravity.google/docs/cli`). Marcel möchte ausprobieren, ob sich Antigravity von Claude Code aus per Terminal/Bash-Befehl ansteuern lässt (`agy`-Kommandos als Subprozess), um beide Tools im Zusammenspiel zu nutzen.
