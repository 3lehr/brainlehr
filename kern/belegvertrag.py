"""Belegvertrag -- allgemeine Form aus openlehr/apps/openlehr/daemon/steuer/
euer_zuordnung.py (_belegt/_selbsttest_regeln), ohne Steuerbezug. ADR-007:
was verweigern koennen muss, gehoert nach brainlehr.

Eine Regel darf nur laden, wenn ihre Fundstelle wortwoertlich in einer der
benannten Quellen steht -- sonst waere sie eine Behauptung, kein Zitat.
Fehlt der Beleg, wirft pruefe_regeln() ValueError statt die Regel klaglos
zu uebernehmen (Vorbild-Verhalten, Modulebene beim Import). Eine Tatsache,
die sich nicht widerspruchsfrei ermitteln laesst, wird None -- nie der
bequeme Wert True/False, siehe _gespeicherte_tatsachen() im Vorbild.
"""

from __future__ import annotations

from typing import Any, Callable


def belegt(fundstelle: str, quellen: dict[str, str]) -> bool:
    """Fundstelle muss wortwoertlich in mindestens einem Quellentext stehen
    (Teilstring-Treffer zaehlt, wie im Vorbild -- ein Substring-Zitat ist
    immer noch woertlich).

    Die leere Fundstelle wird ABGEWIESEN. `"" in text` ist in Python immer
    wahr -- ohne diese Zeile gilt jede Regel ohne Fundstelle als belegt, und
    zwar ausgerechnet die, die gar keine angibt. Gefunden am 2026-08-14 von
    einer unabhaengigen Pruefung, Stunden nach dem Bau; der Selbsttest hatte
    nur echte Fundstellen probiert. Dasselbe gilt fuer eine Fundstelle, die
    nur aus Leerraum besteht."""
    if not fundstelle or not fundstelle.strip():
        return False
    return any(fundstelle in text for text in quellen.values())


def pruefe_regeln(regeln: list[dict[str, Any]], quellen_by_id: dict[str, dict[str, str]]) -> None:
    """Weigert sich mit ValueError, sobald eine Regel keine belegbare
    Fundstelle hat. `regeln`: je Eintrag mindestens {"id", "ziel_id",
    "fundstelle"}. `quellen_by_id`: ziel_id -> {feldname: text}, gegen die
    die Fundstelle geprueft wird."""
    for regel in regeln:
        ziel = quellen_by_id.get(regel["ziel_id"])
        if ziel is None:
            raise ValueError(f"Regel {regel['id']!r}: unbekanntes Ziel {regel['ziel_id']!r}")
        if not belegt(regel["fundstelle"], ziel):
            raise ValueError(
                f"Regel {regel['id']!r}: Fundstelle {regel['fundstelle']!r} steht in keiner Quelle von {regel['ziel_id']!r} -- kein Zitat."
            )


def tatsache(getter: Callable[[], bool]) -> bool | None:
    """Ruft getter() auf; ein ValueError (widerspruechliche Angabe) wird zu
    None -- unbekannt, nie False. Der Aufrufer muss None wie "blockiert
    nichts" behandeln, siehe Vorbild."""
    try:
        return bool(getter())
    except ValueError:
        return None


__all__ = ["belegt", "pruefe_regeln", "tatsache"]
