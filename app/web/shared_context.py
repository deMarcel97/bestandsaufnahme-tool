from app.services.storage import storage
from app.services.progress import progress_service


def build_sidebar_context(auftrag) -> dict:
    """Liefert die von _sidebar.html erwarteten Keys (progress_data, findings,
    offene_punkte, massnahmen), damit die 'Noch nicht erfasst'-Chipliste und die
    Baustein-Fortschrittsanzeige auf jeder Auftrags-Unterseite erscheinen, nicht nur
    auf der Übersichtsseite."""
    standorte = storage.list_standorte(auftrag.id)
    objekte = storage.list_objekte(auftrag.id)
    return {
        "progress_data": progress_service.calculate_progress(auftrag.aktive_bausteine, objekte),
        "findings": storage.list_findings(auftrag.id),
        "offene_punkte": progress_service.collect_offene_punkte(auftrag, standorte, objekte, []),
        "massnahmen": storage.list_massnahmen(auftrag.id),
    }
