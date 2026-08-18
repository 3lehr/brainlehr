"""Nachrangung: umordnen, was die Fusion geliefert hat.

Gemessen 2026-08-18 ueber den Produktivweg: top5 17,1 %, top50 57,1 %. In
40 Prozentpunkten der Faelle liegt das Ziel also bereits in der Liste, nur zu
weit hinten. Genau dort setzt eine Nachrangung an -- sie holt nichts Neues,
sie ordnet um.

ZWEI VERFAHREN, absichtlich beide:

`regel()` braucht kein Modell. Sie bewertet die Deckung zwischen den Woertern
der Anfrage und denen des Kandidaten und zieht kurze, allgemeine Eintraege
leicht ab. Sie ist die NULLLINIE: bringt sie dasselbe wie ein Modell, ist das
Modell ueberfluessig -- und diese Frage muss VOR dem Modell beantwortet sein,
sonst wird die Abhaengigkeit nie wieder los.

`modell()` gibt Anfrage UND Kandidat gemeinsam an ein erzeugendes Modell. Das
ist die Eigenschaft, auf die es ankommt (gemeinsame Bewertung statt zweier
getrennter Vektoren), nicht die Modellgattung.

Beide liefern eine REIHENFOLGE, nie eine Auswahl. Wer beim Umordnen etwas
wegwirft, kann hinterher nicht mehr messen, was er verloren hat.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

_WORT = re.compile(r"[\wäöüÄÖÜß]{3,}", re.UNICODE)

# Woerter, die in fast jeder Anfrage stehen und deshalb nichts unterscheiden.
# Bewusst kurz gehalten: eine lange Liste ist eine zweite, ungepruefte
# Sprachannahme.
_HAEUFIG = {
    "der", "die", "das", "und", "oder", "nicht", "eine", "einen", "einem",
    "wie", "was", "wer", "wann", "warum", "wird", "werden", "ist", "sind",
    "the", "and", "for", "with", "that", "this", "from", "was", "were",
}


def _woerter(text: str) -> set[str]:
    return {w.lower() for w in _WORT.findall(text or "")} - _HAEUFIG


def regel(anfrage: str, kandidaten: list[dict]) -> list[int]:
    """Reihenfolge ohne Modell. Rueckgabe sind INDIZES in `kandidaten`.

    Bewertung: Anteil der Anfragewoerter, die im Kandidatentext vorkommen.
    Gleichstand behaelt die urspruengliche Reihenfolge (stabile Sortierung) --
    die Fusion hat schon etwas gewusst, und ohne Grund wird das nicht verworfen.
    """
    frage = _woerter(anfrage)
    if not frage:
        return list(range(len(kandidaten)))

    def deckung(k: dict) -> float:
        text = " ".join(str(k.get(f) or "") for f in ("title", "summary", "path"))
        treffer = frage & _woerter(text)
        return len(treffer) / len(frage)

    return sorted(range(len(kandidaten)), key=lambda i: -deckung(kandidaten[i]))


_VORLAGE = (
    "Du bewertest, wie gut ein Eintrag eine Frage beantwortet.\n"
    "Frage: {frage}\n\n"
    "Eintraege:\n{liste}\n\n"
    "Antworte NUR mit den Nummern der Eintraege, absteigend nach Nuetzlichkeit, "
    "durch Komma getrennt. Keine Erklaerung, keine weiteren Zeichen."
)


def modell(anfrage: str, kandidaten: list[dict], *, modellname: str = "gemma4:e4b",
           zeitgrenze: int = 120, endpunkt: str = "http://127.0.0.1:11434/api/generate") -> list[int]:
    """Reihenfolge ueber ein erzeugendes Modell, EIN Aufruf fuer alle Kandidaten.

    Faellt bei jedem Fehler auf die urspruengliche Reihenfolge zurueck und
    meldet das NICHT als Erfolg: ein Nachranger, der still nichts tut, waere
    von einem wirkungslosen nicht zu unterscheiden. Der Aufrufer sieht es
    daran, dass die Reihenfolge unveraendert ist.
    """
    if not kandidaten:
        return []
    zeilen = []
    for i, k in enumerate(kandidaten):
        text = (str(k.get("title") or "") + " -- " + str(k.get("summary") or ""))[:300]
        zeilen.append(f"{i}: {text}")
    anfrage_text = _VORLAGE.format(frage=anfrage[:600], liste="\n".join(zeilen))
    daten = json.dumps({"model": modellname, "prompt": anfrage_text,
                        "stream": False, "options": {"temperature": 0}}).encode()
    try:
        req = urllib.request.Request(endpunkt, data=daten,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=zeitgrenze) as antwort:
            roh = json.loads(antwort.read()).get("response", "")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return list(range(len(kandidaten)))

    gesehen, reihenfolge = set(), []
    for zahl in re.findall(r"\d+", roh):
        i = int(zahl)
        if 0 <= i < len(kandidaten) and i not in gesehen:
            gesehen.add(i)
            reihenfolge.append(i)
    # Was das Modell nicht genannt hat, haengt hinten dran -- in der
    # urspruenglichen Reihenfolge. Nie wegwerfen.
    reihenfolge += [i for i in range(len(kandidaten)) if i not in gesehen]
    return reihenfolge
