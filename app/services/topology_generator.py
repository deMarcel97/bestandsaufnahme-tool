"""
Topologie-Generator: Erzeugt automatische Netzwerkpläne aus erfassten Verbindungsdaten.

Hierarchie:
1. Internet / WAN (Anbindungen aus Standortdaten)
2. Perimeter (Firewall / Gateway)
3. Core-Switching (Trunks, LAG, Stacking, Distribution)
4. Access-Switching (Edge, PoE-Switches, Etagenverteiler)
5. Server-Hosts & Virtualisierung (Hyper-V / ESXi / Proxmox / Cluster) & Storage (SAN / NAS / iSCSI)
6. Virtuelle Maschinen (VMs) unter ihren Hypervisoren
7. WLAN Access Points (PoE, Wi-Fi Standards)
8. Clients & Endgeräte (Workstations, Laptops, Gast-WLAN)
"""

from typing import List, Optional, Dict, Any, Tuple
import re
from app.models.standort import Standort
from app.models.technik import TechnikObjekt


def sanitize_mermaid_id(raw_id: str) -> str:
    """Bereinigt einen Bezeichner für gültige Mermaid-Knoten-IDs."""
    if not raw_id:
        return "node_unknown"
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw_id).strip())
    if clean and clean[0].isdigit():
        clean = f"n_{clean}"
    return clean or "node_item"


def sanitize_mermaid_label(text: str) -> str:
    """Bereinigt Text innerhalb von Mermaid-Knotenbeschriftungen."""
    if not text:
        return ""
    s = str(text).strip()
    s = s.replace('"', "'")
    s = s.replace("[", "(").replace("]", ")")
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("\\", "/")
    s = s.replace("\n", "<br/>")
    s = s.replace("\r", "")
    return s


def sanitize_edge_label(text: str) -> str:
    """Bereinigt Verbindungs-Labels für Mermaid (keine Pipes)."""
    if not text:
        return ""
    s = str(text).strip()
    s = s.replace("|", "/")
    s = s.replace('"', "'")
    s = s.replace("[", "(").replace("]", ")")
    s = s.replace("\n", " ")
    return s


def _is_core_switch(obj: TechnikObjekt) -> bool:
    """Ermittelt anhand von Konfiguration und Bezeichnung, ob ein Switch als Core/Distribution fungiert."""
    daten = obj.daten or {}
    bez = (obj.bezeichnung or "").lower()
    
    # Eindeutige Access-Kennzeichen
    if any(kw in bez for kw in ["access", "etage", "edge", "floor", "unterverteil", "client"]):
        return False

    # Explizite Core-Kennzeichen
    if daten.get("cluster_verbund") == "ja":
        return True
    if daten.get("anbindung_firewall_typ") == "lag":
        return True
    if daten.get("geschwindigkeit") in ("10G", "25G"):
        return True
    
    core_keywords = ["core", "hauptverteiler", "backbone", "distrib", "aggr", "stack", "zentral", "haupt"]
    if any(kw in bez for kw in core_keywords):
        return True
    
    return False


def generate_network_topology_mermaid(standort: Optional[Standort], objekte: List[TechnikObjekt]) -> str:
    """
    Generiert ein strukturiertes Mermaid-Flowchart der Netzwerktopologie für einen Standort.
    
    Abgebildete Ebenen:
    WAN -> Perimeter (Firewall) -> Core-Switching -> Access-Switches -> Server & Storage -> VMs -> WLAN -> Clients
    """
    lines: List[str] = []
    lines.append("flowchart TD")
    lines.append("    %% Styling-Definitionen")
    lines.append("    classDef default fill:#FFFFFF,stroke:#94A3B8,stroke-width:1.5px,color:#0F172A,font-family:sans-serif;")
    lines.append("    classDef wanNode fill:#E0F2FE,stroke:#0284C7,stroke-width:2px,color:#0369A1,font-weight:bold;")
    lines.append("    classDef fwNode fill:#FEE2E2,stroke:#DC2626,stroke-width:2px,color:#991B1B,font-weight:bold;")
    lines.append("    classDef coreNode fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px,color:#5B21B6,font-weight:bold;")
    lines.append("    classDef accessNode fill:#E0E7FF,stroke:#4F46E5,stroke-width:2px,color:#3730A3,font-weight:bold;")
    lines.append("    classDef serverNode fill:#FEF3C7,stroke:#D97706,stroke-width:2px,color:#92400E,font-weight:bold;")
    lines.append("    classDef storageNode fill:#FCE7F3,stroke:#DB2777,stroke-width:2px,color:#9D174D,font-weight:bold;")
    lines.append("    classDef vmNode fill:#FFFBEB,stroke:#F59E0B,stroke-width:1.5px,stroke-dasharray:3 3,color:#78350F;")
    lines.append("    classDef apNode fill:#CCFBF1,stroke:#0D9488,stroke-width:2px,color:#115E59,font-weight:bold;")
    lines.append("    classDef clientNode fill:#F1F5F9,stroke:#64748B,stroke-width:1.5px,color:#334155;")
    lines.append("    classDef usvNode fill:#ECFCCB,stroke:#65A30D,stroke-width:1.5px,color:#3F6212;")

    # Objekte nach Typ filtern
    firewalls = [o for o in objekte if o.typ == "firewall"]
    switches = [o for o in objekte if o.typ == "switch"]
    servers = [o for o in objekte if o.typ in ("server_virtualisierung", "server_cluster")]
    storages = [o for o in objekte if o.typ in ("storage", "backup_storage")]
    vms = [o for o in objekte if o.typ == "vm"]
    aps = [o for o in objekte if o.typ == "access_point"]
    client_objs = [o for o in objekte if o.typ == "clients"]
    usv_objs = [o for o in objekte if o.typ == "usv"]

    anbindungen = standort.anbindungen if (standort and standort.anbindungen) else []

    # Prüfen, ob überhaupt Netzwerk- oder Infrastrukturkomponenten vorliegen
    has_any_data = bool(anbindungen or firewalls or switches or servers or storages or vms or aps or client_objs or (standort and standort.anzahl_user > 0))

    if not has_any_data:
        lines.append('    empty_node["ℹ️ Keine Netzwerkkomponenten erfasst"]')
        return "\n".join(lines)

    # 1. WAN-Ebene
    wan_nodes: List[Tuple[str, bool]] = []  # (node_id, is_backup)
    lines.append('\n    subgraph WAN ["🌐 Internet & WAN-Anbindung"]')
    if anbindungen:
        for idx, anb in enumerate(anbindungen, start=1):
            nid = f"wan_{idx}"
            is_backup = (anb.ist_backup_leitung == "ja")
            anbieter = anb.anbieter or "Internet"
            art = anb.art or "WAN"
            down = f"{anb.bandbreite_down_mbit:.0f}" if anb.bandbreite_down_mbit else "?"
            up = f"{anb.bandbreite_up_mbit:.0f}" if anb.bandbreite_up_mbit else "?"
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(anbieter)}</b> ({sanitize_mermaid_label(art)})"]
            lbl_parts.append(f"{down}/{up} Mbit/s")
            if is_backup:
                lbl_parts.append("<i>[Backup-Leitung]</i>")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::wanNode')
            wan_nodes.append((nid, is_backup))
    else:
        nid = "wan_generic"
        lines.append(f'        {nid}["<b>Internet / WAN</b><br/>Öffentliches Netz"]:::wanNode')
        wan_nodes.append((nid, False))
    lines.append("    end")

    # 2. Perimeter (Firewall)
    fw_nodes: List[str] = []
    if firewalls:
        lines.append('\n    subgraph Perimeter ["🛡️ Perimeter & Security"]')
        for fw in firewalls:
            nid = sanitize_mermaid_id(f"fw_{fw.id}")
            fw_nodes.append(nid)
            hersteller = fw.daten.get("hersteller") or ""
            modell = fw.daten.get("modell") or ""
            aufbau = fw.daten.get("aufbau") or ""
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(fw.bezeichnung or 'Firewall')}</b>"]
            if hersteller or modell:
                lbl_parts.append(sanitize_mermaid_label(f"{hersteller} {modell}".strip()))
            if aufbau and aufbau != "unbekannt":
                aufbau_txt = "HA-Cluster (Aktiv/Passiv)" if aufbau == "Cluster_aktiv_passiv" else "HA-Cluster (Aktiv/Aktiv)" if aufbau == "Cluster_aktiv_aktiv" else aufbau
                lbl_parts.append(f"<i>{sanitize_mermaid_label(aufbau_txt)}</i>")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::fwNode')
        lines.append("    end")

    # 3. Switching (Core vs Access)
    core_switches = [s for s in switches if _is_core_switch(s)]
    access_switches = [s for s in switches if not _is_core_switch(s)]
    
    if not core_switches and switches:
        core_switches = [switches[0]]
        access_switches = switches[1:]

    core_nodes: List[str] = []
    if core_switches:
        lines.append('\n    subgraph CoreSwitching ["🔀 Core- & Distribution-Switching"]')
        for sw in core_switches:
            nid = sanitize_mermaid_id(f"sw_core_{sw.id}")
            core_nodes.append(nid)
            hersteller = sw.daten.get("hersteller") or ""
            modell = sw.daten.get("modell") or ""
            speed = sw.daten.get("geschwindigkeit") or ""
            ports = sw.daten.get("port_anzahl") or ""
            cluster = sw.daten.get("cluster_verbund") == "ja"
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(sw.bezeichnung or 'Core Switch')}</b>"]
            details = f"{hersteller} {modell}".strip()
            if ports:
                details += f" ({ports} Ports)"
            if details:
                lbl_parts.append(sanitize_mermaid_label(details))
            if speed and speed != "unbekannt":
                lbl_parts.append(f"Speed: {sanitize_mermaid_label(speed)}")
            if cluster:
                lbl_parts.append("<i>Stack / Cluster-Verbund</i>")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::coreNode')
        lines.append("    end")

    access_nodes: List[str] = []
    if access_switches:
        lines.append('\n    subgraph AccessSwitching ["🔌 Access-Switching"]')
        for sw in access_switches:
            nid = sanitize_mermaid_id(f"sw_acc_{sw.id}")
            access_nodes.append(nid)
            hersteller = sw.daten.get("hersteller") or ""
            modell = sw.daten.get("modell") or ""
            speed = sw.daten.get("geschwindigkeit") or ""
            ports = sw.daten.get("port_anzahl") or ""
            poe = sw.daten.get("poe_vorhanden") == "ja"
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(sw.bezeichnung or 'Access Switch')}</b>"]
            details = f"{hersteller} {modell}".strip()
            if ports:
                details += f" ({ports} Ports)"
            if details:
                lbl_parts.append(sanitize_mermaid_label(details))
            if poe:
                lbl_parts.append("PoE Support")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::accessNode')
        lines.append("    end")

    # 4. Server & Storage
    server_nodes: Dict[str, str] = {}  # obj.id -> mermaid nid
    storage_nodes: List[str] = []
    if servers or storages:
        lines.append('\n    subgraph ServerStorageInfra ["🖥️ Server, Storage & Virtualisierung"]')
        for srv in servers:
            nid = sanitize_mermaid_id(f"srv_{srv.id}")
            server_nodes[srv.id] = nid
            hersteller = srv.daten.get("hersteller") or ""
            modell = srv.daten.get("modell") or ""
            typ_label = "Server-Cluster" if srv.typ == "server_cluster" else "Host Server"
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(srv.bezeichnung or typ_label)}</b>"]
            if srv.typ == "server_cluster":
                knoten = srv.daten.get("anzahl_knoten")
                if knoten:
                    lbl_parts.append(f"{knoten} Knoten")
                storage_t = srv.daten.get("shared_storage_typ")
                if storage_t and storage_t != "unbekannt":
                    lbl_parts.append(f"Shared Storage: {sanitize_mermaid_label(storage_t.upper())}")
            else:
                is_virt = srv.daten.get("wird_virtualisiert") == "ja"
                hyp = srv.daten.get("hypervisor_typ") or ""
                hyp_ver = srv.daten.get("hypervisor_version") or ""
                hosts_anz = srv.daten.get("anzahl_host_server")
                if hosts_anz and int(hosts_anz) > 1:
                    lbl_parts.append(f"{hosts_anz}x Hosts ({hersteller} {modell})".strip())
                elif hersteller or modell:
                    lbl_parts.append(sanitize_mermaid_label(f"{hersteller} {modell}".strip()))
                if is_virt and hyp and hyp != "unbekannt":
                    hyp_name = hyp.replace("_", " ").title()
                    lbl_parts.append(f"Hypervisor: {sanitize_mermaid_label(hyp_name)} {sanitize_mermaid_label(hyp_ver)}".strip())
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::serverNode')

        for sto in storages:
            nid = sanitize_mermaid_id(f"sto_{sto.id}")
            storage_nodes.append(nid)
            hersteller = sto.daten.get("hersteller_shared") or sto.daten.get("hersteller") or ""
            protokoll = sto.daten.get("protokoll_anbindung") or ""
            netto = sto.daten.get("kapazitaet_netto_tb") or sto.daten.get("speicherkapazitaet_tb")
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(sto.bezeichnung or 'Storage')}</b>"]
            details = [hersteller.replace("_", " ").title()] if hersteller and hersteller != "unbekannt" else []
            if protokoll and protokoll != "unbekannt":
                details.append(protokoll.upper())
            if netto:
                details.append(f"{netto} TB")
            if details:
                lbl_parts.append(sanitize_mermaid_label(" · ".join(details)))
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::storageNode')
        lines.append("    end")

    # 5. Virtuelle Maschinen (VMs)
    vm_nodes: List[Tuple[str, Optional[str]]] = []  # (vm_nid, host_obj_id)
    if vms:
        lines.append('\n    subgraph VMs ["📦 Virtuelle Maschinen"]')
        for vm in vms:
            nid = sanitize_mermaid_id(f"vm_{vm.id}")
            host_ref = vm.daten.get("host_referenz")
            vm_nodes.append((nid, host_ref))
            
            vm_name = vm.daten.get("name") or vm.bezeichnung or "VM"
            os_name = vm.daten.get("betriebssystem") or ""
            funktion = vm.daten.get("funktion_dienst") or ""
            cpu = vm.daten.get("cpu_kerne")
            ram = vm.daten.get("ram_gb")
            ha = vm.daten.get("ha_faehig") == "ja"
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(vm_name)}</b>"]
            specs = []
            if cpu:
                specs.append(f"{cpu} vCPU")
            if ram:
                specs.append(f"{ram} GB RAM")
            if specs:
                lbl_parts.append(", ".join(specs))
            if os_name and os_name != "n/a":
                lbl_parts.append(sanitize_mermaid_label(os_name))
            if funktion and funktion != "n/a":
                lbl_parts.append(f"<i>Role: {sanitize_mermaid_label(funktion)}</i>")
            if ha:
                lbl_parts.append("<b>[HA Aktiv]</b>")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::vmNode')
        lines.append("    end")

    # 6. WLAN Access Points
    ap_nodes: List[Tuple[str, bool]] = []  # (ap_nid, has_gast_wlan)
    if aps:
        lines.append('\n    subgraph WLANInfra ["📶 WLAN-Infrastruktur"]')
        for ap in aps:
            nid = sanitize_mermaid_id(f"ap_{ap.id}")
            has_gast = ap.daten.get("gast_wlan_vorhanden") == "ja"
            ap_nodes.append((nid, has_gast))
            
            hersteller = ap.daten.get("hersteller") or ""
            modell = ap.daten.get("modell") or ""
            standard = ap.daten.get("wlan_standard") or ""
            mgmt = ap.daten.get("management") or ""
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(ap.bezeichnung or 'Access Point')}</b>"]
            details = f"{hersteller} {modell}".strip()
            if standard and standard != "unbekannt":
                std_txt = standard.replace("wifi", "Wi-Fi ").upper()
                details += f" ({std_txt})"
            if details:
                lbl_parts.append(sanitize_mermaid_label(details))
            if mgmt and mgmt != "unbekannt":
                mgmt_txt = "Cloud Mgmt" if mgmt == "cloud_controller" else "Controller" if mgmt == "onprem_controller" else "Standalone"
                lbl_parts.append(f"<i>{sanitize_mermaid_label(mgmt_txt)}</i>")
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::apNode')
        lines.append("    end")

    # 7. Clients & Endgeräte
    client_nodes: List[str] = []
    has_gast_wlan_any = any(has_gast for _, has_gast in ap_nodes)
    if client_objs or (standort and standort.anzahl_user > 0) or has_gast_wlan_any:
        lines.append('\n    subgraph Endpoints ["💻 Clients & Endgeräte"]')
        if client_objs:
            for cli in client_objs:
                nid = sanitize_mermaid_id(f"cli_{cli.id}")
                client_nodes.append(nid)
                win = cli.daten.get("anzahl_windows_clients") or 0
                mac = cli.daten.get("anzahl_mac_clients") or 0
                linux = cli.daten.get("anzahl_linux_clients") or 0
                einsatz = cli.daten.get("einsatzart") or ""
                
                lbl_parts = [f"<b>{sanitize_mermaid_label(cli.bezeichnung or 'Clients')}</b>"]
                dev_counts = []
                if win:
                    dev_counts.append(f"{win}x Win")
                if mac:
                    dev_counts.append(f"{mac}x Mac")
                if linux:
                    dev_counts.append(f"{linux}x Linux")
                if dev_counts:
                    lbl_parts.append(" · ".join(dev_counts))
                if einsatz and einsatz != "unbekannt":
                    einsatz_txt = einsatz.replace("_", " ").title()
                    lbl_parts.append(f"<i>{sanitize_mermaid_label(einsatz_txt)}</i>")
                
                node_label = "<br/>".join(lbl_parts)
                lines.append(f'        {nid}["{node_label}"]:::clientNode')
        elif standort and standort.anzahl_user > 0:
            nid = "cli_standort_users"
            client_nodes.append(nid)
            lines.append(f'        {nid}["<b>Arbeitsplatz-Clients</b><br/>{standort.anzahl_user} Benutzer"]:::clientNode')

        if has_gast_wlan_any:
            lines.append('        gast_clients["<b>Gast- & BYOD-Geräte</b><br/><i>Isoliertes Gast-VLAN</i>"]:::clientNode')
        lines.append("    end")

    # 8. USV & Stromversorgung
    usv_nodes: List[str] = []
    if usv_objs:
        lines.append('\n    subgraph PowerInfra ["⚡ Stromabsicherung & USV"]')
        for u in usv_objs:
            nid = sanitize_mermaid_id(f"usv_{u.id}")
            usv_nodes.append(nid)
            hersteller = u.daten.get("hersteller") or ""
            va = u.daten.get("leistung_va")
            minuten = u.daten.get("autonomiezeit_min")
            
            lbl_parts = [f"<b>{sanitize_mermaid_label(u.bezeichnung or 'USV')}</b>"]
            details = [hersteller] if hersteller and hersteller != "unbekannt" else []
            if va:
                details.append(f"{va} VA")
            if minuten:
                details.append(f"{minuten} min Autonomie")
            if details:
                lbl_parts.append(sanitize_mermaid_label(" · ".join(details)))
            
            node_label = "<br/>".join(lbl_parts)
            lines.append(f'        {nid}["{node_label}"]:::usvNode')
        lines.append("    end")

    # ── VERBINDUNGEN (EDGES) ─────────────────────────────────────────────
    lines.append("\n    %% Verbindungen")

    def get_top_switching_nodes() -> List[str]:
        if core_nodes:
            return core_nodes
        if access_nodes:
            return access_nodes
        return []

    # WAN -> Firewall (oder Switch)
    top_targets = fw_nodes if fw_nodes else get_top_switching_nodes()
    if top_targets:
        primary_target = top_targets[0]
        for wan_nid, is_backup in wan_nodes:
            if is_backup:
                lines.append(f"    {wan_nid} -.->|Backup WAN| {primary_target}")
            else:
                lines.append(f"    {wan_nid} ==>|WAN Uplink| {primary_target}")

    # Firewall -> Core-Switches / Access-Switches
    if fw_nodes:
        sw_targets = get_top_switching_nodes()
        if sw_targets:
            for fw_nid in fw_nodes:
                for sw_nid in sw_targets:
                    lines.append(f"    {fw_nid} ==>|Trunk / LAG 10G| {sw_nid}")
        elif server_nodes:
            for fw_nid in fw_nodes:
                for srv_nid in server_nodes.values():
                    lines.append(f"    {fw_nid} -->|Server LAN| {srv_nid}")
        elif client_nodes:
            for fw_nid in fw_nodes:
                for cli_nid in client_nodes:
                    lines.append(f"    {fw_nid} -->|LAN 1G| {cli_nid}")

    # Core-Switches -> Access-Switches
    if core_nodes and access_nodes:
        for c_nid in core_nodes:
            for a_nid in access_nodes:
                lines.append(f"    {c_nid} ==>|Trunk Uplink| {a_nid}")

    # Switching -> Server
    active_switch_nodes = core_nodes or access_nodes or fw_nodes
    if active_switch_nodes and server_nodes:
        sw_primary = active_switch_nodes[0]
        for srv_nid in server_nodes.values():
            lines.append(f"    {sw_primary} ==>|Server Uplink (10G/LAG)| {srv_nid}")

    # Server -> Storage
    if server_nodes and storage_nodes:
        for srv_nid in server_nodes.values():
            for sto_nid in storage_nodes:
                lines.append(f"    {srv_nid} -.->|SAN / iSCSI / NFS| {sto_nid}")
    elif active_switch_nodes and storage_nodes:
        sw_primary = active_switch_nodes[0]
        for sto_nid in storage_nodes:
            lines.append(f"    {sw_primary} -->|Storage VLAN / iSCSI| {sto_nid}")

    # Server -> VMs
    if vms:
        for vm_nid, host_ref in vm_nodes:
            target_srv_nid = None
            if host_ref and host_ref in server_nodes:
                target_srv_nid = server_nodes[host_ref]
            elif server_nodes:
                target_srv_nid = list(server_nodes.values())[0]
            elif active_switch_nodes:
                target_srv_nid = active_switch_nodes[0]
            
            if target_srv_nid:
                lines.append(f"    {target_srv_nid} -->|Hypervisor Host| {vm_nid}")

    # Switching -> WLAN Access Points
    ap_parent_switches = access_nodes or core_nodes or fw_nodes
    if ap_parent_switches and ap_nodes:
        ap_parent = ap_parent_switches[0]
        for ap_nid, has_gast in ap_nodes:
            lines.append(f"    {ap_parent} -->|PoE+ / 1G| {ap_nid}")
            if has_gast:
                lines.append(f"    {ap_nid} -.->|WLAN Gast-SSID| gast_clients")

    # Switching / AP -> Clients
    cli_parent_switches = access_nodes or core_nodes or fw_nodes
    if cli_parent_switches and client_nodes:
        cli_parent = cli_parent_switches[0]
        for cli_nid in client_nodes:
            lines.append(f"    {cli_parent} -->|LAN 1G| {cli_nid}")

    # USV -> Infrastructure
    if usv_nodes:
        usv_primary = usv_nodes[0]
        usv_target = (core_nodes or list(server_nodes.values()) or access_nodes or fw_nodes)
        if usv_target:
            target_id = usv_target[0]
            lines.append(f"    {usv_primary} -.->|USV-Schutz| {target_id}")

    return "\n".join(lines)


def generate_network_topology_summary_text(standort: Optional[Standort], objekte: List[TechnikObjekt]) -> str:
    """
    Erzeugt eine saubere strukturierte Zusammenfassung der Topologie-Ebenen und Pfade
    für Berichtswesen und Dokumenten-Export (.docx).
    """
    lines: List[str] = []
    sto_name = standort.bezeichnung if standort else "Zentrale / Standort"
    lines.append(f"Topologie-Übersicht für {sto_name}:")
    
    # 1. WAN
    anbindungen = standort.anbindungen if (standort and standort.anbindungen) else []
    if anbindungen:
        lines.append("- **WAN / Internetanbindungen:**")
        for a in anbindungen:
            backup_str = " (Backup)" if a.ist_backup_leitung == "ja" else ""
            lines.append(f"  • {a.anbieter or 'Internet'} via {a.art} ({a.bandbreite_down_mbit:.0f}/{a.bandbreite_up_mbit:.0f} Mbit/s){backup_str}")
    
    # 2. Perimeter
    firewalls = [o for o in objekte if o.typ == "firewall"]
    if firewalls:
        lines.append("- **Perimeter & Firewall:**")
        for fw in firewalls:
            hersteller = fw.daten.get("hersteller", "")
            modell = fw.daten.get("modell", "")
            aufbau = fw.daten.get("aufbau", "")
            aufbau_str = f" [{aufbau.replace('_', ' ')}]" if aufbau and aufbau != "unbekannt" else ""
            lines.append(f"  • {fw.bezeichnung} ({hersteller} {modell}){aufbau_str}")

    # 3. Switching
    switches = [o for o in objekte if o.typ == "switch"]
    if switches:
        lines.append("- **Aktive Netzwerktechnik (Switches):**")
        for sw in switches:
            hersteller = sw.daten.get("hersteller", "")
            modell = sw.daten.get("modell", "")
            role = "Core/Distribution" if _is_core_switch(sw) else "Access"
            ports = sw.daten.get("port_anzahl", "")
            ports_str = f", {ports} Ports" if ports else ""
            poe_str = ", PoE" if sw.daten.get("poe_vorhanden") == "ja" else ""
            lines.append(f"  • {sw.bezeichnung} ({role}: {hersteller} {modell}{ports_str}{poe_str})")

    # 4. Server & Storage
    servers = [o for o in objekte if o.typ in ("server_virtualisierung", "server_cluster")]
    storages = [o for o in objekte if o.typ in ("storage", "backup_storage")]
    if servers or storages:
        lines.append("- **Server, Storage & Virtualisierung:**")
        for srv in servers:
            hyp = srv.daten.get("hypervisor_typ", "")
            hyp_str = f" [Hypervisor: {hyp}]" if hyp and hyp != "unbekannt" else ""
            lines.append(f"  • {srv.bezeichnung}{hyp_str}")
        for sto in storages:
            hersteller = sto.daten.get("hersteller_shared") or sto.daten.get("hersteller") or ""
            protokoll = sto.daten.get("protokoll_anbindung", "")
            proto_str = f" ({protokoll.upper()})" if protokoll and protokoll != "unbekannt" else ""
            lines.append(f"  • Storage: {sto.bezeichnung} - {hersteller}{proto_str}")

    # 5. VMs
    vms = [o for o in objekte if o.typ == "vm"]
    if vms:
        lines.append(f"- **Virtuelle Maschinen ({len(vms)} VMs erfasst):**")
        for vm in vms:
            vm_name = vm.daten.get("name") or vm.bezeichnung
            os_name = vm.daten.get("betriebssystem", "")
            funktion = vm.daten.get("funktion_dienst", "")
            fn_str = f" - {funktion}" if funktion else ""
            lines.append(f"  • {vm_name} ({os_name}){fn_str}")

    # 6. WLAN & Clients
    aps = [o for o in objekte if o.typ == "access_point"]
    client_objs = [o for o in objekte if o.typ == "clients"]
    if aps:
        lines.append(f"- **WLAN-Infrastruktur ({len(aps)} Access Points):**")
        for ap in aps:
            std = ap.daten.get("wlan_standard", "")
            lines.append(f"  • {ap.bezeichnung} ({std})")
    if client_objs:
        lines.append("- **Clients & Endgeräte:**")
        for cli in client_objs:
            win = cli.daten.get("anzahl_windows_clients") or 0
            mac = cli.daten.get("anzahl_mac_clients") or 0
            lines.append(f"  • {cli.bezeichnung}: {win} Windows, {mac} Mac")

    return "\n".join(lines)
