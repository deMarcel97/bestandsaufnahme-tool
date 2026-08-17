import pytest
from app.services.report_builder import ReportBuilder
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_report_builder_single_snippet_per_field():
    rb = ReportBuilder()

    auftrag = Auftrag(id="a1", projekt_nummer="P1", kunde="Test Kunde", bezeichnung="Analyse 2026")
    sto = Standort(id="sto-1", auftrag_id="a1", bezeichnung="Zentrale", ort="München")
    fw = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="Haupt-Firewall", auftrag_id="a1", standort_id="sto-1",
        daten={"hersteller": "Sophos", "hardware_alter": "unter_3_jahre"}
    )

    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag(["firewall"], [fw])

    report = rb.build_analysebericht(auftrag, [sto], [fw], [], bew, [], ziel_vertraulichkeit="kundentauglich")
    assert "# Analysebericht: IT-Bestandsaufnahme" in report
    assert "Als zentrale Firewall kommt ein System des Herstellers Sophos zum Einsatz." in report
    assert "Die eingesetzte Hardware ist jünger als drei Jahre" in report

def test_structured_textbaustein_extraction():
    rb = ReportBuilder()
    feldef = {
        "typ": "auswahl",
        "werte": [
            {
                "wert": "gut",
                "textbaustein": {
                    "feststellung": "Das System ist ordnungsgemäß konfiguriert.",
                    "auswirkung": "Keine Sicherheitsrisiken identifiziert."
                }
            }
        ]
    }
    extracted = rb._extract_snippet("gut", feldef)
    assert extracted == "Das System ist ordnungsgemäß konfiguriert.\n\nKeine Sicherheitsrisiken identifiziert."


def test_massnahmenkatalog_table_sum_columns_alignment():
    from app.models.massnahme import Massnahme
    rb = ReportBuilder()
    auftrag = Auftrag(id="a-sum-test", kunde="Summenkunde", bezeichnung="Summentest")
    m1 = Massnahme(
        id="m-1",
        bezeichnung="Firewall Update",
        stufe=1,
        investitionskosten=1200.0,
        monatliche_kosten=50.0,
        zeitaufwand=4.0,
        prioritaet="hoch",
        dringlichkeit="hoch",
        foerderprogramm="Digital Jetzt"
    )
    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag([], [])
    report = rb.build_analysebericht(auftrag, [], [], [m1], bew, [], ziel_vertraulichkeit="kundentauglich")

    # Nur die Zeilen im Maßnahmenkatalog prüfen
    massnahmen_section = report.split("## 7. Priorisierter Maßnahmenkatalog")[1].split("##")[0]
    lines = [line.strip() for line in massnahmen_section.split("\n") if line.strip().startswith("|")]
    for line in lines:
        if line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        assert len(cells) == 8, f"Tabellenzeile hat {len(cells)} statt 8 Spalten: {line}"

