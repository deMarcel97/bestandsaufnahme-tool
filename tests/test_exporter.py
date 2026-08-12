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
    csv_out = exporter.export_massnahmenkatalog_csv([m])
    assert "USV Erneuern" in csv_out
    assert "1500.00" in csv_out
