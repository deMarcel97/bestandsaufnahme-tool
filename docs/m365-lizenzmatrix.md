# M365-Lizenzmatrix

Lizenz-bewusste Regelbewertung für Microsoft 365: Trennung von Lizenz-Fehlt- und Fehlkonfigurations-Triggern.

## Karten

- #405: Recherche der Lizenzmatrix (zwei unabhängige Quellen, Vergleich in #407)
- #408: Fundament (Lizenzfeld, erste drei Regeln, Fix Tier-Blindheit)
- #407: Matrix als Datenquelle im Repo, Lookup in der Rule-Engine
- #409–#412: Ausrollen der verbleibenden 38 Features je Feature-Gruppe

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `rules/m365_lizenzmatrix.json` | Die Matrix: 353 Zeilen (41 Features × 15 Lizenzpläne). **Generiert — nicht von Hand bearbeiten.** |
| `tools/build_m365_matrix.py` | Generator und Feature-Katalog. Hier wird gepflegt. |
| `app/services/m365_lizenzmatrix.py` | Lädt die Matrix, beantwortet „deckt diese Lizenzierung Feature X ab?" |
| `schemas/m365_security.yaml` | Mehrfachauswahl-Feld `m365_lizenzen` (15 SKUs) |
| `rules/m365_lizenzmatrix.yaml` | Die handgepflegten Regeln mit ihren Fundtexten |
| `tests/test_m365_lizenzlookup.py` | Tests zum Lookup (#407) |
| `tests/test_m365_lizenzmatrix.py` | Tests zum Fundament (#408) |

## Warum die Matrix als Daten und nicht in den Regeln steht

Bis #408 trug jede Regel ihre Planliste selbst:

```yaml
- feld: m365_lizenzen
  operator: nicht_in_liste
  wert: [bp, me3, me5, entp1, entp2]     # so nicht mehr
```

Bei 41 Features über 15 Pläne wären das über achtzig handgepflegte Listen,
die nach jedem Microsoft-Repackaging (zuletzt 07/2026) einzeln nachgezogen
werden müssten. Seit #407 steht die Abdeckung stattdessen in der Matrix:

```yaml
- feld: m365_lizenzen
  operator: lizenz_deckt_nicht
  wert: conditional_access               # feature_id aus der Matrix
```

Eine unbekannte `feature_id` lässt das Laden der Regeln fehlschlagen. Ohne
diese Prüfung wäre ein Tippfehler unsichtbar — die Regel würde nie zutreffen
und das Finding still verschlucken.

## Der Unterschied, an dem es hängt

Nur das **Microsoft 365**-Bundle bringt EMS mit (Intune, Entra ID P1/P2,
Windows Enterprise), das gleichnamige **Office 365**-Bundle nicht. Neun
Features unterscheiden sich allein dadurch:

`app_protection`, `autopilot`, `compliance_policies`, `conditional_access`,
`config_profiles`, `defender_endpoint`, `intune_full`, `sspr`,
`windows_enterprise`

Wer beide gleich behandelt, meldet einem Office-365-E3-Kunden Conditional
Access als vorhanden — ein Befund, der im Kundengespräch nicht standhält.
Genau daran wäre die im Vergleich (#407) verworfene Alternativmatrix
gescheitert; `test_office365_e3_hat_kein_ems` hält den Fall fest.

## Drei Zustände, nicht zwei

| `enthalten` | Bedeutung | Gilt als lizenziert |
|---|---|---|
| `Ja` | im Grundpreis enthalten | ja |
| `Add-on` | innerhalb des Plans zubuchbar, aber erst nach Kauf vorhanden | **nein** |
| `Nein` | nur über einen Planwechsel erreichbar | nein |

`Add-on` als vorhanden zu werten würde einen Fehlkonfigurations-Befund für
etwas erzeugen, das der Kunde nie gekauft hat.

Ein Tenant trägt oft mehrere SKUs gleichzeitig (Business Basic plus Entra ID
P1 als Standalone). Es genügt, wenn **eine** davon das Feature abdeckt.

## Trigger-Typen

| Typ | Bedeutung | Regelform |
|---|---|---|
| 1 | Unterlizenzierung — Feature fehlt, Kunde braucht es | `lizenz_deckt_nicht` |
| 2 | Shelfware — vorhanden, aber ungenutzt | `lizenz_deckt` + Nutzungsfeld |
| 3 | Fehlkonfiguration — vorhanden, aber unsicher konfiguriert | `lizenz_deckt` + Konfigurationsfeld |

## Evidenzstatus

Die Matrix ist ein Rechercheergebnis, das **noch niemand Zeile für Zeile
gegen learn.microsoft.com gegengeprüft hat**. Jede Zeile trägt deshalb einen
Evidenzstatus, damit die Wissenslücke sichtbar bleibt statt unbemerkt in
einem Kundenbericht zu landen:

| Status | Bedeutung |
|---|---|
| `bestaetigt` | gegen eine Primärquelle geprüft (URL in `quelle`) |
| `wahrscheinlich` | plausibel, aber ohne Primärquelle |
| `umstritten` | Quellen widersprechen sich |
| `unbestaetigt` | noch nicht gegengeprüft (Ausgangszustand) |

Stand heute: **41 von 41 Features ohne Primärquelle**, davon zwei als
`umstritten` markiert (`sharepoint_quota`, `audio_conferencing` — dort
widersprachen sich die beiden Rechercheergebnisse aus #405).
`meta.evidenz_offen` in der JSON-Datei führt den offenen Rest mit.

## Pflege

```bash
python3 tools/build_m365_matrix.py                          # Matrix neu erzeugen
python3 tools/build_m365_matrix.py --offen                  # Features ohne Regel
python3 tools/build_m365_matrix.py --scaffold intune_full   # YAML-Gerüst
```

Bei einem Microsoft-Repackaging wird der Katalog in `tools/build_m365_matrix.py`
angepasst und die Matrix neu erzeugt. Quellen-URLs werden dort im
`EVIDENZ`-Dict je Feature hinterlegt.

`--scaffold` schreibt bewusst nichts nach `rules/`: die Fundtexte
(`befund`, `risiko`, `empfehlung`) gehören handgepflegt und auf Deutsch. Das
Gerüst liefert nur die Regelstruktur, den Schweregrad und den Recherchetext
als Ausgangspunkt.
