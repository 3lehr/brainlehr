#!/usr/bin/env python3
"""Jeder Name, der als Datenbank-Uebersteuerung ANGEKUENDIGT wird, muss vom
Produktivweg auch GELESEN werden.

ANLASS, 2026-08-18, und der Schaden war real. Ein Messlauf gegen
LongMemEval setzte `BRAINLEHR_DB` auf eine Testdatenbank -- der Name, den
`kern/speicher.py` in seinem eigenen Fehlertext als Pfad-Uebersteuerung
nennt ("Pfad pruefen (BRAINLEHR_DB / BEGOD_KNOWLEDGE_DB)"). Gelesen wird in
`knowledge_mcp_server.py` aber ausschliesslich `BEGOD_KNOWLEDGE_DB`. Folge:
48 Testknoten samt Einbettungen landeten unbemerkt in der PRODUKTIVEN
brainlehr.db. Sie wurden bemerkt, gesichert und entfernt -- aber nur, weil
der Agent seinen eigenen Lauf nachgezaehlt hat.

DIE FEHLERKLASSE: nicht "falscher Name", sondern "angekuendigt und
wirkungslos". Wer die Uebersteuerung setzt, bekommt keinen Fehler, keine
Warnung und kein leeres Ergebnis -- er bekommt die ECHTE Datenbank und
merkt es nicht. Ein Schalter, der stillschweigend nichts tut, ist
gefaehrlicher als ein fehlender: beim fehlenden sucht man weiter.

Verwandt mit L-c72944 (beschlossene Schalterstellung war nicht in Kraft,
der Kommentar behauptete sie weiter) -- dort war es eine ADR, hier ein
Fehlertext. Beide Male hat der TEXT etwas versprochen, was der CODE nicht
hielt, und beide Male hat es niemand gemerkt, weil nichts es prueft.

Dieser Test ist die Pruefung. Er liest, welche Namen als Uebersteuerung
angekuendigt sind, und haelt sie gegen die, die tatsaechlich abgefragt
werden.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent

# Wo eine Uebersteuerung ANGEKUENDIGT wird: Fehlertexte und Modulkoepfe.
ANKUENDIGUNG = re.compile(r"\b([A-Z][A-Z0-9_]{4,})_DB\b")
# Wo sie GELESEN wird: os.environ.get("X") / os.getenv("X").
LESUNG = re.compile(r"(?:environ(?:\.get)?\(|getenv\()\s*[\"']([A-Z][A-Z0-9_]*)[\"']")

# Der Weg, ueber den geschrieben wird -- hier MUSS jeder angekuendigte Name
# ankommen. Die Liste ist bewusst kurz: sie nennt die Stellen, die eine
# Produktivdatenbank oeffnen koennen.
SCHREIBWEGE = ["knowledge_mcp_server.py", "kern/speicher.py"]


def _text(rel: str) -> str:
    p = WURZEL / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def angekuendigte_namen() -> set[str]:
    namen: set[str] = set()
    for rel in SCHREIBWEGE:
        for treffer in ANKUENDIGUNG.finditer(_text(rel)):
            namen.add(treffer.group(0))
    return namen


def gelesene_namen() -> set[str]:
    namen: set[str] = set()
    for rel in SCHREIBWEGE:
        for treffer in LESUNG.finditer(_text(rel)):
            if treffer.group(1).endswith("_DB"):
                namen.add(treffer.group(1))
    return namen


@pytest.mark.xfail(strict=True, reason=(
    "Offener Defekt, 2026-08-18: haken/ort.py meldet aktiv 'BEGOD_KNOWLEDGE_DB "
    "ist veraltet, bitte BRAINLEHR_DB setzen' -- knowledge_mcp_server.py liest "
    "aber nur BEGOD_KNOWLEDGE_DB. Wer der eigenen Empfehlung folgt, schreibt in "
    "die Produktivdatenbank. Behebung gehoert in knowledge_mcp_server.py, die "
    "eine andere Sitzung haelt; ihr gemeldet. strict=True, damit dieser Test "
    "MELDET, sobald es behoben ist, statt still gruen zu werden."))
def test_jede_angekuendigte_uebersteuerung_wird_auch_gelesen():
    """Rot am 2026-08-18: BRAINLEHR_DB wird als massgeblicher Name empfohlen
    und vom Hauptschreibweg nie gelesen."""
    angekuendigt = angekuendigte_namen()
    gelesen = gelesene_namen()
    tot = angekuendigt - gelesen
    assert not tot, (
        f"Angekuendigt, aber von keinem Schreibweg gelesen: {sorted(tot)}.\n"
        f"Gelesen wird: {sorted(gelesen)}.\n"
        "Wer eine dieser Variablen setzt, schreibt in die ECHTE Datenbank und "
        "bekommt keinen Hinweis darauf. Am 2026-08-18 sind so 48 Testknoten in "
        "die produktive brainlehr.db gelaufen.\n"
        "Behebung: entweder den Namen im ankuendigenden Text streichen, oder "
        "ihn im Schreibweg mitlesen. Beides ist richtig -- schweigen ist es nicht."
    )


def test_pruefung_findet_ueberhaupt_etwas():
    """Positivkontrolle. Ohne sie koennte der Test gruen sein, weil die
    Regulaerausdruecke nichts finden -- gruen aus dem falschen Grund ist
    hier besonders billig zu haben, weil beide Mengen dann leer sind."""
    assert gelesene_namen(), "kein einziger DB-Name gelesen -- der Ausdruck greift nicht"
    assert angekuendigte_namen(), "kein einziger DB-Name angekuendigt -- der Ausdruck greift nicht"


def test_erkennt_einen_nachgestellten_bruch(tmp_path, monkeypatch):
    """Gegenprobe in die andere Richtung: ein kuenstlich eingefuegter,
    nirgends gelesener Name MUSS auffallen. Sonst prueft der Test nur den
    heutigen Zustand und nicht die Regel."""
    global WURZEL
    (tmp_path / "kern").mkdir()
    (tmp_path / "knowledge_mcp_server.py").write_text(
        'DB = os.environ.get("BEGOD_KNOWLEDGE_DB")\n', encoding="utf-8")
    (tmp_path / "kern" / "speicher.py").write_text(
        '"""Pfad pruefen (ERFUNDEN_DB / BEGOD_KNOWLEDGE_DB)."""\n', encoding="utf-8")
    monkeypatch.setattr(f"{__name__}.WURZEL", tmp_path)
    assert "ERFUNDEN_DB" in angekuendigte_namen() - gelesene_namen()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
