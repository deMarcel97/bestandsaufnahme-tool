#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generator für die M365-Lizenzmatrix (Karten #405, #407).

Erzeugt `rules/m365_lizenzmatrix.json` aus dem kompakten Feature-Katalog
unten. Bei einem Microsoft-Repackaging (zuletzt 07/2026) wird der Katalog
hier angepasst und neu erzeugt — die JSON-Datei wird nie von Hand bearbeitet.

    python3 tools/build_m365_matrix.py

`--scaffold <feature_id>` gibt zusätzlich ein YAML-Regelgerüst aus, als
Startpunkt für die Feature-Gruppen-Karten #409 bis #412. Es schreibt
bewusst nichts nach `rules/`: die Fundtexte gehören handgepflegt.

Die Texte in FEATURES sind das unveränderte Rechercheergebnis aus #405 und
bewusst ASCII-only. Sie sind Arbeitsgrundlage für den Regelautor, nicht
Kundentext — was im Bericht landet, steht handgepflegt in `rules/*.yaml`.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PLANS = {
    "BB":    {"name": "Microsoft 365 Business Basic",           "familie": "Business",    "seats": "bis 300"},
    "BS":    {"name": "Microsoft 365 Business Standard",        "familie": "Business",    "seats": "bis 300"},
    "BP":    {"name": "Microsoft 365 Business Premium",         "familie": "Business",    "seats": "bis 300"},
    "ME1":   {"name": "Microsoft 365 E1",                        "familie": "Enterprise",  "seats": "keine Obergrenze"},
    "OE3":   {"name": "Office 365 E3",                           "familie": "Enterprise",  "seats": "keine Obergrenze"},
    "ME3":   {"name": "Microsoft 365 E3",                        "familie": "Enterprise",  "seats": "keine Obergrenze"},
    "OE5":   {"name": "Office 365 E5",                           "familie": "Enterprise",  "seats": "keine Obergrenze"},
    "ME5":   {"name": "Microsoft 365 E5",                        "familie": "Enterprise",  "seats": "keine Obergrenze"},
    "EXOP1": {"name": "Exchange Online Plan 1",                  "familie": "Standalone",  "seats": "-"},
    "EXOP2": {"name": "Exchange Online Plan 2",                  "familie": "Standalone",  "seats": "-"},
    "ENTP1": {"name": "Microsoft Entra ID P1 (Standalone)",      "familie": "Standalone",  "seats": "-"},
    "ENTP2": {"name": "Microsoft Entra ID P2 (Standalone)",      "familie": "Standalone",  "seats": "-"},
    "DFB":   {"name": "Microsoft Defender for Business",         "familie": "Standalone",  "seats": "bis 300"},
    "DFEP1": {"name": "Microsoft Defender for Endpoint Plan 1",  "familie": "Standalone",  "seats": "-"},
    "DFEP2": {"name": "Microsoft Defender for Endpoint Plan 2",  "familie": "Standalone",  "seats": "-"},
}

SUITE = ["BB", "BS", "BP", "ME1", "OE3", "ME3", "OE5", "ME5"]

# status codes: J = Ja, N = Nein, A = Add-on
def s(**kwargs):
    """Baut ein vollstaendiges Status-Dict fuer die 8 Suite-Plaene."""
    d = {p: "N" for p in SUITE}
    d.update(kwargs)
    return d

FEATURES = [
    # ---------------- Identity & Endgeraeteverwaltung ----------------
    dict(id="conditional_access", gruppe="Identity & Endgeraeteverwaltung",
         feature="Conditional Access",
         severity="High", trigger_typ_included=3,
         trigger_missing="Kunde benoetigt bedingten Zugriff (z. B. MFA nur bei Risiko-Login, Geo-Blocking, Geraete-Compliance als Voraussetzung), Plan enthaelt aber nur Entra ID Free -> Lizenz-Upgrade auf einen Plan mit Entra ID P1 (Business Premium, Microsoft 365 E3, Entra ID P1 Standalone) erforderlich.",
         trigger_included="Entra ID P1/P2 lizenziert, aber keine Conditional-Access-Richtlinien aktiv/konfiguriert (nur Security Defaults aktiv) -> Sicherheitsrisiko Konfiguration.",
         status=s(BP="J", ME3="J", OE5="N", ME5="J"),
         extra={"ENTP1": "J", "ENTP2": "J"}),

    dict(id="sspr", gruppe="Identity & Endgeraeteverwaltung",
         feature="Self-Service Password Reset (Cloud)",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="SSPR gewuenscht (Entlastung Service-Desk), Plan enthaelt nur Entra ID Free -> Upgrade auf Entra ID P1 noetig.",
         trigger_included="Entra ID P1/P2 vorhanden, SSPR-Richtlinie aber nicht aktiviert/nicht auf alle Nutzer ausgerollt -> Konfigurationsluecke, Service-Desk-Entlastung ungenutzt.",
         status=s(BP="J", ME3="J", ME5="J"),
         extra={"ENTP1": "J", "ENTP2": "J"}),

    dict(id="pim", gruppe="Identity & Endgeraeteverwaltung",
         feature="Privileged Identity Management (PIM)",
         severity="High", trigger_typ_included=2,
         trigger_missing="Privilegierte Rollen (Global Admin etc.) sind dauerhaft aktiv statt just-in-time, Plan bietet kein Entra ID P2 -> Upgrade auf Microsoft 365 E5, Entra ID P2 Standalone oder Defender Suite for Business Premium noetig.",
         trigger_included="Entra ID P2 lizenziert, PIM aber nicht konfiguriert (Admin-Rollen weiterhin dauerhaft vergeben) -> Lizenzpotenzial ungenutzt, Finding zu stehenden Adminrechten.",
         status=s(BP="A", ME5="J"),
         extra={"ENTP1": "N", "ENTP2": "J"}),

    dict(id="identity_protection", gruppe="Identity & Endgeraeteverwaltung",
         feature="Identity Protection (risikobasierte Anmeldeerkennung)",
         severity="High", trigger_typ_included=3,
         trigger_missing="Risikobasierte Anmelde-/Nutzererkennung gefordert, Plan bietet nur P1 -> Upgrade auf Entra ID P2 noetig.",
         trigger_included="Entra ID P2 vorhanden, Risk-Policies aber nicht aktiviert -> kompromittierte Konten werden nicht automatisiert blockiert (Sicherheitsrisiko Konfiguration).",
         status=s(BP="A", ME5="J"),
         extra={"ENTP1": "N", "ENTP2": "J"}),

    dict(id="identity_governance", gruppe="Identity & Endgeraeteverwaltung",
         feature="Identity Governance (Access Reviews, Entitlement Management)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Regelmaessige Zugriffsrezertifizierung gefordert (z. B. ISO 27001), Plan bietet kein Entra ID P2 -> Upgrade noetig.",
         trigger_included="Entra ID P2 vorhanden, Access Reviews aber nie eingerichtet -> verwaiste Berechtigungen bleiben unentdeckt.",
         status=s(BP="A", ME5="J"),
         extra={"ENTP1": "N", "ENTP2": "J"}),

    dict(id="intune_full", gruppe="Identity & Endgeraeteverwaltung",
         feature="Microsoft Intune Plan 1 (vollstaendiges MDM/MAM)",
         severity="High", trigger_typ_included=2,
         trigger_missing="Unternehmensweite Geraeteverwaltung (MDM, macOS/iOS/Android/Windows) gewuenscht, Plan bietet nur Basic Mobility and Security -> Upgrade auf Business Premium/Microsoft 365 E3 noetig.",
         trigger_included="Intune lizenziert, Geraete aber nicht (vollstaendig) eingebunden bzw. Policies nicht ausgerollt -> Lizenzpotenzial ungenutzt.",
         status=s(BP="J", ME3="J", ME5="J")),

    dict(id="basic_mobility", gruppe="Identity & Endgeraeteverwaltung",
         feature="Basic Mobility and Security (eingeschraenktes MDM)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Keine MDM-Faehigkeit im Tenant vorhanden, obwohl Basic Mobility and Security lizenzrechtlich verfuegbar waere -> kostenlose Quick-Win-Absicherung ungenutzt (kein Upgrade noetig, nur Aktivierung).",
         trigger_included="Lizenz vorhanden, aber weder Basic Mobility and Security noch Intune aktiv konfiguriert -> Geraete unverwaltet im Zugriff auf Unternehmensdaten.",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="autopilot", gruppe="Identity & Endgeraeteverwaltung",
         feature="Windows Autopilot Support (Self-Service-Rollout)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Automatisiertes Geraete-Rollout gewuenscht, Plan bietet kein Intune (nur Basic Mobility and Security, kein Autopilot) -> Upgrade auf Intune-fuehrenden Plan noetig.",
         trigger_included="Intune/Autopilot lizenziert, Rollout erfolgt aber weiterhin manuell (Imaging vor Ort) -> Lizenzpotenzial ungenutzt, Prozessineffizienz.",
         status=s(BP="J", ME3="J", ME5="J")),

    dict(id="compliance_policies", gruppe="Identity & Endgeraeteverwaltung",
         feature="Compliance Policies (Intune)",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Geraete-Compliance (Verschluesselung, PIN, OS-Version) soll erzwungen werden, Plan bietet kein Intune -> Upgrade noetig.",
         trigger_included="Intune vorhanden, Compliance Policies aber nicht definiert/nicht mit Conditional Access verknuepft -> nicht-konforme Geraete erhalten weiterhin Zugriff (Sicherheitsrisiko Konfiguration).",
         status=s(BP="J", ME3="J", ME5="J")),

    dict(id="config_profiles", gruppe="Identity & Endgeraeteverwaltung",
         feature="Configuration Profiles (Intune)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Zentrale Geraete-Baseline (WLAN/VPN/Zertifikate/Restrictions) gewuenscht, Plan bietet kein Intune -> Upgrade noetig.",
         trigger_included="Intune vorhanden, Konfigurationsprofile aber nicht ausgerollt -> Geraete laufen auf Werkseinstellungen, Lizenzpotenzial ungenutzt.",
         status=s(BP="J", ME3="J", ME5="J")),

    dict(id="app_protection", gruppe="Identity & Endgeraeteverwaltung",
         feature="App Protection Policies / MAM ohne MDM (BYOD)",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Private Endgeraete (BYOD) greifen auf Unternehmensdaten zu, Plan bietet kein Intune-MAM -> Upgrade noetig, Datenabfluss-Risiko auf unverwalteten Geraeten.",
         trigger_included="Intune vorhanden, App-Protection-Policies fuer BYOD aber nicht konfiguriert, obwohl BYOD im Einsatz ist -> Firmendaten in Apps auf privaten Geraeten ungeschuetzt (Sicherheitsrisiko Konfiguration).",
         status=s(BP="J", ME3="J", ME5="J")),

    dict(id="windows_business", gruppe="Identity & Endgeraeteverwaltung",
         feature="Windows 10/11 Business Upgrade-Recht",
         severity="Low", trigger_typ_included=2,
         trigger_missing="n/a (kein Sicherheits-Finding, rein lizenzrechtlich).",
         trigger_included="Windows-Business-Recht vorhanden, Geraete laufen aber weiterhin auf OEM Home/Pro ohne Subscription Activation -> Lizenzpotenzial ungenutzt.",
         status=s(BP="J"),
         hinweis="Nur in der Business-Linie relevant (max. 300 Seats); kein Enterprise-Deployment-Recht (kein VDA, kein Windows Update for Business zentral)."),

    dict(id="windows_enterprise", gruppe="Identity & Endgeraeteverwaltung",
         feature="Windows 11 Enterprise Upgrade-Recht (inkl. Windows Update for Business, Credential Guard, erweiterte Deployment-Kontrollen)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Enterprise-Sicherheitsfeatures (Credential Guard, zentrales BitLocker, Long-Term Servicing) gefordert, Plan bietet nur Windows Business oder gar kein OS-Recht -> Upgrade auf Microsoft 365 E3/E5 noetig (Office 365 E3/E5 OHNE 'Microsoft 365'-Praefix genuegt NICHT).",
         trigger_included="Windows-Enterprise-Recht vorhanden, Geraete laufen aber weiterhin auf Windows Pro ohne Subscription Activation -> Lizenzpotenzial ungenutzt.",
         status=s(ME3="J", ME5="J"),
         hinweis="Kritischer Unterschied Office 365 vs. Microsoft 365: Office 365 E3/E5 enthaelt KEIN Windows-Enterprise-Recht, kein Intune, kein Entra ID P1/P2 (diese Komponenten kommen ausschliesslich aus dem 'Microsoft 365'-Bundle via EMS)."),

    # ---------------- Security & Defender ----------------
    dict(id="eop_baseline", gruppe="Security & Defender",
         feature="Exchange Online Protection Basisschutz (Anti-Malware/Anti-Spam/Anti-Phishing-Spoofing)",
         severity="Low", trigger_typ_included=3,
         trigger_missing="n/a (in jedem Plan mit Exchange Online enthalten).",
         trigger_included="EOP aktiv, Standardrichtlinien aber nicht verschaerft (kein Preset Security Policy 'Standard'/'Strict' zugewiesen) -> Basisschutz bleibt hinter Best Practice zurueck (Sicherheitsrisiko Konfiguration).",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         extra={"EXOP1": "J", "EXOP2": "J"}),

    dict(id="defender_o365_p1", gruppe="Security & Defender",
         feature="Microsoft Defender for Office 365 Plan 1 (Safe Links, Safe Attachments, erweiterter Anti-Phishing/Impersonation-Schutz)",
         severity="High", trigger_typ_included=3,
         trigger_missing="Schutz vor Phishing-Links/schaedlichen Anhaengen gefordert, Plan bietet nur EOP-Basisschutz -> Upgrade auf Business Premium bzw. (O365/M365) E3 noetig.",
         trigger_included="Defender for Office 365 P1 lizenziert, Safe Links/Safe Attachments Policies aber nicht aktiv bzw. nicht auf alle Nutzer angewendet -> Sicherheitsrisiko Konfiguration.",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         hinweis="Seit Repackaging Juli 2026 Bestandteil von E3 (zuvor Business-/E5-exklusiv bzw. kostenpflichtiges Add-on zu E1/E3)."),

    dict(id="defender_o365_p2", gruppe="Security & Defender",
         feature="Microsoft Defender for Office 365 Plan 2 (Threat Explorer, automatisierte Untersuchung & Reaktion)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="SOC-Funktionen (Threat Hunting, automatisierte Reaktion) gefordert, Plan bietet nur P1 -> Upgrade auf (O365/M365) E5 noetig.",
         trigger_included="Defender for Office 365 P2 lizenziert, Threat Explorer/automatisierte Playbooks aber nicht genutzt -> Lizenzpotenzial ungenutzt.",
         status=s(BP="A", OE5="J", ME5="J")),

    dict(id="attack_simulation", gruppe="Security & Defender",
         feature="Attack Simulation Training (Phishing-Simulationskampagnen)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Security-Awareness-Kampagnen gewuenscht, Plan bietet kein Defender for Office 365 P2 -> Upgrade auf E5 bzw. Defender Suite for Business Premium noetig.",
         trigger_included="Feature lizenziert, aber keine Simulationen durchgefuehrt -> Awareness-Potenzial ungenutzt.",
         status=s(BP="A", OE5="J", ME5="J")),

    dict(id="defender_endpoint", gruppe="Security & Defender",
         feature="Endpoint Detection & Response (EDR) / verwalteter Geraete-Virenschutz",
         severity="High", trigger_typ_included=2,
         trigger_missing="Zentral verwalteter Endpoint-Schutz gefordert, Plan bietet keinen Defender for Business/Endpoint -> Drittanbieter-AV oder unverwalteter Windows Defender im Einsatz; Upgrade/Zusatzlizenz noetig.",
         trigger_included="Defender for Business/Endpoint lizenziert, Geraete aber nicht onboarded bzw. Drittanbieter-AV weiterhin im Parallelbetrieb -> Lizenzpotenzial ungenutzt (Shelfware).",
         status=s(BP="J", ME3="J", ME5="J"),
         extra={"DFB": "J", "DFEP1": "J", "DFEP2": "J"},
         hinweis="Business Premium = Defender for Business (Funktionsumfang zwischen DfE P1 und P2, limitiert auf 300 Geraete/Nutzer). Microsoft 365 E3 = Defender for Endpoint Plan 1 (nur Praevention: AV, Angriffsflächenreduzierung, Geraetesteuerung - kein volles EDR). Microsoft 365 E5 = Defender for Endpoint Plan 2 (volles EDR inkl. automatisierter Untersuchung, Threat & Vulnerability Management, 6 Monate Datenretention). Office 365 E3/E5 (ohne 'Microsoft 365') erhalten KEINEN Endpoint-Schutz."),

    dict(id="defender_identity", gruppe="Security & Defender",
         feature="Microsoft Defender for Identity (Bedrohungserkennung fuer Hybrid Active Directory)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Hybrid Active Directory im Einsatz, Plan bietet kein Defender for Identity -> blinder Fleck bei Lateral-Movement-/AD-Angriffen; Upgrade auf Microsoft 365 E5 bzw. Defender Suite for Business Premium noetig.",
         trigger_included="Defender for Identity lizenziert, Sensoren aber nicht auf Domain Controllern installiert -> Lizenzpotenzial ungenutzt.",
         status=s(BP="A", ME5="J"),
         extra={"DFB": "N", "DFEP1": "N", "DFEP2": "N"}),

    dict(id="defender_cloud_apps", gruppe="Security & Defender",
         feature="Microsoft Defender for Cloud Apps (CASB)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Schatten-IT-/Cloud-App-Kontrolle gefordert, Plan bietet kein CASB -> Upgrade auf Microsoft 365 E5 bzw. Defender Suite for Business Premium noetig.",
         trigger_included="CASB lizenziert, aber keine App-Discovery/Session-Policies konfiguriert -> Lizenzpotenzial ungenutzt.",
         status=s(BP="A", ME5="J"),
         extra={"DFB": "N", "DFEP1": "N", "DFEP2": "N"}),

    # ---------------- Compliance & Governance (Purview) ----------------
    dict(id="retention", gruppe="Compliance & Governance (Purview)",
         feature="Retention-Labels & -Richtlinien (Kernfunktion)",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Aufbewahrungspflichten (z. B. handels-/steuerrechtlich) bestehen, Plan bietet keine Purview-Retention-Labels -> Upgrade noetig.",
         trigger_included="Retention-Labels verfuegbar, aber nicht veroeffentlicht/angewendet -> Aufbewahrungspflichten faktisch nicht durchgesetzt (Compliance-/Konfigurationsrisiko).",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="retention_advanced", gruppe="Compliance & Governance (Purview)",
         feature="Erweiterte Retention (Trainable Classifiers, Priority Cleanup, File Plan Manager)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Automatisierte Klassifizierung grosser Datenmengen gewuenscht, Plan bietet nur Kern-Retention -> Upgrade auf E5 bzw. Purview Suite for Business Premium noetig.",
         trigger_included="Feature lizenziert, aber keine Trainable Classifiers im Einsatz -> Lizenzpotenzial ungenutzt.",
         status=s(BP="A", OE5="J", ME5="J")),

    dict(id="dlp_core", gruppe="Compliance & Governance (Purview)",
         feature="Data Loss Prevention (DLP) - Exchange/SharePoint/OneDrive/Teams",
         severity="High", trigger_typ_included=3,
         trigger_missing="Schutz vor Abfluss sensibler Daten (PII/PCI/IBAN) gefordert, Plan bietet kein DLP -> Upgrade auf Business Premium bzw. (O365/M365) E3 noetig.",
         trigger_included="DLP lizenziert, aber keine Richtlinien aktiv (z. B. externe SharePoint-Freigaben ohne Kontrolle sensibler Inhalte) -> Sicherheitsrisiko Konfiguration.",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="dlp_advanced", gruppe="Compliance & Governance (Purview)",
         feature="Erweitertes DLP (Teams-Chat-DLP, Endpoint-DLP fuer USB/Druck/Zwischenablage)",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Exfiltration ueber Endgeraete (USB/Druck/Zwischenablage) oder Teams-Chat soll verhindert werden, Plan bietet nur Kern-DLP -> Upgrade auf E5 noetig.",
         trigger_included="Endpoint-DLP lizenziert, Geraete aber nicht in Scope der Richtlinien -> Lizenzpotenzial ungenutzt.",
         status=s(OE5="J", ME5="J")),

    dict(id="sensitivity_manual", gruppe="Compliance & Governance (Purview)",
         feature="Sensitivity Labels (manuell, inkl. Verschluesselung/Zugriffsbeschraenkung)",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Klassifizierung/Verschluesselung vertraulicher Dokumente gewuenscht, Plan bietet keine Sensitivity Labels -> Upgrade auf Business Premium bzw. (O365/M365) E3 noetig.",
         trigger_included="Sensitivity Labels verfuegbar, aber nicht veroeffentlicht/von Nutzern nicht angewendet -> vertrauliche Dokumente unklassifiziert im Umlauf (Sicherheitsrisiko Konfiguration).",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="sensitivity_auto", gruppe="Compliance & Governance (Purview)",
         feature="Automatische Sensitivity Labels (Auto-Labeling, Default-Labeling SharePoint, Co-Autoring verschluesselter Dateien)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Automatische Klassifizierung ohne Nutzerinteraktion gewuenscht, Plan bietet nur manuelles Labeling -> Upgrade auf E5 bzw. Information Protection Add-on noetig.",
         trigger_included="Auto-Labeling lizenziert, Richtlinien aber nicht konfiguriert -> weiterhin manuelle/inkonsistente Klassifizierung trotz Lizenz.",
         status=s(OE5="J", ME5="J")),

    dict(id="ediscovery_standard", gruppe="Compliance & Governance (Purview)",
         feature="eDiscovery (Standard) - Content Search, Legal Hold, Custodian-Verwaltung",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Rechtliche Aufbewahrung/Herausgabe von Postfach-/Dateiinhalten (Legal Hold) gefordert, Plan bietet nur Basis-Content-Search (E1) oder gar nichts -> Upgrade auf Business Premium bzw. (O365/M365) E3 noetig.",
         trigger_included="eDiscovery Standard verfuegbar, aber keine Cases/Holds eingerichtet -> im Bedarfsfall (Rechtsstreit, Auskunftsersuchen) fehlt ein etablierter Prozess.",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         hinweis="Microsoft 365 E1 bietet nur eingeschraenkte Content Search, keine vollstaendige eDiscovery-(Standard)-Funktionalitaet (kein Custodian-/Hold-Management)."),

    dict(id="ediscovery_premium", gruppe="Compliance & Governance (Purview)",
         feature="eDiscovery (Premium/Advanced) - Predictive Coding, Chain of Custody, Review-Sets",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Komplexe, mehrstufige Rechtsfaelle mit Review-Workflow gefordert, Plan bietet nur eDiscovery Standard -> Upgrade auf E5 bzw. Purview Suite for Business Premium noetig.",
         trigger_included="eDiscovery Premium lizenziert, aber noch nie fuer einen Case genutzt -> Lizenzpotenzial ungenutzt.",
         status=s(BP="A", OE5="J", ME5="J")),

    dict(id="audit_standard", gruppe="Compliance & Governance (Purview)",
         feature="Purview Audit (Standard) - Unified Audit Log, 180 Tage Aufbewahrung",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Nachvollziehbarkeit von Admin-/Nutzeraktivitaeten gefordert (z. B. fuer Incident-Response), Plan/Compliance-Center-Zugriff fehlt -> Upgrade auf Business Premium bzw. E1+ noetig.",
         trigger_included="Audit Standard verfuegbar, Suche/Auswertung erfolgt aber nicht regelmaessig bzw. keine Alerting-Policies eingerichtet -> Vorfaelle werden zu spaet erkannt (Sicherheitsrisiko Konfiguration).",
         status=s(BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         hinweis="Business Basic/Standard haben keinen Zugriff auf das Purview Compliance Center und damit faktisch keine durchsuchbare Audit-Log-Oberflaeche."),

    dict(id="audit_premium", gruppe="Compliance & Governance (Purview)",
         feature="Purview Audit (Premium) - laengere Aufbewahrung (>180 Tage), forensische Ereignisse (z. B. MailItemsAccessed)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Forensische Untersuchung nach Postfach-Kompromittierung (z. B. Business E-Mail Compromise) gefordert, Plan bietet nur Audit Standard -> Upgrade auf E5 noetig.",
         trigger_included="Audit Premium lizenziert, hoehere Log-Retention aber nicht als Aufbewahrungsrichtlinie konfiguriert -> Beweismittel verfallen trotz Lizenz nach Standardfrist.",
         status=s(OE5="J", ME5="J")),

    dict(id="insider_risk", gruppe="Compliance & Governance (Purview)",
         feature="Insider Risk Management",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Erkennung riskanten Insider-Verhaltens (Datenabfluss vor Kuendigung etc.) gewuenscht, Plan bietet kein Insider Risk Management -> Upgrade auf E5 noetig.",
         trigger_included="Feature lizenziert, aber keine Richtlinien/Indikatoren konfiguriert -> Lizenzpotenzial ungenutzt.",
         status=s(OE5="J", ME5="J")),

    dict(id="comm_compliance", gruppe="Compliance & Governance (Purview)",
         feature="Communication Compliance (Ueberwachung interner/externer Kommunikation, z. B. Belaestigung, Insider Trading)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Regulatorische Kommunikationsueberwachung gefordert (z. B. Finanzbranche), Plan bietet dies nicht -> Upgrade auf E5 noetig.",
         trigger_included="Feature lizenziert, aber keine Richtlinien konfiguriert -> Lizenzpotenzial ungenutzt.",
         status=s(OE5="J", ME5="J")),

    # ---------------- Kollaboration & Office-Plattform ----------------
    dict(id="office_desktop", gruppe="Kollaboration & Office-Plattform",
         feature="Office Desktop-Apps (lokale Installation Word/Excel/PowerPoint/Outlook)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Nutzer benoetigen Offline-/Vollfunktions-Office, Plan bietet nur Web-/Mobile-Apps -> Upgrade auf Business Standard/Premium bzw. E3/E5 noetig.",
         trigger_included="Desktop-Apps lizenziert, Nutzer arbeiten aber laut Befragung ausschliesslich mit Web-Apps -> Lizenzpotenzial ungenutzt, Downgrade-Pruefung moeglich.",
         status=s(BS="J", BP="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="shared_computer_activation", gruppe="Kollaboration & Office-Plattform",
         feature="Shared Computer Activation (Mehrbenutzerbetrieb auf RDS/Terminalserver/VDI)",
         severity="High", trigger_typ_included=2,
         trigger_missing="Office wird auf Terminalserver/RDS mit mehreren gleichzeitigen Benutzern eingesetzt, aktueller Plan (Business Standard/Basic) unterstuetzt jedoch keine Shared Computer Activation -> Aktivierungsfehler und Lizenzverstoss; Upgrade auf Business Premium oder E3/E5 zwingend erforderlich.",
         trigger_included="SCA-faehige Lizenz vorhanden, wird aber nicht fuer Terminalserver-Bereitstellung nachgewiesen/genutzt -> pruefen, ob RDS/VDI tatsaechlich im Einsatz ist (sonst kein Finding).",
         status=s(BP="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         hinweis="Microsoft 365 Apps for business (Business Standard) unterstuetzt KEINE Shared Computer Activation - nur Microsoft 365 Apps for enterprise (Business Premium, E3, E5)."),

    dict(id="teams", gruppe="Kollaboration & Office-Plattform",
         feature="Microsoft Teams",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Teams wird genutzt/gewuenscht, ist im aktuellen (nach der weltweiten Entbuendelung ab 2024/2025 abgeschlossenen) Neuvertrag aber nicht mehr automatisch enthalten -> separate Teams-Lizenz (Microsoft Teams Enterprise/Business) erforderlich, sonst Lizenzverstoss bei Nutzung.",
         trigger_included="Teams-Lizenz vorhanden, Adoption aber gering (Drittanbieter-Tool wie Zoom/Slack im Parallelbetrieb) -> doppelte Kollaborationskosten, Konsolidierungspotenzial.",
         status=s(BB="A", BS="A", BP="A", ME1="A", OE3="A", ME3="A", OE5="A", ME5="A"),
         hinweis="Bei Vertragsabschluss vor dem jeweiligen Stichtag (EEA: 01.10.2023 / weltweit: 01.04.2024) bleibt Teams im Bestandsvertrag gebuendelt ('Ja'). Bei jedem Neuvertrag bzw. Lizenzwechsel danach ist Teams separat (meist ohne Aufpreis) zu lizenzieren - im Rahmen der Bestandsaufnahme daher IMMER pruefen, welches Vertragsdatum/-modell vorliegt."),

    dict(id="teams_phone", gruppe="Kollaboration & Office-Plattform",
         feature="Teams Phone Standard (Cloud-Telefonanlage/PBX)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="Kunde nutzt/wuenscht Teams als Telefonanlagen-Ersatz, Plan bietet keine Teams-Telefonie -> Zusatzlizenz Teams Phone Standard (+ ggf. Calling Plan/Operator Connect fuer PSTN) erforderlich.",
         trigger_included="Teams Phone lizenziert (E5), PSTN-Anbindung/Rufnummern aber nicht eingerichtet -> Telefonanlagen-Konsolidierungspotenzial ungenutzt.",
         status=s(OE5="J", ME5="J"),
         hinweis="PSTN-Anbindung (tatsaechliche Amtsleitung) ist selbst in E5 NICHT enthalten und erfordert zusaetzlich Calling Plan oder Operator Connect/Direct Routing."),

    dict(id="audio_conferencing", gruppe="Kollaboration & Office-Plattform",
         feature="Audio Conferencing (Telefon-Einwahl zu Teams-Meetings)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="n/a (mittlerweile kostenlos in praktisch allen Teams-faehigen Plaenen enthalten).",
         trigger_included="Audio Conferencing verfuegbar, Einwahlrufnummern aber nicht aktiviert -> internationale/mobile Teilnehmer koennen nicht teilnehmen (Quick Win).",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="mailbox_quota", gruppe="Kollaboration & Office-Plattform",
         feature="Exchange-Postfach-Kontingent & Auto-Expanding Archive",
         severity="Medium", trigger_typ_included=2,
         trigger_missing="Postfaecher stossen an die 50-GB-Grenze (Business-Linie/E1/Exchange Online Plan 1), Nutzer benoetigen mehr Ablage -> Upgrade auf einen Plan mit 100 GB + unbegrenztem Auto-Expanding Archive (E3/E5/Exchange Online Plan 2) noetig.",
         trigger_included="Groesseres Kontingent lizenziert, Altdaten liegen aber weiterhin lokal in PST-Dateien statt in der Cloud-Archivierung -> Backup-/Compliance-Luecke trotz vorhandener Lizenz.",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J"),
         extra={"EXOP1": "J", "EXOP2": "J"},
         hinweis="Business Basic/Standard/Premium und Microsoft 365 E1 entsprechen dem Exchange-Online-Plan-1-Niveau: 50 GB Primaerpostfach, KEIN Auto-Expanding Archive. (O365/M365) E3 und E5 entsprechen Exchange-Online-Plan-2-Niveau: 100 GB Primaerpostfach + unbegrenztes Auto-Expanding Archive (bis 1,5 TB via automatischer Erweiterung)."),

    dict(id="litigation_hold", gruppe="Kollaboration & Office-Plattform",
         feature="Litigation Hold / In-Place Hold",
         severity="Medium", trigger_typ_included=3,
         trigger_missing="Rechtliche Aufbewahrungspflicht (Litigation Hold) gefordert, Plan bietet nur Exchange-Online-Plan-1-Niveau -> Upgrade auf (O365/M365) E3/E5 bzw. Exchange Online Plan 2 noetig.",
         trigger_included="Litigation Hold verfuegbar, aber nicht auf betroffene Postfaecher angewendet -> Beweismittel koennten im Bedarfsfall fehlen (Compliance-Risiko Konfiguration).",
         status=s(OE3="J", ME3="J", OE5="J", ME5="J"),
         extra={"EXOP1": "N", "EXOP2": "J"}),

    dict(id="sharepoint_quota", gruppe="Kollaboration & Office-Plattform",
         feature="SharePoint-Speicherkontingent (Tenant-Pool)",
         severity="Low", trigger_typ_included=2,
         trigger_missing="n/a (Basiskontingent in jedem Plan mit SharePoint Online enthalten).",
         trigger_included="Kontingent vorhanden (1 TB Basis + 10 GB je lizenziertem Nutzer, gepoolt), Nutzung wird aber nicht ueberwacht -> Gefahr eines Tenant-weiten Storage-Engpasses (schreibgeschuetzte Sites) ohne Fruehwarnung.",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J")),

    dict(id="onedrive_quota", gruppe="Kollaboration & Office-Plattform",
         feature="OneDrive-Speicherkontingent pro Nutzer",
         severity="Low", trigger_typ_included=2,
         trigger_missing="n/a (1 TB pro Nutzer in jedem Plan mit OneDrive enthalten, erweiterbar bis 5 TB je nach Tenant-Groesse).",
         trigger_included="Kontingent vorhanden, Synchronisationsverhalten/Freigabeeinstellungen aber nicht ueberprueft -> ungeprueftes Risiko externer Freigaben auf Nutzerebene.",
         status=s(BB="J", BS="J", BP="J", ME1="J", OE3="J", ME3="J", OE5="J", ME5="J")),
]

STATUS_LABEL = {"J": "Ja", "N": "Nein", "A": "Add-on"}
TRIGGER_LABEL = {
    1: "Trigger 1 - Unterlizenzierung / fehlendes Feature",
    2: "Trigger 2 - Ungenutzte Lizenzwerte / Shelfware",
    3: "Trigger 3 - Sicherheitsluecke durch Fehlkonfiguration",
}

# Plan-Kuerzel -> Feldwert im Schema m365_security (Feld `m365_lizenzen`).
# Die Matrix traegt den Code pro Zeile mit, damit die Laufzeit-Suche ueber
# den Code geht und nicht ueber den Anzeigenamen: ein umbenannter Plan
# ("Office 365 E3" -> "Microsoft 365 ...") wuerde sonst still ins Leere greifen.
PLAN_CODES = {
    "BB": "bb", "BS": "bs", "BP": "bp", "ME1": "me1", "OE3": "oe3",
    "ME3": "me3", "OE5": "oe5", "ME5": "me5", "EXOP1": "exop1",
    "EXOP2": "exop2", "ENTP1": "entp1", "ENTP2": "entp2",
    "DFB": "dfb", "DFEP1": "dfep1", "DFEP2": "dfep2",
}

# Schweregrad der Matrix -> Schweregrad der Regel-Engine.
SEVERITY_MAP = {"High": "hoch", "Medium": "mittel", "Low": "niedrig"}

EVIDENZ_STUFEN = ("bestaetigt", "wahrscheinlich", "umstritten", "unbestaetigt")

# Evidenzlage je Feature (Konzept aus Matrix B, siehe #407).
#
# Bewusst konservativ: Der Katalog oben ist ein Rechercheergebnis, das noch
# niemand Zeile fuer Zeile gegen learn.microsoft.com gegengeprueft hat.
# Alles gilt deshalb als `unbestaetigt`, solange keine Primaerquelle
# hinterlegt ist. Ein optimistischer Default wuerde die Luecke genau dort
# unsichtbar machen, wo sie zaehlt — beim Kunden im Bericht.
EVIDENZ_DEFAULT = ("unbestaetigt", "")
EVIDENZ = {
    # Im Matrixvergleich (#407) ausdruecklich als offener Pruefpunkt benannt:
    # Matrix A nimmt eine Standardformel an, Matrix B markiert dieselbe
    # Angabe als Wissensluecke. Bis das geklaert ist: umstritten.
    "sharepoint_quota": ("umstritten", ""),
    "audio_conferencing": ("umstritten", ""),
}


def build_rows():
    """Expandiert den Feature-Katalog zur flachen Matrix (1 Zeile = Plan x Feature)."""
    rows = []
    for feat in FEATURES:
        evidenzstatus, quelle = EVIDENZ.get(feat["id"], EVIDENZ_DEFAULT)
        if evidenzstatus not in EVIDENZ_STUFEN:
            raise ValueError(f"Unbekannte Evidenzstufe '{evidenzstatus}' bei {feat['id']}")

        combined_status = dict(feat["status"])
        combined_status.update(feat.get("extra", {}))
        for plan_id, code in combined_status.items():
            plan = PLANS[plan_id]
            if code == "N":
                finding_trigger = feat["trigger_missing"]
                trigger_typ = 1
            else:
                finding_trigger = feat["trigger_included"]
                trigger_typ = feat["trigger_typ_included"]
            rows.append({
                "lizenzplan": plan["name"],
                "lizenzcode": PLAN_CODES[plan_id],
                "lizenzfamilie": plan["familie"],
                "seat_range": plan["seats"],
                "feature_gruppe": feat["gruppe"],
                "feature": feat["feature"],
                "enthalten": STATUS_LABEL[code],
                "empfohlener_finding_trigger": finding_trigger,
                "schweregrad": feat["severity"],
                "schweregrad_regel": SEVERITY_MAP[feat["severity"]],
                "trigger_typ": trigger_typ,
                "trigger_typ_bezeichnung": TRIGGER_LABEL[trigger_typ],
                "hinweis": feat.get("hinweis", ""),
                "feature_id": feat["id"],
                "evidenzstatus": evidenzstatus,
                "quelle": quelle,
            })

    plan_order = {pid: i for i, pid in enumerate(PLANS.keys())}
    code_to_order = {PLAN_CODES[pid]: i for pid, i in plan_order.items()}
    rows.sort(key=lambda r: (code_to_order[r["lizenzcode"]], r["feature_gruppe"], r["feature"]))
    return rows


def build_output(rows):
    ungeprueft = sorted({r["feature_id"] for r in rows if r["evidenzstatus"] != "bestaetigt"})
    return {
        "meta": {
            "titel": "M365-Lizenzmatrix & Feature-Trigger fuer das Bestandsaufnahme-Tool",
            "stand": "2026-08-21",
            "erzeugt_von": "tools/build_m365_matrix.py — nicht von Hand bearbeiten",
            "quellen_hinweis": (
                "Zusammengestellt aus offiziellen Microsoft-Learn-/Microsoft-Licensing-Quellen "
                "sowie aktuellen Fachartikeln (Stand August 2026). Microsoft-Lizenzierung aendert "
                "sich regelmaessig (z. B. Repackaging Juli 2026, Teams-Entbuendelung 2024/2025) - "
                "Matrix vor produktivem Einsatz stichprobenartig gegen learn.microsoft.com "
                "verifizieren und in regelmaessigen Abstaenden aktualisieren."
            ),
            "spalten_erklaerung": {
                "enthalten": (
                    "Ja = im Grundpreis enthalten. Nein = nicht verfuegbar, nur durch Upgrade auf "
                    "anderen Plan erreichbar. Add-on = gegen Aufpreis zubuchbar innerhalb desselben "
                    "Plans (z. B. Defender Suite for Business Premium, Purview Suite for Business "
                    "Premium). Nur 'Ja' gilt als lizenziert — 'Add-on' muss der Kunde erst kaufen."
                ),
                "trigger_typ": (
                    "1 = Unterlizenzierung (Feature fehlt, Kunde braucht es -> Upgrade), "
                    "2 = Shelfware (Feature vorhanden, aber ungenutzt -> Aktivierung/Beratung), "
                    "3 = Fehlkonfiguration (Feature vorhanden, aber unsicher/offen konfiguriert -> Haerten)."
                ),
                "evidenzstatus": (
                    "bestaetigt = gegen eine Primaerquelle geprueft (URL in 'quelle'). "
                    "wahrscheinlich = plausibel, aber ohne Primaerquelle. "
                    "umstritten = Quellen widersprechen sich. "
                    "unbestaetigt = noch nicht gegengeprueft (Ausgangszustand)."
                ),
            },
            "anzahl_zeilen": len(rows),
            "abgedeckte_lizenzplaene": [p["name"] for p in PLANS.values()],
            "lizenzcodes": PLAN_CODES,
            "evidenz_offen": {
                "anzahl_features": len(ungeprueft),
                "feature_ids": ungeprueft,
                "hinweis": (
                    "Diese Features sind noch nicht gegen eine Primaerquelle geprueft. "
                    "Vor dem Produktiveinsatz stichprobenartig gegen learn.microsoft.com "
                    "verifizieren und 'quelle' je Feature in tools/build_m365_matrix.py setzen."
                ),
            },
        },
        "matrix": rows,
    }


def schreibe(rows):
    ziel_json = REPO / "rules" / "m365_lizenzmatrix.json"
    with open(ziel_json, "w", encoding="utf-8") as f:
        json.dump(build_output(rows), f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{ziel_json.relative_to(REPO)}: {len(rows)} Zeilen, {len(PLANS)} Plaene")
    offen = sorted({r["feature_id"] for r in rows if r["evidenzstatus"] != "bestaetigt"})
    print(f"Ohne Primaerquelle: {len(offen)} von {len({r['feature_id'] for r in rows})} Features")
    for stufe, n in sorted(Counter(r["evidenzstatus"] for r in rows).items()):
        print(f"  {stufe}: {n} Zeilen")


def bereits_verregelt():
    """Feature-IDs, die in rules/*.yaml schon ueber die Lizenz-Operatoren haengen."""
    import re
    treffer = set()
    for pfad in (REPO / "rules").glob("*.yaml"):
        text = pfad.read_text(encoding="utf-8")
        for m in re.finditer(r"operator:\s*lizenz_deckt(?:_nicht)?\s*\n\s*wert:\s*(\S+)", text):
            treffer.add(m.group(1).strip("\"'"))
    return treffer


def scaffold(feature_id, rows):
    """YAML-Regelgeruest fuer ein Feature — Startpunkt, kein fertiges Regelwerk."""
    zeilen = [r for r in rows if r["feature_id"] == feature_id]
    if not zeilen:
        raise SystemExit(f"Unbekannte feature_id '{feature_id}'")
    beispiel = zeilen[0]
    lizenziert = sorted(r["lizenzcode"] for r in zeilen if r["enthalten"] == "Ja")
    addon = sorted(r["lizenzcode"] for r in zeilen if r["enthalten"] == "Add-on")
    slug = feature_id.replace("_", "-")
    fehlt = next(r["empfohlener_finding_trigger"] for r in zeilen if r["trigger_typ"] == 1)
    drin = next(
        (r["empfohlener_finding_trigger"] for r in zeilen if r["trigger_typ"] != 1),
        "",
    )

    return f"""  # --- Feature: {beispiel['feature']} ({beispiel['feature_gruppe']}) ---
  # Matrix: enthalten in {lizenziert or '-'} | Add-on: {addon or '-'}
  # Schweregrad {beispiel['schweregrad']} | Evidenz: {beispiel['evidenzstatus']}
  #
  # Die Planlisten stehen bewusst NICHT hier: `lizenz_deckt` liest sie zur
  # Laufzeit aus rules/m365_lizenzmatrix.json.
  - id: m365-lizenz-{slug}-fehlt
    gilt_fuer: m365_security
    bedingung:
      alle:
        - feld: m365_lizenzen
          operator: lizenz_deckt_nicht
          wert: {feature_id}
    schweregrad: {beispiel['schweregrad_regel']}
    befund: TODO Kurzbefund
    # Ausgangstext aus der Recherche (#405), vor Uebernahme umformulieren:
    # {fehlt}
    risiko: TODO
    empfehlung: TODO
    referenz: ""
    massnahme_vorschlag:
      bezeichnung: TODO
      kosten_richtwert: 0
      aufwand_richtwert: 2

  - id: m365-{slug}-fehlt
    gilt_fuer: m365_security
    bedingung:
      alle:
        - feld: m365_lizenzen
          operator: lizenz_deckt
          wert: {feature_id}
        # TODO: Schemafeld in schemas/m365_security.yaml ergaenzen und hier eintragen.
        - feld: TODO_SCHEMAFELD
          operator: gleich
          wert: "nein"
    schweregrad: {beispiel['schweregrad_regel']}
    befund: TODO Kurzbefund
    # Ausgangstext aus der Recherche (#405), vor Uebernahme umformulieren:
    # {drin}
    risiko: TODO
    empfehlung: TODO
    referenz: ""
    massnahme_vorschlag:
      bezeichnung: TODO
      kosten_richtwert: 0
      aufwand_richtwert: 2
"""


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scaffold", metavar="FEATURE_ID",
                   help="YAML-Regelgeruest fuer ein Feature ausgeben statt die Matrix zu schreiben")
    p.add_argument("--offen", action="store_true",
                   help="Features auflisten, die noch keine Regel haben")
    args = p.parse_args()

    rows = build_rows()

    if args.offen:
        alle = {r["feature_id"] for r in rows}
        fertig = bereits_verregelt()
        for fid in sorted(alle - fertig):
            gruppe = next(r["feature_gruppe"] for r in rows if r["feature_id"] == fid)
            print(f"{fid:30s} {gruppe}")
        print(f"\n{len(alle - fertig)} offen, {len(fertig)} verregelt, {len(alle)} gesamt")
        return

    if args.scaffold:
        print(scaffold(args.scaffold, rows))
        return

    schreibe(rows)


if __name__ == "__main__":
    main()
