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


# ─── kanten_nachziehen (Auftrag 81): Kantenberechnung an diesen Haken gehaengt ──

def test_kanten_nachziehen_meldet_wenn_automatischer_lauf_etwas_liefert(capsys, monkeypatch):
    """automatischer_lauf() liegt in kern/kanten_aus_bedeutung.py und ist dort
    getestet -- hier wird nur geprueft, dass der Haken sie aufruft und eine
    Rueckmeldung ausgibt, ohne selbst eine echte DB zu brauchen."""
    import types

    fake = types.SimpleNamespace(automatischer_lauf=lambda db_path: "Kanten nachgezogen: 3 neu, 0 bereits vorhanden (3 Knoten ohne Kante geprueft).")
    monkeypatch.setitem(sys.modules, "kanten_aus_bedeutung", fake)

    an.kanten_nachziehen()
    out = capsys.readouterr().out
    assert "Kanten nachgezogen: 3 neu" in out


def test_kanten_nachziehen_schweigt_wenn_nichts_zu_tun_war(capsys, monkeypatch):
    """Negativfall: liefert automatischer_lauf None (nichts Neues), gibt der
    Haken nichts aus -- kein Rauschen bei jedem Stop."""
    import types

    fake = types.SimpleNamespace(automatischer_lauf=lambda db_path: None)
    monkeypatch.setitem(sys.modules, "kanten_aus_bedeutung", fake)

    an.kanten_nachziehen()
    assert capsys.readouterr().out == ""


def test_kanten_nachziehen_faengt_fehler_ab(capsys, monkeypatch):
    """Ein Fehler in der Kantenberechnung darf den Haken nicht zum Absturz
    bringen -- gleiche Haltung wie bei der Auszug-Pruefung selbst."""
    import types

    def _boom(db_path):
        raise RuntimeError("kaputt")

    fake = types.SimpleNamespace(automatischer_lauf=_boom)
    monkeypatch.setitem(sys.modules, "kanten_aus_bedeutung", fake)

    an.kanten_nachziehen()  # darf nicht werfen
    assert capsys.readouterr().out == ""


# ─── vorschlaege_nachziehen (Auftrag 84): Neuheitsfilter fuer berichte/vorschlag.py ──

def test_vorschlaege_nachziehen_meldet_wenn_melde_etwas_liefert(capsys, monkeypatch):
    """melde() liegt in melder/vorschlagsmelder.py und ist dort getestet --
    hier nur, dass der Haken sie aufruft und die Meldung ausgibt."""
    import types

    fake = types.SimpleNamespace(melde=lambda: "NEU seit dem letzten Lauf: L-testid")
    monkeypatch.setitem(sys.modules, "vorschlagsmelder", fake)

    an.vorschlaege_nachziehen()
    out = capsys.readouterr().out
    assert "NEU seit dem letzten Lauf: L-testid" in out


def test_vorschlaege_nachziehen_schweigt_wenn_nichts_neu_ist(capsys, monkeypatch):
    """Negativfall: melde() liefert einen leeren String (kein neuer
    Kandidat) -- der Haken gibt nichts aus, keine Leermeldung."""
    import types

    fake = types.SimpleNamespace(melde=lambda: "")
    monkeypatch.setitem(sys.modules, "vorschlagsmelder", fake)

    an.vorschlaege_nachziehen()
    assert capsys.readouterr().out == ""


def test_vorschlaege_nachziehen_faengt_fehler_ab(capsys, monkeypatch):
    """Ein Fehler im Vorschlagsmelder darf den Haken nicht zum Absturz
    bringen -- gleiche Haltung wie bei kanten_nachziehen()."""
    import types

    def _boom():
        raise RuntimeError("kaputt")

    fake = types.SimpleNamespace(melde=_boom)
    monkeypatch.setitem(sys.modules, "vorschlagsmelder", fake)

    an.vorschlaege_nachziehen()  # darf nicht werfen
    assert capsys.readouterr().out == ""
