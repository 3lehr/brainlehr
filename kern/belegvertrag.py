"""Belegvertrag -- allgemeine Form aus openlehr/apps/openlehr/daemon/steuer/
euer_zuordnung.py (_belegt/_selbsttest_regeln), ohne Steuerbezug. ADR-007:
was verweigern koennen muss, gehoert nach brainlehr.

Eine Regel darf nur laden, wenn ihre Fundstelle wortwoertlich in einer der
benannten Quellen steht -- sonst waere sie eine Behauptung, kein Zitat.
Fehlt der Beleg, wirft pruefe_regeln() ValueError statt die Regel klaglos
zu uebernehmen (Vorbild-Verhalten, Modulebene beim Import). Eine Tatsache,
die sich nicht widerspruchsfrei ermitteln laesst, wird None -- nie der
bequeme Wert True/False, siehe _gespeicherte_tatsachen() im Vorbild.

FUND O3 (docs/SICHERHEITSFUNDE_2026-08-14.md): dieser Vertrag prueft
Selbstkonsistenz, nicht Herkunft -- Regel und Quelle kommen aus derselben
Paketdatei, eine erfundene Quelle mit woertlich passender Fundstelle wird
angenommen. herkunftsart() unten macht die Herkunft wenigstens UNTERSCHEIDBAR:
'mitgeliefert' (Vorgabe, der Normalfall -- der Quellentext steht im Paket
selbst, z.B. ein eingefuegter Gesetzestext; das bleibt Selbstkonsistenz, kein
externer Beleg) gegen 'bestand' (die Quelle behauptet, ein bereits
VORHANDENER, von diesem Paket unabhaengiger Bestandsknoten zu sein -- ob das
stimmt, kann dieses Modul nicht pruefen, es hat keinen DB-Zugriff; das prueft
der Aufrufer, kern/domaene.py::pruefe(), gegen die echte Datenbank). Eine
dritte Art -- extern nachpruefbare Zitate wie Gesetz/DIN/ISO -- erkennt und
prueft bereits kern/normbezug.py im Fliesstext; das wird hier nicht
verdoppelt, nur nicht blockiert (ein Quellentext mit einem solchen Zitat
bleibt 'mitgeliefert' und kann spaeter zusaetzlich dort geprueft werden)."""

from __future__ import annotations

from typing import Any, Callable

# Reserviertes Feld in einer Quelle (dict[str, str]) fuer ihre Herkunftsart --
# fuehrender Unterstrich, damit es nie mit einem echten Beleg-Feldnamen
# ("bezeichnung", "hinweistext", ...) kollidiert.
_HERKUNFT_SCHLUESSEL = "_herkunft"


def herkunftsart(quelle: dict[str, Any]) -> tuple[str, str | None]:
    """Woher eine Quelle sich ausweist. Traegt sie kein '_herkunft'-Feld
    (der ueberwiegende, heutige Fall -- siehe pakete/steuer.domaene.json),
    gilt 'mitgeliefert': der Text kommt aus demselben Paket wie die Regel,
    die er belegen soll. Beginnt '_herkunft' mit 'bestand:', behauptet die
    Quelle, ein vorhandener Bestandsknoten mit dieser id zu sein; die id wird
    mitgeliefert, aber NICHT hier geprueft. Rueckgabe: (art, bestand_id)."""
    wert = quelle.get(_HERKUNFT_SCHLUESSEL) if isinstance(quelle, dict) else None
    if isinstance(wert, str) and wert.startswith("bestand:"):
        bestand_id = wert[len("bestand:"):].strip()
        return ("bestand", bestand_id or None)
    return ("mitgeliefert", None)


def belegt(fundstelle: str, quellen: dict[str, str]) -> bool:
    """Fundstelle muss wortwoertlich in mindestens einem Quellentext stehen
    (Teilstring-Treffer zaehlt, wie im Vorbild -- ein Substring-Zitat ist
    immer noch woertlich). Das reservierte '_herkunft'-Feld selbst zaehlt
    nicht als Belegtext -- sonst koennte eine Fundstelle wie "bestand" durch
    das eigene Herkunftsfeld belegt werden, ein Beleg ueber ein Steuerfeld
    statt ueber Inhalt.

    Die leere Fundstelle wird ABGEWIESEN. `"" in text` ist in Python immer
    wahr -- ohne diese Zeile gilt jede Regel ohne Fundstelle als belegt, und
    zwar ausgerechnet die, die gar keine angibt. Gefunden am 2026-08-14 von
    einer unabhaengigen Pruefung, Stunden nach dem Bau; der Selbsttest hatte
    nur echte Fundstellen probiert. Dasselbe gilt fuer eine Fundstelle, die
    nur aus Leerraum besteht."""
    if not fundstelle or not fundstelle.strip():
        return False
    return any(
        fundstelle in text
        for feld, text in quellen.items()
        if feld != _HERKUNFT_SCHLUESSEL and isinstance(text, str)
    )


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


__all__ = ["belegt", "herkunftsart", "pruefe_regeln", "tatsache"]
