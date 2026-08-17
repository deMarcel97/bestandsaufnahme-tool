import pytest
from app.services.exporter import ExporterService
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.models.massnahme import Massnahme

def test_exporter_confidentiality_and_anonymization():
    exporter = ExporterService()

    auftrag = Auftrag(id="a1", projekt_nummer="P100", kunde="Gemeinde Musterstadt", bezeichnung="IT-Check")
    sto = Standort(id="sto-1", auftrag_id="a1", bezeichnung="Rathaus")
    fw = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="FW 1", auftrag_id="a1", standort_id="sto-1",
        vertraulichkeit="intern",
        daten={"hersteller": "Fortinet", "ip_adressen": "10.0.0.1"}
    )

    # 1. Kundentauglich mode: intern object is excluded
    report_kd = exporter.export_analysebericht(auftrag, [sto], [fw], [], ziel_vertraulichkeit="kundentauglich")
    assert "Gemeinde Musterstadt" in report_kd
    assert "10.0.0.1" not in report_kd

    # 2. Anonymisiert mode: client name masked, object count preserved
    _, _, filtered_objekte, _ = exporter._filter_and_evaluate(auftrag, [sto], [fw], "anonymisiert")
    assert len(filtered_objekte) == 1, "Anonymisierung muss Objektanzahl unverändert erhalten"

    report_anon = exporter.export_analysebericht(auftrag, [sto], [fw], [], ziel_vertraulichkeit="anonymisiert")
    assert "[ANONYMISIERT]" in report_anon

def test_csv_exporter():
    exporter = ExporterService()
    m = Massnahme(id="m1", bezeichnung="USV Erneuern", stufe=1, investitionskosten=1500.0, prioritaet="hoch")
    # Die Stufe wird bewusst mitgegeben: seit #310 hat die Signatur keinen
    # stillen Vorgabewert mehr, der sonst „kundentauglich" angenommen hätte.
    csv_out = exporter.export_massnahmenkatalog_csv([m], ziel_vertraulichkeit="kundentauglich")
    assert "USV Erneuern" in csv_out
    assert "1500.00" in csv_out

def test_docx_exporter():
    exporter = ExporterService()
    auftrag = Auftrag(id="a1", projekt_nummer="P100", kunde="Musterkunde", bezeichnung="IT-Check")
    sto = Standort(id="sto-1", auftrag_id="a1", bezeichnung="Zentrale")
    fw = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="FW 1", auftrag_id="a1", standort_id="sto-1",
        vertraulichkeit="kundentauglich",
        daten={"hersteller": "Fortinet", "hardware_alter": "1_bis_3_jahre"}
    )
    docx_stream = exporter.export_analysebericht_docx(auftrag, [sto], [fw], [], ziel_vertraulichkeit="kundentauglich")
    assert docx_stream is not None
    assert docx_stream.getbuffer().nbytes > 0


def test_massnahmenkatalog_md_export_sum_columns_alignment():
    exporter = ExporterService()
    m1 = Massnahme(
        id="m1",
        bezeichnung="USV Erneuern",
        beschreibung="Alte USV austauschen",
        stufe=1,
        investitionskosten=1500.0,
        monatliche_kosten=0.0,
        zeitaufwand=2.0,
        prioritaet="hoch",
        dringlichkeit="hoch",
        foerderprogramm="Digitalbonus"
    )
    md_out = exporter.export_massnahmenkatalog_md([m1], ziel_vertraulichkeit="kundentauglich")
    lines = [line.strip() for line in md_out.split("\n") if line.strip().startswith("|")]
    for line in lines:
        if line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        assert len(cells) == 9, f"Tabellenzeile hat {len(cells)} statt 9 Spalten: {line}"


