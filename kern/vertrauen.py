#!/usr/bin/env python3
"""Der Vertrauensregler -- wie viel der Assistent selbst entscheiden darf.

BETREIBERENTSCHEIDUNG 2026-08-16, woertlich: „das was an mir haengt, lass davon
mehr brainlehr machen, brainlehr braucht mehr vertrauen! dazu koennten wir
einen vertrauensregler einbauen, den der user steuern kann. meistens waren die
blocker bisher keine echten!"

Plan: docs/PLAN_VERTRAUENSREGLER_2026-08-16.md, Knoten a6991a6b.

WAS DER REGLER STEUERT: die Rueckfragepflicht -- wann innegehalten und gefragt
wird, statt zu entscheiden und danach zu berichten.

WAS ER NICHT STEUERT: die Belegpflicht. Rot vor gruen, messen statt vermuten,
Befunde benennen statt glaetten gelten auf JEDER Stufe unveraendert. Wer
schneller handeln darf, prueft sorgfaeltiger.

MERKMAL, KEINE SPERRE -- und das gehoert in jeden Bericht, der ihn erwaehnt:
Der Assistent laeuft als derselbe Benutzer, dem die Reglerdatei gehoert. Er
koennte sie selbst hochsetzen. Dasselbe gilt fuer art=mensch am Ausweis
(L-33d3bd), und dort war genau diese Verwechslung der Befund. Der Regler
DRUECKT DEN WILLEN DES BETREIBERS AUS und macht ihn maschinenlesbar; er
schuetzt nicht gegen einen boeswilligen Assistenten und darf nirgends als
Schutz auftreten.

Tragfaehig wird er durch die Gegenrichtung: Jede Handlung oberhalb der
Vorgabestufe wird MIT IHRER STUFE protokolliert (`vermerke`). Der Regler senkt
die Zahl der Rueckfragen und erhoeht die Nachvollziehbarkeit, nicht umgekehrt.

WARUM EINE KLARTEXTDATEI und keine Tabelle: Sie muss lesbar sein, bevor eine
Datenbank offen ist, und von einem Menschen ohne Werkzeug aenderbar --
`echo raeumen > ~/.brainlehr/vertrauensstufe` und fertig.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Benannt, nicht nummeriert. Eine Skala 0..10 wurde verworfen: niemand kann
# sagen, was 6 erlaubt und 7 nicht, und was sich nicht sagen laesst, wird nach
# Gefuehl gestellt und nach Gefuehl ausgelegt.
STUFEN = ("vorlegen", "handeln", "raeumen")

# Vorgabe ist der Stand seit dem 2026-08-11 (Testumgebungs-Direktive), nicht
# die neue Stufe. Ein Regler, der beim Einbau schon hochgedreht ist, hat nie
# eine Ausgangslage.
VORGABE = "handeln"

DATEI = Path(os.environ.get("BRAINLEHR_VERTRAUEN",
                            Path.home() / ".brainlehr" / "vertrauensstufe"))
PROTOKOLL = DATEI.parent / "vertrauen-protokoll.jsonl"

# Was auf KEINER Stufe ohne Rueckfrage geschieht. Diese vier haengen nicht am
# Vertrauen, sondern an der Reichweite der Folgen -- ein Regler, der sie
# mitregelt, ist kein Vertrauensregler, sondern ein Ausschalter.
IMMER_FRAGEN = (
    "kennwoerter und zugangsdaten",
    "aussenwirkung gegenueber dritten",
    "unumkehrbares ohne rueckweg",
    "geld",
)


def stufe() -> str:
    """Die eingestellte Stufe, sonst die Vorgabe.

    Ein unbekannter Wert faellt auf die Vorgabe zurueck und wird NICHT als
    Fehler geworfen: Ein Tippfehler in der Reglerdatei darf die Arbeit nicht
    anhalten -- aber er darf auch nicht zufaellig hochstufen."""
    try:
        wert = DATEI.read_text(encoding="utf-8").strip().splitlines()[0].strip().lower()
    except (OSError, IndexError):
        return VORGABE
    return wert if wert in STUFEN else VORGABE


def mindestens(verlangt: str) -> bool:
    """Erreicht die eingestellte Stufe mindestens `verlangt`?"""
    if verlangt not in STUFEN:
        raise ValueError(f"unbekannte Stufe: {verlangt!r}, erlaubt: {STUFEN}")
    return STUFEN.index(stufe()) >= STUFEN.index(verlangt)


def darf_raeumen() -> bool:
    """Formale Blocker selbst aufloesen?

    Ein Blocker ist FORMAL, wenn seine Aufloesung keine Frage beantwortet, die
    nur ein Mensch beantworten kann. Rangeinstufung einer bereits getroffenen
    Entscheidung: formal. Ob eine Entscheidung ueberhaupt gilt: nicht formal."""
    return mindestens("raeumen")


def vermerke(handlung: str, *, verlangte_stufe: str, grund: str = "") -> None:
    """Haelt fest, dass oberhalb der Vorgabe gehandelt wurde.

    Das ist die Gegenleistung fuer die Freiheit: weniger Rueckfragen, dafuer
    eine Spur. Auf Vorgabestufe wird NICHT protokolliert -- ein Protokoll, das
    jede gewoehnliche Handlung aufnimmt, ist nach einem Tag unlesbar und wird
    dann von niemandem mehr gelesen."""
    if STUFEN.index(verlangte_stufe) <= STUFEN.index(VORGABE):
        return
    PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
    with PROTOKOLL.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"handlung": handlung, "stufe": stufe(),
                            "verlangt": verlangte_stufe, "grund": grund},
                           ensure_ascii=False) + "\n")


def demo() -> None:
    """Selbsttest ohne Aufbau. Prueft beide Richtungen und die Rueckfaelle."""
    import tempfile
    global DATEI, PROTOKOLL
    merk_d, merk_p = DATEI, PROTOKOLL
    try:
        with tempfile.TemporaryDirectory() as d:
            DATEI = Path(d) / "stufe"
            PROTOKOLL = Path(d) / "protokoll.jsonl"

            # Ohne Datei gilt die Vorgabe -- nicht die hoechste Stufe.
            assert stufe() == VORGABE == "handeln", stufe()
            assert not darf_raeumen(), "ohne Einstellung wird nicht geraeumt"

            DATEI.write_text("raeumen\n", encoding="utf-8")
            assert stufe() == "raeumen" and darf_raeumen()
            assert mindestens("vorlegen") and mindestens("handeln")

            DATEI.write_text("vorlegen", encoding="utf-8")
            assert stufe() == "vorlegen" and not mindestens("handeln")

            # Ein Tippfehler darf weder anhalten noch hochstufen.
            DATEI.write_text("raemen\n", encoding="utf-8")
            assert stufe() == VORGABE, "unbekannter Wert faellt auf die Vorgabe"
            DATEI.write_text("   \n", encoding="utf-8")
            assert stufe() == VORGABE, "leere Datei faellt auf die Vorgabe"

            # Protokoll: nur oberhalb der Vorgabe, und dann vollstaendig.
            DATEI.write_text("raeumen\n", encoding="utf-8")
            vermerke("Rang nachgetragen", verlangte_stufe="raeumen", grund="formal")
            vermerke("Datei gelesen", verlangte_stufe="handeln")
            zeilen = PROTOKOLL.read_text(encoding="utf-8").strip().splitlines()
            assert len(zeilen) == 1, f"nur die geraeumte Handlung gehoert ins Protokoll: {zeilen}"
            eintrag = json.loads(zeilen[0])
            assert eintrag["stufe"] == "raeumen" and eintrag["grund"] == "formal"

            # Die vier Stopp-Punkte stehen ausserhalb des Reglers. Diese Zeile
            # ist kein Test einer Funktion, sondern eine Zusicherung: sie faellt
            # auf, sobald jemand sie in die Stufenlogik hineinzieht.
            assert len(IMMER_FRAGEN) == 4 and "geld" in IMMER_FRAGEN
    finally:
        DATEI, PROTOKOLL = merk_d, merk_p
    print("demo: ok", file=sys.stderr)


if __name__ == "__main__":
    demo()
    print(f"Stufe: {stufe()}   (Datei: {DATEI})")
    print(f"Stopp-Punkte, die IMMER gefragt werden: {', '.join(IMMER_FRAGEN)}")
