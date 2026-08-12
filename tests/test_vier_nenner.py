"""Der Selbsttest von melder/vier_nenner.py (Aufgabe 62) laeuft im Testlauf
mit -- sonst ist er ein Skript, das niemand aufruft, und verrottet wie jedes
andere. Der Selbsttest selbst traegt die Rot-Probe (konstruierter Fall mit
bekanntem Soll fuer A/B, Gegenprobe gegen den falschen Nenner aus
recall_log.jsonl, Tupel-Fallstrick in nenner_c()). Hier zusaetzlich ein
paar Grenzwert-Assertions auf melden(), damit `pytest -k vier_nenner` auch
ohne den kompletten Selbsttest-Lauf etwas zeigt."""

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "melder"))

import vier_nenner  # noqa: E402


def test_selftest():
    vier_nenner._selftest()


def test_melden_b_ist_keine_fehlerquote_text():
    """B darf im Ausgabetext nicht als Fehler formuliert sein (Auftrag:
    'leer' ist NICHT 'versagt')."""
    with mock.patch.object(vier_nenner, "nenner_a_b", return_value={
            "a_nachrichten": 10, "a_abruf_gelaufen": 8, "b_leer": 3}):
        befund = vier_nenner.melden(mit_c=False)
        assert befund["B"].startswith("3/8")
        assert "versagt" not in befund["B"].lower()
        assert "KEINE Fehlerquote" in befund["B"]  # ausdruecklich verneint, nicht behauptet


def test_melden_b_grenzwert_kein_abruf_gelaufen():
    """Grenzwert: a_abruf_gelaufen == 0 darf B nicht durch 0 teilen lassen."""
    with mock.patch.object(vier_nenner, "nenner_a_b", return_value={
            "a_nachrichten": 4, "a_abruf_gelaufen": 0, "b_leer": 0}):
        befund = vier_nenner.melden(mit_c=False)
        assert befund["B"] == "0/0 -- kein Abruf lief"


def test_nenner_c_tupel_nicht_verwechselt():
    """Rot-Probe fuer den beim ersten Anlauf gefundenen Fehler: ergebnis[g]
    ist ein (treffer_n, gesamt_n)-Tupel, keine Liste von Booleans -- Treffer
    duerfen nie groesser als der Nenner sein."""
    with mock.patch.object(vier_nenner.abrufguete, "lade_korpus",
                            return_value=([{"target_kind": "node"}] * 9, 0)), \
         mock.patch.object(vier_nenner.abrufguete, "messe", return_value={
             "LESSON": (1, 2), "NODE": (2, 7), "MIT_KANTE": (2, 4), "OHNE_KANTE": (1, 5)}), \
         mock.patch("sqlite3.connect"):
        c = vier_nenner.nenner_c()
        assert c["c_ziele_bekannt"] == 9  # 2 + 7, NICHT 4 Gruppen * 2
        assert c["c_getroffen"] == 3      # 1 + 2
        assert c["c_getroffen"] <= c["c_ziele_bekannt"]
