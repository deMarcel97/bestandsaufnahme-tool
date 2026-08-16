"""Wiederholbare Unterformulare aus dem POST einlesen.

Beteiligte, Verträge, Unterlagen, Ergebnisartefakte und die Aspekt-Listen sind
alle dasselbe: eine beliebig lange Reihe gleichartiger Datensätze in einem
Formular. Die Felder heissen `<praefix>_<feld>_<index>`, also etwa
`beteiligter_name_0`, `beteiligter_email_0`, `beteiligter_name_1`.

Das Muster stammt aus `routes_standort.py::_parse_anbindungen_from_form`
(Internetanbindungen). Es hier ein zweites bis sechstes Mal abzuschreiben hiesse
fünfmal dieselben zwanzig Zeilen, jede mit eigener Gelegenheit für einen
Tippfehler — deshalb einmal allgemein, mit den Feldnamen aus dem Modell statt
aus einer gepflegten Liste (Karte #316).

Die Anbindungen selbst bleiben bewusst bei ihrem eigenen Parser: sie haben
Kästchen-Felder und eine Sonderregel für „vorhanden", die hier nur als
Sonderfall wieder auftauchen würde.
"""

from typing import Optional, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel

from app.utils.number_parser import parse_float_german, parse_int_german

T = TypeVar("T", bound=BaseModel)


def _zieltyp(annotation) -> type:
    """Der Typ hinter einem `Optional[X]` — sonst die Annotation selbst."""
    if get_origin(annotation) is not None:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _indizes(form_data, praefix: str, felder: list[str]) -> list[int]:
    """Alle Zeilennummern, zu denen das Formular überhaupt ein Feld mitschickt.

    Bewusst über die Feldnamen des Modells statt über „alles, was auf eine Zahl
    endet": im selben Formular stehen weitere Felder, und ein `anzahl_2` hätte
    sonst eine leere Zeile 2 erzeugt.
    """
    gefunden = set()
    for key in form_data.keys():
        for feld in felder:
            vorsatz = f"{praefix}_{feld}_"
            if key.startswith(vorsatz):
                idx = parse_int_german(key[len(vorsatz):], -1)
                if idx >= 0:
                    gefunden.add(idx)
    return sorted(gefunden)


def parse_unterobjekte(form_data, praefix: str, modell: Type[T]) -> list[T]:
    """Baut aus den Formularfeldern eine Liste von `modell`-Objekten.

    Leere Zeilen fallen heraus: wer ein Unterformular hinzufügt und dann doch
    nichts einträgt, soll keinen leeren Datensatz hinterlassen. Als „leer" gilt
    eine Zeile, in der kein einziges Feld vom Vorgabewert des Modells abweicht.

    Der Vergleich gegen den Vorgabewert ist der Kern, nicht nur gegen den leeren
    String: ein `<select>` schickt **immer** einen Wert mit, auch für eine
    unberührte Zeile. Ein `status`-Feld mit der Vorauswahl „offen" hätte sonst
    jede leere Zeile als Eingabe gelten lassen, und die Prüfung wäre wirkungslos
    gewesen (beim Bau der Unterlagen-Seite aufgefallen, Karte #316).
    """
    felder = list(modell.model_fields.keys())
    ergebnis: list[T] = []

    for idx in _indizes(form_data, praefix, felder):
        werte: dict = {}
        etwas_eingetragen = False

        for feld, info in modell.model_fields.items():
            roh = form_data.get(f"{praefix}_{feld}_{idx}")
            if roh is None:
                continue
            roh = str(roh).strip()
            typ = _zieltyp(info.annotation)

            if typ is float:
                zahl = parse_float_german(roh)
                werte[feld] = zahl
                if zahl != info.default:
                    etwas_eingetragen = True
            elif typ is int:
                zahl = parse_int_german(roh, 0)
                werte[feld] = zahl
                if zahl != info.default:
                    etwas_eingetragen = True
            else:
                # Optionale Textfelder (Datumsangaben) bleiben leer statt "" zu
                # speichern — sonst steht im YAML ein leerer String, wo das
                # Modell None meint.
                if not roh and _ist_optional(info.annotation):
                    werte[feld] = None
                    continue
                werte[feld] = roh
                if roh and roh != info.default:
                    etwas_eingetragen = True

        if etwas_eingetragen:
            ergebnis.append(modell(**werte))

    return ergebnis


def _ist_optional(annotation) -> bool:
    return get_origin(annotation) is not None and type(None) in get_args(annotation)
