# Offene Punkte

Hierarchische Gliederung offener Punkte nach Standort und Thema, mit Priorisierung und Akkordeon-Toggles.

## Karten

- #287: Offene Punkte nach Baustein gruppieren
- #314: Offene Punkte nach Standort und Thema gliedern (mit Toggles)
- #369: 3-stufige Priorisierung mit Dashboard-Kennzahlen

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_offene_punkte.py` | Aggregiert offene Punkte aus allen Objekten + Standorten |
| `app/services/progress.py` | `collect_offene_punkte()` sammelt Punkte aus TechnikObjekten |
| `app/templates/offene_punkte/index.html` | Akkordeon-Ansicht mit Toggles und Filter-Tabs |

## Funktionsweise

### Hierarchie (#314, #287)

```
Standort 1
  ├── Firewall
  │   ├── Punkt 1
  │   └── Punkt 2
  ├── Switch
  │   └── Punkt 3
  └── ...
Standort 2
  └── ...
Standortübergreifend
  ├── M365 Security
  │   └── Punkt 4
  └── Organisation & Prozesse
      └── Punkt 5
```

### Akkordeon-Toggles (#314)

- Semantische `<details>`/`<summary>`-Toggles für Standorte und Themenbereiche.
- Zähler-Badges pro Ebene.
- "Alle aufklappen" / "Alle zuklappen" Buttons.

### 3-stufige Priorisierung (#369)

| Stufe | Bedeutung |
|---|---|
| Kritisch | Handlungsdruck besteht |
| Wichtig | Sollte angegangen werden |
| Hinweise | Empfehlung |

- Dashboard-Kennzahlen pro Stufe.
- Interaktive Filter-Tabs.

### Sichtbarkeitsfilter (#369)

- `sichtbar_wenn` in `collect_offene_punkte` integriert.
- Irrelevante Warnungen bei inaktiven Sub-Feldern werden unterdrückt.
