"""Eine Namensfrage erkennen und den Eigennamen herausloesen -- P18
(docs/PLAN_NAECHSTE_STUFE_2026-08-21.md, docs/REQUIREMENTS_BRAINLEHR.md).

DER BEFUND (gemessen 2026-08-21 gegen den echten Bestand, s. runs/
namensfrage_2026-08-21.json): der blosse Name "Döldissen" findet alle drei
bekannten Ziele (Rang 1-3). Die natuerliche Frage "zeige mir alles was mit
Frau Döldissen zu tun hat" findet nur eins -- nicht weil die Kandidaten
fehlen (sie stehen alle drei im vollen OR-Fund, nur auf Rang 0/6/20 statt
0/1/2), sondern weil Fuellwoerter ("zeige", "mit", "zu", "tun", "hat") und
vor allem die ANREDE "Frau" den Namen verduennen: "Frau" trifft einen
ANDEREN Knoten (koeder-frau-elvira-quenzelbach) und zieht ihn vor die
eigentlichen Ziele.

VERFAHREN: kein Modell, keine neue Abhaengigkeit (Stdlib, wie
kern/spracherkennung.py). Eine Anrede (Frau/Herr/Herrn/Familie) MARKIERT
den folgenden Eigennamen, wird selbst aber nicht als Name behandelt --
genau das war die Luecke: "Frau" allein waere ein Grossschreibungs-Treffer
UND ein Stoppwort-Nicht-Treffer, aber kein Name.

WARUM NUR DIE ANREDE UND NICHT "grossgeschrieben + kein Stoppwort" ALLEIN:
Deutsche Substantive sind IMMER grossgeschrieben, auch mitten im Satz
("wie funktioniert die Herkunftsschranke") -- eine reine Grossschreibungs-
Heuristik traefe jede Sachfrage. Der Anker macht daraus ein Signal statt
eines Rauschens: er kommt in einer Sachfrage praktisch nicht vor (0 Treffer
in runs/pruefkorpus.jsonl, 45 Faelle -- s. Selbsttest unten).

Stoppwortliste wiederverwendet aus kern/spracherkennung.py (DE ∪ EN, 36
Woerter) -- nicht um Sprache zu erkennen, sondern um einen grossgeschriebenen
Satzanfang nach der Anrede ("Frau, Wenn Sie...") nicht versehentlich als
Namen zu nehmen. Das Verfahren selbst (Anker statt Klassifikation) ist NICHT
wiederverwendet, es existierte vorher nicht.

GRENZE (ponytail: absichtlich, Ausbau erst bei Bedarf): ein Name OHNE Anrede
("Anna Schmidt kommt morgen") wird NICHT erkannt. Das ist der einzige im
Auftrag gemessene Fehlschlag (Anrede-Verduennung) -- eine allgemeine
Namenserkennung (z.B. zwei aufeinanderfolgende grossgeschriebene Woerter)
ist spekulativ, solange kein Fall sie verlangt."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import re

import spracherkennung

# Anreden -- MARKIEREN einen Namen, sind selbst NIE der Name (die Falle, an
# der der schlechte Lauf gescheitert ist, s. Moduldoc).
ANREDEN = frozenset({"frau", "herr", "herrn", "familie"})

# Bis zu drei Woerter nach der Anrede ("Frau Elvira Quenzelbach") -- mehr
# waere fuer einen Namen ungewoehnlich und faengt eher einen Nebensatz ein.
MAX_NAMENSLAENGE = 3

_WORT_RE = re.compile(r"\w+", re.UNICODE)

# Gleiche Umlautfaltung wie spracherkennung.py/knowledge_recall_hook.py --
# nicht importiert, absichtlich dupliziert (Begruendung dort: abhaengigkeits-
# frei bleiben, jede Datei faltet fuer sich selbst).
_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _stoppwort(wort: str) -> bool:
    gefaltet = wort.lower().translate(_FOLD_TABLE)
    return gefaltet in spracherkennung.DE or gefaltet in spracherkennung.EN


def eigennamen(text: str | None) -> list[str]:
    """Liste der Eigennamen, je einer je Anrede-Fund, Reihenfolge und
    Dubletten wie im Text (erste Nennung gewinnt). Leere Liste heisst: keine
    Anrede gefunden ODER der Anrede folgte kein brauchbarer Name -- beides
    ist "keine Namensfrage", keine Unterscheidung noetig fuer den Aufrufer."""
    if not text:
        return []
    tokens = _WORT_RE.findall(text)
    namen: list[str] = []
    gesehen: set[str] = set()
    i, n = 0, len(tokens)
    while i < n:
        wort = tokens[i]
        if wort.lower() not in ANREDEN:
            i += 1
            continue
        j = i + 1
        lauf: list[str] = []
        while j < n and len(lauf) < MAX_NAMENSLAENGE:
            kandidat = tokens[j]
            if not kandidat.isalpha() or not kandidat[0].isupper():
                break
            if kandidat.lower() in ANREDEN or _stoppwort(kandidat):
                break
            lauf.append(kandidat)
            j += 1
        if lauf:
            name = " ".join(lauf)
            if name not in gesehen:
                namen.append(name)
                gesehen.add(name)
            i = j
        else:
            i += 1
    return namen


def _selftest() -> None:
    # Der Auftragsfall selbst.
    assert eigennamen("zeige mir alles was mit Frau Döldissen zu tun hat") == ["Döldissen"]
    assert eigennamen("Döldissen") == [], "blosser Name ohne Anrede ist kein Ankerfund (braucht ihn auch nicht)"

    # Mehrwortname nach Anrede.
    assert eigennamen("Termine fuer Frau Elvira Quenzelbach") == ["Elvira Quenzelbach"]

    # Negativtest: Sachfrage, KEIN Name -- trotz grossgeschriebenem Substantiv
    # mitten im Satz (Herkunftsschranke ist ein ganz normales deutsches Wort).
    assert eigennamen("wie funktioniert die Herkunftsschranke") == []

    # Grossbuchstabe am Satzanfang macht noch keinen Namen.
    assert eigennamen("Wie geht es Ihnen") == []

    # Anrede ohne folgenden Namen -- kein Ausschlag.
    assert eigennamen("Ich bin Frau") == []
    assert eigennamen("Frau und Herr sind hier keine Namen") == [], "Anrede gefolgt von Stoppwort/Kleinschreibung"

    # Zwei Anreden im selben Satz.
    assert eigennamen("Frau Döldissen und Herr Müller waren da") == ["Döldissen", "Müller"]

    # Umlaut/Umschrift -- das Modul faltet NICHT selbst (das macht die FTS-
    # Anfrage des Aufrufers), es loest nur heraus, was dasteht.
    assert eigennamen("mit Frau Doeldissen") == ["Doeldissen"]

    # Leerfaelle.
    assert eigennamen(None) == []
    assert eigennamen("") == []
    assert eigennamen("   ") == []

    # Realer Pruefkorpus (runs/pruefkorpus.jsonl): keine der 45 Sachfragen
    # traegt eine Anrede -- der Namensweg darf dort niemals ausschlagen,
    # sonst waere das keine gezielte Erweiterung, sondern ein neues Rauschen.
    import json
    korpus = _w / "runs" / "pruefkorpus.jsonl"
    if korpus.exists():
        ausschlaege = 0
        for zeile in korpus.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if not zeile:
                continue
            fall = json.loads(zeile)
            if eigennamen(fall.get("task", "")):
                ausschlaege += 1
        assert ausschlaege == 0, (
            f"{ausschlaege} Faelle im Sach-Pruefkorpus wurden faelschlich als Namensfrage erkannt")

    print("namensfrage: alle Proben bestanden")


if __name__ == "__main__":
    _selftest()
