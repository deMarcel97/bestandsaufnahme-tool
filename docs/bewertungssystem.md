# Bewertungssystem

Berechnet Ampel-Scores und Gesamteinschätzungen zur IT-Sicherheit und Operational Readiness pro Standort und Kunde.

## Karten

- #294: Standort-Bezeichnung in Bewertung aufgelöst

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/services/evaluator.py` | `EvaluatorService`-Singleton: berechnet `GesamtBewertung` |
| `app/models/bewertung.py` | `KriteriumBewertung`, `KategorieBewertung`, `GesamtBewertung` |
| `bewertung/kategorien.yaml` | 4 Bewertungskategorien |
| `bewertung/skala.yaml` | 5 Bewertungsstufen |
| `app/web/routes_bewertung.py` | Bewertungs-Dashboard-Route |
| `app/templates/bewertung/index.html` | Bewertungs-Dashboard mit KPI-Kacheln |
| `app/templates/_gesamtbewertung_kpi.html` | KPI-Kachel "Gesamtbewertung" |
| `app/services/chart_generator.py` | Generiert Balkendiagramm (Pillow) für Dashboard |

## Funktionsweise

### Kategorien (`kategorien.yaml`)

| ID | Name |
|---|---|
| 1 | IT-Sicherheit |
| 2 | Rechtliche Anforderungen |
| 3 | Hardware & Software |
| 4 | Betriebsrisiken |

### Skala (`skala.yaml`)

| Stufe | Prozent | Bedeutung |
|---|---|---|
| `kritisch` | <=20% | Kritischer Zustand |
| `mangelhaft` | <=40% | Mangelhaft |
| `ausreichend` | <=60% | Ausreichend |
| `gut` | <=80% | Gut |
| `sehr_gut` | <=100% | Sehr gut |

### Berechnung

1. Pro `TechnikObjekt`: Punkte aus schema-Feldern (`regelrelevant` markiert).
2. Pro Kriterium: Aggregation über alle Objekte.
3. Pro Kategorie: Aggregation über Kriterien.
4. Gesamt: Schlechtester Standort bestimmt das Gesamtergebnis (Worst-Case-Prinzip).
5. `schlechtester_standort_bezeichnung` wird anhand `Standort.bezeichnung` aufgelöst (#294).

### Vorläufig-Hinweis (#403)

- KPI-Kachel "Gesamtbewertung" zeigt bei niedrigem Erfassungsstand "Vorläufig: <Stufe>" mit Badge "Erfassungsstand: X %".
- Konsistent auf allen drei Seiten: Bewertung, Auftrag-Übersicht, Auftrag-Detail.
