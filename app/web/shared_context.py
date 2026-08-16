from app.services.storage import storage
from app.services.progress import progress_service


def build_sidebar_context(auftrag, standorte=None, objekte=None) -> dict:
    """Liefert die von _sidebar.html erwarteten Keys (progress_data, findings,
    offene_punkte, massnahmen), damit die 'Noch nicht erfasst'-Chipliste und die
    Baustein-Fortschrittsanzeige auf jeder Auftrags-Unterseite erscheinen, nicht nur
    auf der Übersichtsseite.

    Routen, die Standorte und Objekte ohnehin schon geladen haben, reichen sie durch,
    damit dieselben Dateien nicht ein zweites Mal von der Platte gelesen werden."""
    if standorte is None:
        standorte = storage.list_standorte(auftrag.id)
    if objekte is None:
        objekte = storage.list_objekte(auftrag.id)
    return {
        "progress_data": progress_service.calculate_progress(auftrag.aktive_bausteine, objekte),
        "findings": storage.list_findings(auftrag.id),
        "offene_punkte": progress_service.collect_offene_punkte(auftrag, standorte, objekte, []),
        "massnahmen": storage.list_massnahmen(auftrag.id),
    }


def aktuelle_version(auftrag_id: str, fallback: int) -> int:
    """Der Stand, der nach einem Konflikt auf der Platte liegt.

    Das Formular geht damit zurück an den Benutzer, damit ein zweites Speichern
    die fremde Änderung bewusst überschreiben kann, statt in derselben Meldung
    hängenzubleiben (Karte #308).

    Steht hier, weil inzwischen fünf Auftrags-Unterseiten dieselbe
    Konflikterkennung führen. Als private Kopie in jedem Route-Modul wäre der
    Tag absehbar gekommen, an dem eine davon nicht mitgezogen wird.
    """
    aktuell = storage.load_auftrag(auftrag_id)
    return aktuell.version if aktuell else fallback
