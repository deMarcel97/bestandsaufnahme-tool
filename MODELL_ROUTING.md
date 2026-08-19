# MODELL_ROUTING.md

**Zweck:** Diese Datei definiert, welches Modell/Tool für welche Aufgabe verwendet wird.
Claude liest diese Datei bei Projektstart und wendet die Regeln automatisch an,
ohne Rückfrage — außer die Aufgabe ist eindeutig nicht zuordenbar.

Diese Datei ist bewusst lokal/untracked (wie `deploy/server.local.env`) — sie
ergänzt nur die Modellwahl, sie ersetzt nichts.

## Gemeinsame Basis (gilt unabhängig davon, wer liest)

Der eigentliche "eine Datei/ein Befehl für jede KI"-Mechanismus existiert
bereits, unabhängig von dieser Datei hier:

- **[ARBEITSWEISE.md](../ARBEITSWEISE.md)** (projektübergreifend) — wie
  Marcel arbeiten will, zum Mitgeben an jedes Tool.
- **`RESUME.md`** im Notizen-Ordner — fertige Copy-Paste-Befehle pro Tool
  (Antigravity, Mistral Vibe), die der Reihe nach `CLAUDE.md` →
  ggf. `HANDOFF_antigravity.md` → `ARBEITSWEISE.md` → `TODO.md`/
  `ARBEITSPROTOKOLL.md` lesen lassen, inkl. Git-Stand-Check vorweg. **Das ist
  der Weg, wenn Marcel manuell ein Tool startet — nicht diese Datei hier.**
- **[CLAUDE.md](CLAUDE.md)** — die verbindlichen Arbeitsregeln;
  [HANDOFF_claude_code.md](HANDOFF_claude_code.md) für den Sitzungseinstieg.

Diese Datei hier dupliziert das nicht, sondern kommt on top: sie regelt,
**welches Modell eine Aufgabe bekommt**, wenn *Claude* delegiert, und **wie
das Ergebnis zurück in Claudes Hände kommt**.

## Aufgabe an ein Modell übergeben (auch manuell, ohne Claude)

**Normalfall:** die nächste offene Karte aus `TODO.md` (Notizen-Ordner) per
`RESUME.md`-Befehl an ein Tool geben — das ist bereits der etablierte Weg.

**Sonderfall:** eine einzelne Aufgabe, die (noch) nicht als Karte in
`TODO.md` steht oder mehr Detail braucht, als der Kartentext hergibt. Dafür
legt Claude eine Auftragsdatei unter `scratch/auftrag_<karten-id>.md` an
(Vorlage: `scratch/auftrag_TEMPLATE.md`) — Kontext, betroffene Dateien,
Akzeptanzkriterien, was nicht angefasst werden soll. `scratch/` ist
gitignored, reine Arbeitsgrundlage, kein Repo-Artefakt.

Damit lässt sich auch so eine Aufgabe **ohne Claude als Vermittler**
zuweisen: Modell wählen, dann `"Lies scratch/auftrag_319.md und setze das
um"` — das Modell hat denselben Stand, den Claude ihm sonst per cli-bridge
gegeben hätte.

## Review-Pflicht nach Delegation

Jedes Ergebnis aus Antigravity oder Mistral Vibe geht vor dem Merge durch
Claude — unabhängig davon, ob Claude die Delegation selbst über cli-bridge
angestoßen hat oder Marcel sie manuell im jeweiligen Tool ausgeführt hat.

- **Immer:** `/code-review` auf den Diff.
- **Zusätzlich `/security-review`**, wenn die Änderung Auth, Datenhaltung,
  Eingabe-Parsing, Vertraulichkeitsstufen (`VertraulichkeitsStufe`) oder
  sonst sicherheitsrelevante Pfade berührt.
- **Auslöser bei manueller Ausführung:** Kein automatischer Check bei
  Sitzungsstart — Marcel sagt explizit Bescheid ("prüf den Diff von agy"),
  erst dann reviewt Claude.
- Befunde werden vor dem Merge behoben oder zumindest an die Superthread-Karte
  kommentiert, nicht stillschweigend übergangen.

---

## REGEL (an Claude)

Du bist der Orchestrator. Für jede Aufgabe aus TODO.md oder aus einem
Superthread-Card:

1. Bestimme den Aufgabentyp anhand der Tabelle unten.
2. Wenn die Aufgabe an ein anderes Tool delegiert werden soll (Mistral Vibe
   oder Antigravity), nutze cli-bridge, um den Befehl auszuführen.
3. Wenn die Aufgabe bei dir selbst (Claude Code) bleibt, wähle das
   angegebene Modell/Effort-Level über die entsprechenden Flags.
4. Zeig vor jeder Delegation an ein anderes Tool kurz an, was du vorhast
   (1 Satz), führe es aus, und fasse das Ergebnis zusammen.
5. Bei Unklarheit über die Zuordnung: Frag kurz nach, statt zu raten.

---

## ROUTING-TABELLE

| Aufgabentyp | Tool | Modell | Effort/Modus | Befehl (via cli-bridge oder direkt) |
|---|---|---|---|---|
| Architektur, Systemdesign, Tech-Stack-Entscheidung | Claude Code | Opus 5 | high | direkt, `--effort high` |
| Komplexer Multi-File-Bug, Security-Audit | Claude Code | Opus 5 | high | direkt, `--effort high` |
| Backend-Coding (API, DB, Business-Logik) | Claude Code | Sonnet 5 | high | direkt, `--effort high` |
| Terminal/Shell/DevOps-Skripte, CI/CD | Claude Code | Sonnet 5 | high | direkt (stärkstes Terminal-Bench-Ergebnis) |
| Code-Review, Refactoring-Vorschläge | Claude Code | Sonnet 5 | medium | direkt |
| Linting, Formatierung, einfache Doku, Boilerplate | Claude Code | Haiku 4.5 | low | direkt, `--effort low` |
| UI/UX-Design, Wireframes, interaktive Prototypen | Antigravity | Gemini 3.7 Flash | fast | cli-bridge → `agy --model gemini-3.7-flash --fast` |
| Komplexe UI-Interaktion, Generative UI, Multi-Step-Reasoning zu Interface | Antigravity | Gemini 2.5 Pro | plan | cli-bridge → `agy --model gemini-2.5-pro` |
| Frontend-Implementierung (React/Vue/Components) | Antigravity | Gemini 3.7 Flash | fast/goal | cli-bridge → `agy --model gemini-3.7-flash --fast` |
| Zweitmeinung zu Code / schnelle alternative Lösung | Mistral Vibe | Medium 3.5 | ask | cli-bridge → `vibe --model medium-3.5` |
| Lange, autonome Multi-File-Debugging-Session | Mistral Vibe | Devstral 2 | code | cli-bridge → `vibe --model devstral-2 --mode code` |
| Dokumentation (API-Docs, User-Guides) | Mistral Vibe | Medium 3.5 | work | cli-bridge → `vibe --model medium-3.5 --mode work` |
| Test-Suite (Unit/Integration/E2E) | Mistral Vibe | Medium 3.5 | code | cli-bridge → `vibe --model medium-3.5 --mode code` |

---

## KURZFASSUNG (Faustregel)

- **Planen, Architektur, harte Bugs, Security** → Opus 5 (Claude selbst, hoher Effort)
- **Normales Coding, Backend, Shell/DevOps** → Sonnet 5 (Claude selbst)
- **Simple/Routine-Sachen (Lint, Doku)** → Haiku 4.5 (Claude selbst, low effort)
- **Alles mit UI/Frontend/Design** → Antigravity / Gemini 3.7 Flash
- **Zweitmeinung, Tests, Doku-Texte** → Mistral Vibe / Medium 3.5
- **Sehr lange autonome Coding-Loops** → Mistral Vibe / Devstral 2

---

## BEISPIEL-ANWENDUNG

Card aus Superthread: "Ändere den Speichern-Button so, dass er nach Klick
einen Ladeindikator zeigt."

→ Aufgabentyp: Frontend-Implementierung
→ Tool: Antigravity, Modell: Gemini 3.7 Flash, Modus: fast
→ Claude führt aus: `agy --model gemini-3.7-flash --fast -p "..."`
→ Ergebnis als Diff zur Review zurück an dich.

Card: "Prüfe, ob die neue Auth-Logik Race-Conditions hat."

→ Aufgabentyp: Komplexer Bug / Security
→ Tool: Claude Code selbst, Modell: Opus 5, Effort: high
→ Claude bearbeitet es direkt, kein Delegieren nötig.
