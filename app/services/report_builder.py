from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.models.massnahme import Massnahme
from app.models.finding import Finding
from app.models.bewertung import GesamtBewertung
from app.services.schema_loader import schema_loader
from app.services.evaluator import evaluator_service
from app.services.rule_engine import rule_engine
from app.services.topology_generator import generate_network_topology_mermaid

# Storage module attribute for backward compatibility with external test runners
storage = None

class ReportBuilder:
    def build_analysebericht(
        self,
        auftrag: Auftrag,
        standorte: List[Standort],
        objekte: List[TechnikObjekt],
        massnahmen: List[Massnahme],
        bewertung: GesamtBewertung,
        findings: Optional[List[Finding]] = None,
        *,
        # Ohne Vorgabewert und nur benannt übergebbar: ein stiller Default hat
        # hier „kundentauglich" angenommen und damit die schützende Stufe
        # verfehlt, sobald ein Aufrufer die Angabe schlicht vergisst (Karte #310).
        ziel_vertraulichkeit: str  # intern, kundentauglich, anonymisiert
    ) -> str:
        """
        Builds the complete Markdown Analysebericht without emojis.
        Processes pre-filtered objects, locations, and findings directly.
        """
        if findings is None:
            findings = []

        lines = []

        # 1. Header
        kunde_display = "[ANONYMISIERT]" if ziel_vertraulichkeit == "anonymisiert" else auftrag.kunde
        lines.append(f"# Analysebericht: IT-Bestandsaufnahme")
        lines.append(f"**Kunde:** {kunde_display or 'Kein Kunde angegeben'}")
        lines.append(f"**Projektnummer:** {auftrag.projekt_nummer}")
        lines.append(f"**Bezeichnung:** {auftrag.bezeichnung}")
        lines.append(f"**Datum:** {datetime.now().strftime('%d.%m.%Y')}")
        lines.append(f"**Vertraulichkeitsstufe:** {ziel_vertraulichkeit.upper()}")
        lines.append("")

        # 2. Vertraulichkeitshinweis
        lines.append("## Vertraulichkeitshinweis")
        lines.append("Dieses Dokument enthält vertrauliche Informationen zur IT-Infrastruktur des Kunden. "
                     "Eine Weitergabe an unbefugte Dritte ist ohne vorherige schriftliche Zustimmung nicht gestattet.")
        lines.append("")

        # 3. Einleitung: Unternehmenskontext
        ctx = auftrag.unternehmenskontext
        lines.append("## 1. Unternehmenskontext")
        if ziel_vertraulichkeit != "anonymisiert":
            if ctx.kerngeschaeft:
                lines.append(f"**Kerngeschäft:** {ctx.kerngeschaeft}")
            
            mitarbeiter_info = []
            if ctx.anzahl_mitarbeiter_gesamt:
                mitarbeiter_info.append(f"**Mitarbeiter Gesamt:** {ctx.anzahl_mitarbeiter_gesamt}")
            if ctx.anzahl_it_nutzer:
                mitarbeiter_info.append(f"**IT-Nutzer:** {ctx.anzahl_it_nutzer}")
            if mitarbeiter_info:
                lines.append(" | ".join(mitarbeiter_info))
            
            if ctx.geschaeftszeiten_tage:
                if ctx.geschaeftszeiten_tage == "24/7":
                    lines.append("**Geschäftszeiten:** 24/7 Betrieb")
                elif ctx.geschaeftszeiten_von and ctx.geschaeftszeiten_bis:
                    lines.append(f"**Geschäftszeiten:** {ctx.geschaeftszeiten_tage}, {ctx.geschaeftszeiten_von} - {ctx.geschaeftszeiten_bis} Uhr")
                else:
                    lines.append(f"**Geschäftszeiten:** {ctx.geschaeftszeiten_tage}")
        else:
            if ctx.anzahl_it_nutzer:
                lines.append(f"**IT-Nutzer:** {ctx.anzahl_it_nutzer}")
        
        if ctx.geschaeftskritische_systeme:
            lines.append("\n### Geschäftskritische Systeme")
            for sys in ctx.geschaeftskritische_systeme:
                lines.append(f"- **{sys.titel}:** {sys.text}")

        if ctx.geplante_aenderungen:
            status_labels = {
                "in_planung": "In Planung",
                "budgetierung": "Budgetierung",
                "in_durchfuehrung": "In Durchführung / Projektstart bestätigt",
                "abgeschlossen": "Abgeschlossen",
            }
            lines.append("\n### Geplante Änderungen")
            for aend in ctx.geplante_aenderungen:
                status_raw = getattr(aend, "status", "")
                status_suffix = f" (Status: {status_labels.get(status_raw, status_raw)})" if status_raw else ""
                lines.append(f"- **{aend.titel}**{status_suffix}: {aend.text}")
        lines.append("")

        # 4. Ansprechpartner & Support-Matrix (Chapter 2)
        lines.append("## 2. Ansprechpartner & Support-Matrix")
        if auftrag.beteiligte:
            lines.append("| System/Bereich | Ansprechpartner & Rolle | Service- & Notfallkontakt | Service-Zeiten & SLA |")
            lines.append("| --- | --- | --- | --- |")
            for b in auftrag.beteiligte:
                matching_obj = next((o for o in objekte if o.id == b.objekt_id), None) if b.objekt_id else None
                if matching_obj:
                    schema = schema_loader.get_schema(matching_obj.typ)
                    typ_label = schema.get("bezeichnung_anzeige", matching_obj.typ.capitalize()) if schema else matching_obj.typ.capitalize()
                    sys_name = f"{matching_obj.bezeichnung} ({typ_label})"
                    if b.zustaendig_fuer_thema:
                        system_bereich = f"{sys_name} - {b.zustaendig_fuer_thema}"
                    else:
                        system_bereich = sys_name
                else:
                    system_bereich = b.zustaendig_fuer_thema if b.zustaendig_fuer_thema else "Allgemein / Gesamt-IT"

                if ziel_vertraulichkeit == "anonymisiert":
                    ansprechpartner = "[ANONYMISIERT]"
                    if b.rolle:
                        ansprechpartner += f" ({b.rolle})"
                else:
                    ansp_parts = []
                    if b.name:
                        ansp_parts.append(b.name)
                    rolle_info = []
                    if b.rolle and b.rolle != "Sonstiges":
                        rolle_info.append(b.rolle)
                    if b.organisation:
                        rolle_info.append(b.organisation)
                    if rolle_info:
                        ansp_parts.append(f"({', '.join(rolle_info)})")
                    ansprechpartner = " ".join(ansp_parts) if ansp_parts else "-"

                if ziel_vertraulichkeit == "anonymisiert":
                    kontakt = "[ANONYMISIERT]"
                else:
                    kontakte = []
                    if b.telefon:
                        kontakte.append(f"Tel: {b.telefon}")
                    if b.notfall_telefon:
                        kontakte.append(f"Notfall: {b.notfall_telefon}")
                    if b.email:
                        kontakte.append(f"Mail: {b.email}")
                    kontakt = " / ".join(kontakte) if kontakte else "-"

                sla_parts = []
                if b.erreichbarkeit:
                    sla_parts.append(f"Zeiten: {b.erreichbarkeit}")
                if b.sla_reaktionszeit:
                    sla_parts.append(f"SLA: {b.sla_reaktionszeit}")
                service_sla = " / ".join(sla_parts) if sla_parts else "-"

                clean_sb = system_bereich.replace("|", "/").replace("\n", " ").strip()
                clean_ap = ansprechpartner.replace("|", "/").replace("\n", " ").strip()
                clean_kt = kontakt.replace("|", "/").replace("\n", " ").strip()
                clean_sla = service_sla.replace("|", "/").replace("\n", " ").strip()

                lines.append(f"| {clean_sb} | {clean_ap} | {clean_kt} | {clean_sla} |")
            lines.append("")
        else:
            lines.append("Es wurden keine Ansprechpartner oder Support-Kontakte erfasst.\n")

        # 5. Executive Summary & Bewertung (Chapter 3)
        lines.append("## 3. Executive Summary & Bewertung der IT-Umgebung")
        lines.append(f"**Gesamteinstufung:** {bewertung.gesamt_stufe_bezeichnung} ({bewertung.gesamt_prozent:.1f} %)")
        lines.append(f"**Feldabdeckung:** {bewertung.feldabdeckung_prozent:.1f} % | **Bausteinabdeckung:** {bewertung.bausteinabdeckung_prozent:.1f} %")
        lines.append("")
        lines.append("[[GRAFIK:executive_summary]]")
        lines.append("")

        if bewertung.unter_50_prozent_warnung:
            warn_txt = f"\n> **HINWEIS:** Die Bausteine wurden nicht vollständig erfasst. "
            if bewertung.nicht_erfasste_bausteine:
                warn_txt += f"Folgende Bausteine fehlen: {', '.join(bewertung.nicht_erfasste_bausteine)}. "
            warn_txt += "Die Bewertung bezieht sich ausschließlich auf die erfassten Bereiche."
            lines.append(warn_txt)

        lines.append("\n### Bewertung nach Kategorien")
        lines.append("| Kategorie | Punkte Erreicht / Max | Erreichte Prozent | Einstufung |")
        lines.append("| --- | --- | --- | --- |")
        for kat in bewertung.kategorien:
            lines.append(f"| {kat.bezeichnung} | {kat.erreichte_punkte:.1f} / {kat.max_punkte:.1f} | {kat.prozent:.1f} % | {kat.stufe_bezeichnung} |")
        lines.append("")

        # 6. Fachkapitel nach Objekttyp-berichtskapitel (Chapter 4)
        lines.append("## 4. Technische Infrastruktur und Fachkapitel")
        for sto in standorte:
            sto_title = f"### Standort: {sto.bezeichnung} ({sto.ort})" if sto.ort else f"### Standort: {sto.bezeichnung}"
            lines.append(sto_title)
            if sto.anbindungen:
                anb_texts = [f"{a.anbieter} ({a.art}, {a.bandbreite_down_mbit:.0f}/{a.bandbreite_up_mbit:.0f} Mbit/s)" for a in sto.anbindungen]
                lines.append(f"**Internetanbindungen ({len(sto.anbindungen)}):** {', '.join(anb_texts)}")

            sto_objekte = [o for o in objekte if o.standort_id == sto.id]

            # Netzwerktopologie-Abschnitt mit Mermaid-Diagramm
            topo_mermaid = generate_network_topology_mermaid(sto, sto_objekte)
            lines.append("\n#### Netzwerktopologie")
            lines.append("```mermaid")
            lines.append(topo_mermaid)
            lines.append("```\n")

            if not sto_objekte:
                lines.append("Für diesen Standort wurden noch keine Technik-Objekte erfasst.\n")
                continue

            # Separate VMs from other objects for grouped rendering
            vm_objekte = [o for o in sto_objekte if o.typ == "vm"]
            sto_objekte_ohne_vms = [o for o in sto_objekte if o.typ != "vm"]
            
            # Build lookup map: host_id -> list of VMs
            vms_by_host_id = {}
            for vm in vm_objekte:
                host_ref = vm.daten.get("host_referenz")
                if host_ref:
                    if host_ref not in vms_by_host_id:
                        vms_by_host_id[host_ref] = []
                    vms_by_host_id[host_ref].append(vm)

            for obj in sto_objekte_ohne_vms:
                schema = schema_loader.get_schema(obj.typ)
                if not schema:
                    continue

                kapitel_titel = schema.get("bezeichnung_anzeige", obj.typ.capitalize())
                lines.append(f"#### {obj.bezeichnung} ({kapitel_titel})")
                
                # Render VMs grouped under their host
                if obj.id in vms_by_host_id:
                    for vm in vms_by_host_id[obj.id]:
                        vm_name = vm.daten.get("name", "Unbenannte VM")
                        vm_os = vm.daten.get("betriebssystem", "n/a")
                        vm_cpu = vm.daten.get("cpu_kerne", "n/a")
                        vm_ram = vm.daten.get("ram_gb", "n/a")
                        vm_funktion = vm.daten.get("funktion_dienst", "n/a")
                        vm_ha = vm.daten.get("ha_faehig", "n/a")
                        ha_str = "JA" if vm_ha == "ja" else "NEIN" if vm_ha == "nein" else vm_ha
                        lines.append(f"##### VM: {vm_name}")
                        lines.append(f"- **Betriebssystem:** {vm_os}")
                        lines.append(f"- **CPU-Kerne:** {vm_cpu}")
                        lines.append(f"- **RAM (GB):** {vm_ram}")
                        lines.append(f"- **Funktion/Dienst:** {vm_funktion}")
                        lines.append(f"- **HA-fähig:** {ha_str}")
                        lines.append("")

                snippets = []
                for abschnitt in schema.get("abschnitte", []):
                    for feldef in abschnitt.get("felder", []):
                        fname = feldef.get("name")
                        val = obj.daten.get(fname)
                        fest, ausw = self._extract_snippet_pair(val, feldef)
                        if fest:
                            snippets.append(fest)
                        if ausw:
                            snippets.append(ausw)

                if snippets:
                    for snip in snippets:
                        lines.append(snip)
                        lines.append("")
                else:
                    lines.append("Keine detaillierten Angaben zu diesem Objekt vorhanden.")
                    lines.append("")
            
            # Render orphaned VMs (host reference not found in this location's objects)
            all_host_ids = {o.id for o in sto_objekte_ohne_vms}
            for vm in vm_objekte:
                host_ref = vm.daten.get("host_referenz")
                if host_ref and host_ref not in all_host_ids:
                    vm_name = vm.daten.get("name", "Unbenannte VM")
                    vm_os = vm.daten.get("betriebssystem", "n/a")
                    vm_cpu = vm.daten.get("cpu_kerne", "n/a")
                    vm_ram = vm.daten.get("ram_gb", "n/a")
                    vm_funktion = vm.daten.get("funktion_dienst", "n/a")
                    vm_ha = vm.daten.get("ha_faehig", "n/a")
                    ha_str = "JA" if vm_ha == "ja" else "NEIN" if vm_ha == "nein" else vm_ha
                    lines.append(f"#### VM: {vm_name} (Host nicht gefunden)")
                    lines.append(f"- **Betriebssystem:** {vm_os}")
                    lines.append(f"- **CPU-Kerne:** {vm_cpu}")
                    lines.append(f"- **RAM (GB):** {vm_ram}")
                    lines.append(f"- **Funktion/Dienst:** {vm_funktion}")
                    lines.append(f"- **HA-fähig:** {ha_str}")
                    lines.append("")

        cloud_objekte = [o for o in objekte if not o.standort_id]
        if cloud_objekte:
            lines.append("### Standortübergreifende Infrastruktur & Cloud-Dienste")
            vm_objekte = [o for o in cloud_objekte if o.typ == "vm"]
            cloud_objekte_ohne_vms = [o for o in cloud_objekte if o.typ != "vm"]

            vms_by_host_id = {}
            for vm in vm_objekte:
                host_ref = vm.daten.get("host_referenz")
                if host_ref:
                    if host_ref not in vms_by_host_id:
                        vms_by_host_id[host_ref] = []
                    vms_by_host_id[host_ref].append(vm)

            for obj in cloud_objekte_ohne_vms:
                schema = schema_loader.get_schema(obj.typ)
                if not schema:
                    continue

                kapitel_titel = schema.get("bezeichnung_anzeige", obj.typ.capitalize())
                lines.append(f"#### {obj.bezeichnung} ({kapitel_titel})")

                if obj.id in vms_by_host_id:
                    for vm in vms_by_host_id[obj.id]:
                        vm_name = vm.daten.get("name", "Unbenannte VM")
                        vm_os = vm.daten.get("betriebssystem", "n/a")
                        vm_cpu = vm.daten.get("cpu_kerne", "n/a")
                        vm_ram = vm.daten.get("ram_gb", "n/a")
                        vm_funktion = vm.daten.get("funktion_dienst", "n/a")
                        vm_ha = vm.daten.get("ha_faehig", "n/a")
                        ha_str = "JA" if vm_ha == "ja" else "NEIN" if vm_ha == "nein" else vm_ha
                        lines.append(f"##### VM: {vm_name}")
                        lines.append(f"- **Betriebssystem:** {vm_os}")
                        lines.append(f"- **CPU-Kerne:** {vm_cpu}")
                        lines.append(f"- **RAM (GB):** {vm_ram}")
                        lines.append(f"- **Funktion/Dienst:** {vm_funktion}")
                        lines.append(f"- **HA-fähig:** {ha_str}")
                        lines.append("")

                snippets = []
                for abschnitt in schema.get("abschnitte", []):
                    for feldef in abschnitt.get("felder", []):
                        fname = feldef.get("name")
                        val = obj.daten.get(fname)
                        fest, ausw = self._extract_snippet_pair(val, feldef)
                        if fest:
                            snippets.append(fest)
                        if ausw:
                            snippets.append(ausw)

                if snippets:
                    for snip in snippets:
                        lines.append(snip)
                        lines.append("")
                else:
                    lines.append("Keine detaillierten Angaben zu diesem Objekt vorhanden.")
                    lines.append("")

        # 7. Übersichtstabellen Erfasster Systeme (Chapter 5)
        lines.append("## 5. Übersichtstabellen Erfasster Systeme")
        if objekte:
            lines.append("| Bezeichnung | Objekttyp | Standort | Betreut durch | Status |")
            lines.append("| --- | --- | --- | --- | --- |")
            for o in objekte:
                schema = schema_loader.get_schema(o.typ)
                typ_name = schema.get("bezeichnung_anzeige", o.typ) if schema else o.typ
                if o.standort_id:
                    sto_name = next((s.bezeichnung for s in standorte if s.id == o.standort_id), "Unbekannt")
                else:
                    sto_name = "Standortübergreifend"
                calc_status = evaluator_service.calculate_objekt_status(o)
                lines.append(f"| {o.bezeichnung} | {typ_name} | {sto_name} | {o.betreut_durch} | {calc_status} |")
            lines.append("")
        else:
            lines.append("Keine Objekte erfasst.\n")

        # 8. Chapter 6: Feststellungen (Findings)
        lines.append("## 6. Feststellungen (Findings)")
        active_findings = [f for f in findings if f.status != "uebernommen"]
        if active_findings:
            lines.append("| Objekt / Standort | Feld | Erfasster Wert | Schweregrad | Feststellung | Auswirkung | Maßnahme |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for f in active_findings:
                obj_name = "Standort"
                matching_obj = None
                if getattr(f, "objekt_id", None):
                    matching_obj = next((o for o in objekte if o.id == f.objekt_id), None)
                    if matching_obj:
                        obj_name = matching_obj.bezeichnung
                elif getattr(f, "standort_id", None):
                    matching_sto = next((s for s in standorte if s.id == f.standort_id), None)
                    if matching_sto:
                        obj_name = f"Standort: {matching_sto.bezeichnung}"

                field_name = "n/a"
                erfasster_wert = "n/a"
                rule_id = getattr(f, "quelle", None)
                if rule_id and rule_id != "manuell":
                    rule = next((r for r in rule_engine.rules if r.get("id") == rule_id), None)
                    if rule and "bedingung" in rule:
                        cond = rule["bedingung"]
                        cond_items = cond.get("alle", cond.get("eines", []))
                        if cond_items:
                            field_name = cond_items[0].get("feld", "n/a")
                            if matching_obj and hasattr(matching_obj, "daten"):
                                erfasster_wert = str(matching_obj.daten.get(field_name, "n/a"))

                befund_clean = (f.befund or "").replace("\n", " ").replace("|", "/").strip()
                risiko_clean = (f.risiko or "").replace("\n", " ").replace("|", "/").strip()
                m_ref = f.massnahme_id or "Maßnahme ausstehend"
                lines.append(f"| {obj_name} | {field_name} | {erfasster_wert} | {f.schweregrad.upper()} | {befund_clean} | {risiko_clean} | {m_ref} |")
            lines.append("")
        else:
            lines.append("Es wurden keine aktiven Risiken oder Befunde identifiziert.\n")

        # 9. Chapter 7: Priorisierter Maßnahmenkatalog
        lines.append("## 7. Priorisierter Maßnahmenkatalog")
        tot_inv = 0.0
        tot_mon = 0.0
        tot_zeit = 0.0
        tot_count = 0
        tot_uncalc = 0

        for stufe in [1, 2, 3]:
            st_massnahmen = [m for m in massnahmen if m.stufe == stufe]
            lines.append(f"### Umsetzungsstufe {stufe}")
            if not st_massnahmen:
                lines.append("Keine Maßnahmen für diese Stufe zugeordnet.\n")
                continue

            inv_sum = sum(m.investitionskosten for m in st_massnahmen if m.investitionskosten > 0)
            mon_sum = sum(m.monatliche_kosten for m in st_massnahmen if m.monatliche_kosten > 0)
            zeit_sum = sum(m.zeitaufwand for m in st_massnahmen if m.zeitaufwand > 0)
            uncalc_cnt = len([m for m in st_massnahmen if getattr(m, "kosten_quelle", "offen") == "offen" or (m.investitionskosten == 0 and m.zeitaufwand == 0)])

            tot_inv += inv_sum
            tot_mon += mon_sum
            tot_zeit += zeit_sum
            tot_count += len(st_massnahmen)
            tot_uncalc += uncalc_cnt

            lines.append("| Maßnahme | Priorität | Dringlichkeit | Förderprogramm | Investition (€) | Monatlich (€) | Aufwand (Aufwandseinheiten) | Status |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for m in st_massnahmen:
                inv_str = f"{m.investitionskosten:.2f} €" if m.investitionskosten > 0 else "noch zu kalkulieren"
                mon_str = f"{m.monatliche_kosten:.2f} €" if m.monatliche_kosten > 0 else "noch zu kalkulieren"
                zeit_str = f"{m.zeitaufwand:g}" if m.zeitaufwand > 0 else "noch zu kalkulieren"
                foerder = getattr(m, "foerderprogramm", "") or "–"
                lines.append(f"| {m.bezeichnung} | {m.prioritaet} | {getattr(m, 'dringlichkeit', 'mittel')} | {foerder} | {inv_str} | {mon_str} | {zeit_str} | {m.status} |")

            inv_sum_str = f"{inv_sum:.2f} €" if inv_sum > 0 else "noch zu kalkulieren"
            mon_sum_str = f"{mon_sum:.2f} €" if mon_sum > 0 else "noch zu kalkulieren"
            zeit_sum_str = f"{zeit_sum:g}" if zeit_sum > 0 else "noch zu kalkulieren"
            uncalc_note = f" ({uncalc_cnt} von {len(st_massnahmen)} Maßnahmen noch nicht kalkuliert)" if uncalc_cnt > 0 else ""
            lines.append(f"| **Zwischensumme Stufe {stufe}** | | | | **{inv_sum_str}** | **{mon_sum_str}** | **{zeit_sum_str}**{uncalc_note} | |")
            lines.append("")

        if massnahmen:
            tot_inv_str = f"{tot_inv:.2f} €" if tot_inv > 0 else "noch zu kalkulieren"
            tot_mon_str = f"{tot_mon:.2f} €" if tot_mon > 0 else "noch zu kalkulieren"
            tot_zeit_str = f"{tot_zeit:g}" if tot_zeit > 0 else "noch zu kalkulieren"
            tot_note = f" ({tot_uncalc} von {tot_count} Maßnahmen noch nicht kalkuliert)" if tot_uncalc > 0 else ""
            lines.append(f"### Gesamtsumme Maßnahmenkatalog")
            lines.append(f"| **Gesamtsumme Aller Stufen** | | | | **{tot_inv_str}** | **{tot_mon_str}** | **{tot_zeit_str}**{tot_note} | |")
            lines.append("")

        # 10. Anhang: Verträge
        if auftrag.vertraege and ziel_vertraulichkeit != "anonymisiert":
            lines.append("## Anhang: Vertragsübersicht")
            lines.append("| Vertrag | Partner | Gegenstand | Laufzeit bis | Monatl. Kosten (€) |")
            lines.append("| --- | --- | --- | --- | --- |")
            for v in auftrag.vertraege:
                lines.append(f"| {v.bezeichnung} | {v.vertragspartner} | {v.gegenstand} | {v.laufzeit_bis or 'k.A.'} | {v.monatliche_kosten:.2f} |")
            lines.append("")

        # 11. Anhang: Beobachtungen vor Ort. Bewusst getrennt von Kapitel 6
        # (Feststellungen): dort stehen die automatisch aus den Erfassungsregeln
        # erzeugten Findings, hier der manuell notierte persönliche Eindruck vor
        # Ort — sonst blieben `positive_aspekte`/`negative_aspekte` folgenlos
        # (Karte #316). Wie die Verträge unterdrückt für die anonymisierte
        # Fassung, da Freitext leicht auf den Kunden schliessen lässt.
        if (auftrag.positive_aspekte or auftrag.negative_aspekte) and ziel_vertraulichkeit != "anonymisiert":
            lines.append("## Anhang: Beobachtungen vor Ort")
            lines.append(
                "Persönlicher Eindruck vor Ort, unabhängig von den automatisch "
                "erzeugten Feststellungen in Kapitel 6."
            )
            lines.append("")

            if auftrag.positive_aspekte:
                lines.append("### Positive Beobachtungen")
                for a in auftrag.positive_aspekte:
                    lines.append(f"- **{a.titel}:** {a.text}")
                lines.append("")

            if auftrag.negative_aspekte:
                lines.append("### Negative Beobachtungen")
                for a in auftrag.negative_aspekte:
                    lines.append(f"- **{a.titel}:** {a.text}")
                lines.append("")

        return "\n".join(lines)

    def _extract_snippet_pair(self, val: Any, feldef: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        if val is None or val == "" or val == "unbekannt" or val == "rueckfrage":
            return (None, None)

        ftype = feldef.get("typ")
        if ftype in ("auswahl", "ja_nein", "ja_nein_unbekannt", "ja_nein_nicht_relevant") and "werte" in feldef:
            for w in feldef["werte"]:
                if str(w.get("wert")).lower() == str(val).lower():
                    tb = w.get("textbaustein")
                    if isinstance(tb, dict):
                        return (tb.get("feststellung"), tb.get("auswirkung"))
                    elif isinstance(tb, str):
                        return (tb, None)
        elif ftype == "mehrfachauswahl" and "werte" in feldef:
            val_list = val if isinstance(val, (list, tuple)) else [val]
            feststellungen = []
            for item in val_list:
                for w in feldef["werte"]:
                    if str(w.get("wert")).lower() == str(item).lower():
                        tb = w.get("textbaustein")
                        if isinstance(tb, dict) and tb.get("feststellung"):
                            feststellungen.append(tb.get("feststellung"))
                        elif isinstance(tb, str) and tb:
                            feststellungen.append(tb)
            if feststellungen:
                return ("\n".join(feststellungen), None)
        return (None, None)

    def _extract_snippet(self, val: Any, feldef: Dict[str, Any]) -> Optional[str]:
        f_text, a_text = self._extract_snippet_pair(val, feldef)
        if f_text and a_text:
            return f"{f_text}\n\n{a_text}"
        return f_text or a_text

report_builder = ReportBuilder()
