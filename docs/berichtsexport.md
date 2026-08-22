# Berichtsexport

Erzeugt strukturierte Kundenberichte als DOCX, Markdown, CSV und Management-Summary mit Vertraulichkeitsfilter.

## Karten

- #292: DOCX-Export (pillow-Abhängigkeit)
- #310: Vertraulichkeitsfilter im Export

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/services/exporter.py` | `ExporterService`-Singleton: alle Export-Formate |
| `app/services/report_builder.py` | `ReportBuilder`-Singleton: baut Analysebericht-Inhalt zusammen |
| `app/web/routes_export.py` | Export-Hub-Route, Download-Endpunkte |
| `app/templates/export/index.html` | Export-Übersichtsseite |

## Funktionsweise

### Export-Formate

| Format | Funktion | Beschreibung |
|---|---|---|
| DOCX | `export_analysebericht_docx` | Vollständiger Analysebericht mit python-docx, inkl. Diagrammen (Pillow) |
| Markdown | `export_analysebericht` | Analysebericht als Markdown |
| Massnahmen MD | `export_massnahmenkatalog_md` | Massnahmenkatalog als Markdown |
| Massnahmen CSV | `export_massnahmenkatalog_csv` | Massnahmenkatalog als CSV |
| Management-Summary | `export_managementsummary` | Kurzzusammenfassung |
| Offene Punkte MD | `export_offene_punkte_md` | Offene Punkte als Markdown |
| Raw JSON | `export_raw_json` | Rohdaten-Export |

### Vertraulichkeitsfilter (#310)

- `VertraulichkeitsStufe`: `intern` -> `kundentauglich` -> `anonymisiert` (absteigende Freigabe).
- Beim Export wird das Ziel (`ziel_vertraulichkeit`) als Parameter übergeben (nicht optional).
- Datensätze mit höherer Vertraulichkeit als das Ziel werden gefiltert.
- Rückfallwerte: für erfasste Datensätze `INTERN`, für Exportziele `ANONYMISIERT` (die schützendste Stufe).
- `ziel_vertraulichkeit` ist keine optionale Angabe mehr -- ein vergessener Aufruf fällt sofort auf.

### Berichtsstruktur

1. **Kapitel 1**: Auftrags- und Kundendaten
2. **Kapitel 2**: Ansprechpartner & Support-Matrix (#321)
3. **Kapitel 3**: Standortübergreifende Infrastruktur & Cloud-Dienste (#315)
4. **Kapitel 4**: Technische Infrastruktur und Fachkapitel (pro Standort)
   - Pro Baustein: Textbausteine aus Schema-Werten
   - Netzwerktopologie als Mermaid-Diagramm (#324)
   - VMs gruppiert unter Host/Cluster
5. **Anhang**: Beobachtungen vor Ort (#316, nur bei Ziel `intern`/`kundentauglich`)
6. **Massnahmenkatalog**: Alle Massnahmen mit Kosten und Dringlichkeit

### Anonymisierung

- Bei Ziel `anonymisiert`: persönliche Daten werden maskiert.
- Freitext-Felder (Beobachtungen vor Ort) entfallen bei anonymisiertem Export.
- `getattr(o, "vertraulichkeit", "intern")` -- Rückfall ist immer die schützendste Stufe.
