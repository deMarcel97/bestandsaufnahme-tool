# Netzwerktopologie

Automatische Generierung und interaktive Visualisierung von Netzwerktopologien aus Standort-Anbindungen und Technik-Objekten.

## Karten

- #324: Automatischer Netzplan aus Verbindungsdaten
- #362: Phantom-Backup-ISP entfernt, Standard-Uplink-Labels bereinigt
- #372: Offline-Fähigkeit für Mermaid.js
- #402: Platzhalter-Werte bereinigt, echte Anbindungsdaten auf Kanten, redundante 2. Internetleitung

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/services/topology_generator.py` | `generate_network_topology_mermaid()` -- generiert Mermaid-Flowchart |
| `app/static/js/topology.js` | Interaktiver Web-Viewer: Zoom, Pan, Vollbild |
| `app/static/js/mermaid.min.js` | Lokales Mermaid.js-Bundle (Offline) |
| `app/templates/auftrag/_topologie_preview.html` | Topologie-Vorschau-Karte |
| `app/templates/auftrag/erfassung.html` | Einbettung in Erfassungsseite |
| `app/templates/auftrag/uebersicht.html` | Einbettung in Übersichtsseite |
| `app/templates/auftrag/detail.html` | Einbettung in Detailseite |

## Funktionsweise

### Topologie-Generator

Generiert strukturierte, farbcodierte Mermaid-Flowcharts mit vollständiger Hierarchie:

```
WAN/Internet (Anbindungen & Bandbreiten)
  -> Perimeter (Firewalls, HA-Cluster)
    -> Core-Switching (Trunk, LAG, Stacking)
      -> Access-Switching (Edge, PoE)
        -> Server & Storage (Hypervisoren, SAN/NAS, iSCSI, FC)
          -> Virtuelle Maschinen (VMs mit OS, Specs, Rollen)
        -> WLAN Access Points (Wi-Fi Standards, PoE+, Gast-WLAN)
      -> Endgeräte & Clients
    -> USV
```

### Interaktive Web-UI

- Mermaid.js-Rendering mit Zoom In (+), Zoom Out (-), 1:1 Reset.
- Maus-Pan (Drag & Drop), Mausrad-Zoom.
- Vollbild-Modus.
- `htmx:afterSwap`-Event-Listener für dynamisches Nachladen.

### Offline-Fähigkeit (#372)

- `mermaid.min.js` als lokales Asset unter `/static/js/mermaid.min.js` gebündelt.
- Vollständige Visualisierung ohne externe Internetverbindung (vor Ort beim Kunden).

### Bereinigungen (#362, #402)

- **Phantom-Backup-ISP (#362)**: Backup-Leitungen werden nur gerendert, wenn `redundante_anbindung = "ja"`.
- **Standard-Uplink-Labels (#362)**: Hartcodierte Labels ("Trunk / LAG 10G", "Server Uplink (10G/LAG)") durch generisches "Uplink" ersetzt.
- **Platzhalter-Filter (#402)**: `clean_brand_model` filtert "sonstige"/"unbekannt"/"diverse" aus Labels.
- **Echte Anbindungsdaten (#402)**: WAN-/Firewall-/Switch-Kanten zeigen echte erfasste Anbindungsdaten (Anschlussart, LAG-Typ, Geschwindigkeit).
- **Redundante 2. Internetleitung (#402)**: Wizard erfasst Anbieter, Anschlussart, Bandbreite und Failover einer Backup-Leitung.

### Berichts-Integration

- Integration in Kapitel 4 des Analyseberichts mit eigenem Unterabschnitt "Netzwerktopologie" pro Standort.
- Im DOCX-Export als formatierter Mermaid-Diagrammblock.
