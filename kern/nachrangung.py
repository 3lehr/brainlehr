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
import os
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
    "Antworte mit einem JSON-Objekt: {{\"reihenfolge\": [Nummern absteigend "
    "nach Nuetzlichkeit]}}. Keine Erklaerung."
)


# Erzwungenes Ausgabeformat statt einer Bitte im Prompt.
#
# DER BEFUND (2026-08-20): Der Prompt bittet um "NUR die Nummern, keine
# Erklaerung". Kleine lokale Modelle halten sich daran nicht zuverlaessig, und
# der Parser zog mit re.findall(r"\d+") JEDE Ziffernfolge aus dem Rohtext --
# eine Vorrede wie "Hier sind die Top 5:" schob die 5 an den ANFANG der
# Reihenfolge. Das faellt nirgends auf: Die Funktion liefert weiterhin eine
# gueltige Reihenfolge ueber alle Kandidaten, nur die falsche. Kein Fehler,
# keine Ausnahme -- die Guete sinkt still.
#
# Ollama ab 0.5 nimmt hier ein JSON-Schema entgegen und beschraenkt die
# Dekodierung darauf: Das Modell KANN kein ungueltiges Token mehr waehlen.
# Das ist der Unterschied zwischen einer Bitte und einer Sperre.
#
# WAS ES NICHT LEISTET, und das ist hier besonders wichtig: Ein Schema
# erzwingt die FORM, nie den INHALT. Eine schemakonforme Reihenfolge kann
# fachlich voellig falsch sein und sieht dabei makellos aus -- derselbe
# Vorbehalt wie beim Aehnlichkeitswert, der sagt, ob etwas Passendes vorliegt,
# und nicht, ob es stimmt.
# Der Endpunkt ist einstellbar, weil er es sein MUSS.
#
# GEMESSEN 2026-08-20 auf dem Rechner des Betreibers: Der bisherige
# Vorgabewert zeigte auf Ollama (Port 11434) -- dort lauscht niemand. Was
# laeuft, ist LM Studio auf Port 1234. Der Nachranger fiel damit bei jedem
# Aufruf still auf die urspruengliche Reihenfolge zurueck: kein Fehler, kein
# Log, nur Wirkung null. Ein erzwungenes Ausgabeformat an einem toten
# Endpunkt waeren zwei wirkungslose Dinge uebereinander.
ENDPUNKT = os.environ.get("BRAINLEHR_MODELL_ENDPUNKT",
                          "http://127.0.0.1:11434/api/generate")
MODELLNAME = os.environ.get("BRAINLEHR_MODELL_NAME", "gemma4:e4b")


def _ist_openai(endpunkt: str) -> bool:
    """LM Studio spricht OpenAI-kompatibel, Ollama nicht -- Nutzlast UND
    Antwortform unterscheiden sich.

    Erkannt an der Pfadform, nicht an einer zweiten Einstellung: Zwei
    Schalter, die zusammenpassen muessen, gehen irgendwann auseinander, und
    dann zeigt der eine auf LM Studio, waehrend der andere Ollama-Nutzlast
    schickt."""
    return "/chat/completions" in endpunkt or "/v1/" in endpunkt


def _text_aus(antwort: dict) -> str:
    """Der erzeugte Text, aus beiden Antwortformen. Leerer String statt
    Ausnahme: Der Aufrufer hat fuer jeden Fehlerfall bereits den Rueckfall
    auf die urspruengliche Reihenfolge."""
    if isinstance(antwort.get("response"), str):
        return antwort["response"]
    try:
        nachricht = antwort["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return ""
    # Das Denkfeld NUR, wenn der Inhalt leer bleibt.
    #
    # GEMESSEN 2026-08-20 gegen LM Studio (qwen3.8-27b), und das Ergebnis war
    # das Gegenteil der Erwartung:
    #     ohne Schemazwang, 285 s:  '{"reihenfolge": [2, 0, 1]}'  richtig
    #     mit  Schemazwang,  15 s:  ''                            Rueckfall
    # Der Zwang wirkt -- aber bei einem Reasoning-Modell landet die
    # schemakonforme Ausgabe in `reasoning_content`, waehrend `content` leer
    # bleibt. Wer nur `content` liest, macht aus einer richtigen Antwort einen
    # stillen Rueckfall, und das Format, das die Guete heben sollte, senkt sie.
    #
    # Die Reihenfolge ist der halbe Punkt: Ist beides da, gilt der Inhalt.
    # Denktext ist sonst nicht die Antwort -- wer ihn immer nimmt, liest die
    # Ueberlegung statt des Ergebnisses.
    return (nachricht.get("content") or nachricht.get("reasoning_content") or "")


FORMAT_REIHENFOLGE = {
    "type": "object",
    "properties": {"reihenfolge": {"type": "array", "items": {"type": "integer"}}},
    "required": ["reihenfolge"],
}


def _reihenfolge_aus(roh: str, anzahl: int) -> list[int]:
    """Rohantwort -> Reihenfolge. Herausgeloest, damit sie OHNE laufendes
    Modell pruefbar ist -- vorher stand sie inline in modell() und war nur
    ueber einen echten Ollama-Aufruf erreichbar.

    Zwei Wege mit Absicht: erst JSON (das erzwungene Format), dann die alte
    Zahlensuche. Der Rueckfall bleibt, weil aeltere Ollama-Fassungen und
    andere Endpunkte kein Schema koennen -- ohne ihn waere der Einbau eine
    Verschlechterung fuer alle, die es nicht koennen."""
    kandidaten_zahlen: list[int] = []
    try:
        gelesen = json.loads(roh)
        if isinstance(gelesen, dict) and isinstance(gelesen.get("reihenfolge"), list):
            kandidaten_zahlen = [int(x) for x in gelesen["reihenfolge"]
                                 if isinstance(x, (int, float)) and not isinstance(x, bool)]
    except (ValueError, TypeError):
        pass
    if not kandidaten_zahlen:
        kandidaten_zahlen = [int(z) for z in re.findall(r"\d+", roh or "")]

    gesehen, reihenfolge = set(), []
    for i in kandidaten_zahlen:
        if 0 <= i < anzahl and i not in gesehen:
            gesehen.add(i)
            reihenfolge.append(i)
    # Was das Modell nicht genannt hat, haengt hinten dran -- in der
    # urspruenglichen Reihenfolge. Nie wegwerfen.
    reihenfolge += [i for i in range(anzahl) if i not in gesehen]
    return reihenfolge


def modell(anfrage: str, kandidaten: list[dict], *, modellname: str | None = None,
           zeitgrenze: int = 120, endpunkt: str | None = None) -> list[int]:
    """Reihenfolge ueber ein erzeugendes Modell, EIN Aufruf fuer alle Kandidaten.

    Faellt bei jedem Fehler auf die urspruengliche Reihenfolge zurueck und
    meldet das NICHT als Erfolg: ein Nachranger, der still nichts tut, waere
    von einem wirkungslosen nicht zu unterscheiden. Der Aufrufer sieht es
    daran, dass die Reihenfolge unveraendert ist.
    """
    if not kandidaten:
        return []
    endpunkt = endpunkt or ENDPUNKT
    modellname = modellname or MODELLNAME
    zeilen = []
    for i, k in enumerate(kandidaten):
        text = (str(k.get("title") or "") + " -- " + str(k.get("summary") or ""))[:300]
        zeilen.append(f"{i}: {text}")
    anfrage_text = _VORLAGE.format(frage=anfrage[:600], liste="\n".join(zeilen))
    if _ist_openai(endpunkt):
        last = {"model": modellname, "temperature": 0,
                "messages": [{"role": "user", "content": anfrage_text}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "reihenfolge", "strict": True,
                                                    "schema": FORMAT_REIHENFOLGE}}}
    else:
        last = {"model": modellname, "prompt": anfrage_text, "stream": False,
                "options": {"temperature": 0}, "format": FORMAT_REIHENFOLGE}
    daten = json.dumps(last).encode()
    try:
        req = urllib.request.Request(endpunkt, data=daten,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=zeitgrenze) as antwort:
            roh = _text_aus(json.loads(antwort.read()))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return list(range(len(kandidaten)))

    return _reihenfolge_aus(roh, len(kandidaten))
