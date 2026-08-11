"""Der Haken zieht nach, wenn der Bestand juenger ist als der Auszug -- und
nur dann. Beide Richtungen, weil ein Haken, der immer laeuft, acht Megabyte
je Sitzung schreibt, und einer, der nie laeuft, still hinterherhinkt.
"""

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import auszug_nachziehen as an  # noqa: E402


def test_noetig_nur_wenn_der_bestand_juenger_ist(tmp_path):
    db = tmp_path / "brainlehr.db"
    auszug = tmp_path / "bestand_2026-08-08.jsonl"

    db.write_text("x")
    assert an.nachziehen_noetig(db, None), "ohne Auszug ist es immer noetig"
    assert an.nachziehen_noetig(db, auszug), "fehlender Auszug zaehlt wie keiner"

    auszug.write_text("y")
    import os
    os.utime(auszug, (db.stat().st_mtime + 10, db.stat().st_mtime + 10))
    assert not an.nachziehen_noetig(db, auszug), "juengerer Auszug: nichts zu tun"

    os.utime(db, (auszug.stat().st_mtime + 10, auszug.stat().st_mtime + 10))
    assert an.nachziehen_noetig(db, auszug), "juengere Datenbank: nachziehen"


def test_ohne_datenbank_passiert_nichts(tmp_path):
    """Negativfall: ein Arbeitsbaum ohne Bestand darf keinen Auszug erzeugen."""
    assert not an.nachziehen_noetig(tmp_path / "gibtsnicht.db", None)


def test_ein_auszug_je_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(an, "AUSZUG_ORDNER", tmp_path)
    assert an.ziel_fuer_heute("2026-08-08").name == "bestand_2026-08-08.jsonl"
    assert an.ziel_fuer_heute("2026-08-08") == an.ziel_fuer_heute("2026-08-08")
