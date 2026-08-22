# Hersteller- und Modelllisten

Pro-Hersteller Modell-Auswahllisten mit Freitext-Fallback für Hardware-Bausteine.

## Karten

- #355: Hersteller-Listen erweitert + Modell-Auswahllisten pro Hersteller

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `schemas/firewall.yaml` | Firewall-Hersteller + Modell-Listen |
| `schemas/switch.yaml` | Switch-Hersteller + Modell-Listen |
| `schemas/server_virtualisierung.yaml` | Server-Hersteller + Modell-Listen |
| `schemas/usv.yaml` | USV-Hersteller + Modell-Listen |
| `schemas/access_point.yaml` | AP-Hersteller + Modell-Listen |
| `schemas/storage.yaml` | Storage-Hersteller |
| `app/templates/technik/form.html` | Template mit `sichtbar_wenn` für Modell-Dropdowns |

## Funktionsweise

### Muster

1. Hersteller-Dropdown mit fester Liste + `sonstige` + Freitext-Fallback.
2. Pro Hersteller ein eigenes Modell-Dropdown, eingeblendet per `sichtbar_wenn`.
3. Freitext-Fallback für "Sonstiges" Modell.

### Abgedeckte Bausteine

| Baustein | Hersteller |
|---|---|
| Firewall | Fortinet, Sophos, Palo Alto, Cisco, WatchGuard, SonicWall, Juniper, Check Point, Barracuda, Zyxel, Stormshield |
| Switch | Cisco, Aruba/HPE, Dell, Ubiquiti, Juniper, Extreme Networks, Zyxel, D-Link, TP-Link, Brocade/Ruckus, Allied Telesis |
| Server | Dell PowerEdge, HPE ProLiant, Lenovo ThinkSystem, Fujitsu PRIMERGY, Cisco UCS, Huawei, ASUS, Gigabyte |
| USV | APC, Eaton, Generex, Socomec, CyberPower, FSP |
| Access Point | Cisco, Aruba/HPE, Ubiquiti, Ruckus, Zyxel, TP-Link, DrayTek, LANCOM, Extreme Networks |
| Storage | NetApp, Dell, Huawei, HPE, Synology, QNAP, TrueNAS, Pure Storage, IBM, Hitachi, Fujitsu, Lenovo, Buffalo |

### Modellreihen

- Echte Modellreihen (2011-2026) für Firewall, Switch, Server, USV und Access Point.
- Template-Fix für numerische Modell-Werte (z. B. Check Point 600/700).

### Baustein-Bezeichnung (#376)

- `format_baustein_bezeichnung` priorisiert das Modell: `Firewall FortiGate 60F`, `Switch Catalyst 9200-24T`, `Server PowerEdge R740`.
