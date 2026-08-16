from typing import List, Optional
from pydantic import BaseModel, Field

class Beteiligter(BaseModel):
    name: str = ""
    organisation: str = ""  # eigene Firma, Kunde, Dritter
    rolle: str = "Sonstiges"  # Projektleitung, Techniker, Vertrieb, Ansprechpartner_Kunde, Dienstleister, Sonstiges
    zustaendig_fuer_thema: str = ""
    email: str = ""
    telefon: str = ""
    objekt_id: Optional[str] = None
    notfall_telefon: str = ""
    erreichbarkeit: str = ""
    sla_reaktionszeit: str = ""


class Dokumentenanforderung(BaseModel):
    bezeichnung: str = ""
    angefordert_am: Optional[str] = None
    status: str = "offen"  # angefordert, erhalten, offen, abgelehnt
    bemerkung: str = ""

class Ergebnisartefakt(BaseModel):
    bezeichnung: str = ""
    typ: str = "Analysebericht"  # Analysebericht, Managementsummary, Massnahmenkatalog, Netzdokumentation, Notfalldokumentation
    status: str = "offen"  # offen, in Arbeit, geliefert

class Vertrag(BaseModel):
    bezeichnung: str = ""
    vertragspartner: str = ""
    gegenstand: str = ""
    laufzeit_bis: Optional[str] = None
    kuendigungsfrist: str = ""
    monatliche_kosten: float = 0.0
    ansprechpartner: str = ""
    bemerkung: str = ""

class Aspekt(BaseModel):
    titel: str = ""
    text: str = ""

class Unternehmenskontext(BaseModel):
    kerngeschaeft: str = ""
    anzahl_standorte_kunde: int = 1
    it_abteilung_vorhanden: str = "nein"
    anzahl_mitarbeiter_gesamt: Optional[int] = None
    anzahl_it_mitarbeiter: Optional[int] = None
    anzahl_it_nutzer: Optional[int] = None
    geschaeftszeiten_tage: str = "Montag bis Freitag"
    geschaeftszeiten_von: str = "08:00"
    geschaeftszeiten_bis: str = "17:00"
    geschaeftskritische_systeme: List[Aspekt] = Field(default_factory=list)
    geplante_aenderungen: List[Aspekt] = Field(default_factory=list)
    allgemeine_hinweise: str = ""

    @property
    def empfehlung_rufbereitschaft(self) -> bool:
        return self.geschaeftszeiten_tage == "24/7"

    @property
    def empfehlung_it_dienstleister(self) -> bool:
        return self.it_abteilung_vorhanden == "nein"

class Termine(BaseModel):
    beauftragung: Optional[str] = None
    kickoff: Optional[str] = None
    entwurf_vorlage: Optional[str] = None
    abgabe: Optional[str] = None
    praesentation: Optional[str] = None

    @property
    def hat_termin_warnung(self) -> bool:
        if self.entwurf_vorlage and self.abgabe:
            return self.entwurf_vorlage > self.abgabe
        return False

class Rahmenbedingungen(BaseModel):
    benoetigte_zugaenge: str = ""
    zutrittsregelung: str = ""
    nda_vorhanden: str = "nein"  # ja / nein
    wartungsfenster_einschraenkungen: str = ""
    analysewerkzeuge: str = ""

class Auftrag(BaseModel):
    schema_version: int = 1
    # Zählt bei jedem Speichern hoch. Formulare führen den beim Laden
    # gesehenen Stand mit; weicht er beim Speichern ab, hat jemand anderes
    # zwischenzeitlich gespeichert (siehe StorageService). Bestandsdaten ohne
    # dieses Feld starten bei 1.
    version: int = 1
    id: str
    projekt_nummer: str = ""
    jira_url: Optional[str] = None
    kunde: str = ""
    auftraggeber: str = ""
    bezeichnung: str = ""
    grundlage: str = "Sonstiges"  # Ausschreibung, Angebot, Analyse, Rahmenvertrag, Sonstiges (Auswahl: GRUNDLAGE_OPTIONS in app/web/routes_auftrag.py)
    zweck: List[str] = Field(default_factory=list)  # Infrastrukturanalyse, Migrationsvorbereitung, Notfalldokumentation, Betriebsuebernahme, Optimierung
    aufwand_geplant: float = 0.0
    aufwand_ist: float = 0.0
    aktive_bausteine: List[str] = Field(default_factory=lambda: ["firewall"])
    abgrenzung: str = ""
    termine: Termine = Field(default_factory=Termine)
    beteiligte: List[Beteiligter] = Field(default_factory=list)
    dokumentenanforderung: List[Dokumentenanforderung] = Field(default_factory=list)
    rahmenbedingungen: Rahmenbedingungen = Field(default_factory=Rahmenbedingungen)
    status: str = "Vorbereitung"  # Vorbereitung, Erfassung, Konsolidierung, Bewertung, Abgabe
    vertraulichkeit_default: str = "intern"  # intern, kundentauglich, anonymisiert
    vorgaenger_auftrag: Optional[str] = None
    ergebnisartefakte: List[Ergebnisartefakt] = Field(default_factory=list)
    unternehmenskontext: Unternehmenskontext = Field(default_factory=Unternehmenskontext)
    vertraege: List[Vertrag] = Field(default_factory=list)
    positive_aspekte: List[Aspekt] = Field(default_factory=list)
    negative_aspekte: List[Aspekt] = Field(default_factory=list)
