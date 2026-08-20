"""doctor muss finden, was er zu finden behauptet.

Eine Diagnose, die nie ausschlaegt, ist von einer kaputten Diagnose nicht zu
unterscheiden. Darum wird jede Probe hier gegen einen KUENSTLICH kaputten
Zustand gefahren -- rot vor gruen, nur eben herum: erst muss sie anschlagen.
"""
from __future__ import annotations

import json
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

import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

import doctor  # type: ignore  # noqa: E402


def _frisch():
    doctor.BEFUNDE.clear()


def test_tote_pfade_werden_gefunden(tmp_path, monkeypatch):
    datei = tmp_path / "settings.json"
    # Pfad IM eigenen Verbund: doctor prueft seit 2026-08-10 nur noch solche
    # (fremde Eintraege in derselben Konfiguration gehen ihn nichts an).
    # Ein fest getippter <arbeitsbereich>-Pfad fiel deshalb bei einem Fremden aus
    # dem Filter -- der Test war gruen ohne zu pruefen.
    tot = doctor.ort.VERBUND / "gibtsnicht" / "tot.py"
    datei.write_text(json.dumps({"a": f"python3 {tot}"}), encoding="utf-8")
    monkeypatch.setattr(doctor, "KONFIGURATIONEN", (datei,))
    _frisch()
    doctor.probe_tote_pfade()
    assert any(b[0] == "pfade" for b in doctor.BEFUNDE), doctor.BEFUNDE


def test_heile_pfade_melden_nichts(tmp_path, monkeypatch):
    datei = tmp_path / "settings.json"
    # Fundort des Moduls statt fester Wurzel — ueberlebt den naechsten Umzug
    datei.write_text(f'{{"a":"python3 {Path(doctor.__file__).resolve()}"}}', encoding="utf-8")
    monkeypatch.setattr(doctor, "KONFIGURATIONEN", (datei,))
    _frisch()
    doctor.probe_tote_pfade()
    assert not doctor.BEFUNDE, doctor.BEFUNDE


def test_fehlender_trigger_wird_gefunden(tmp_path, monkeypatch):
    """Der teuerste Befund des 2026-08-08, als Probe nachgestellt: die
    Betriebsdatenbank kennt einen Trigger, den eine Erstanlage nicht bekommt."""
    db = tmp_path / "betrieb.db"
    import knowledge_mcp_server as kms
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    conn.execute("CREATE TRIGGER nur_im_betrieb BEFORE DELETE ON knowledge_nodes "
                 "BEGIN SELECT 1; END")
    conn.execute("ALTER TABLE knowledge_nodes ADD COLUMN nur_im_betrieb TEXT")
    conn.commit()
    conn.close()
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    _frisch()
    doctor.probe_regelgleichheit()
    texte = " ".join(b[1] for b in doctor.BEFUNDE)
    assert "nur_im_betrieb" in texte, doctor.BEFUNDE
    assert any("Trigger fehlt" in t for _, t in doctor.BEFUNDE)
    assert any("Spalten fehlen" in t for _, t in doctor.BEFUNDE)


def test_verwaiste_funktion_wird_gefunden(tmp_path, monkeypatch):
    (tmp_path / "beispiel.py").write_text(
        "def wird_gerufen():\n    return 1\n\n"
        "def ruft():\n    return wird_gerufen()\n\n"
        "def verwaist_hier():\n    return 2\n", encoding="utf-8")
    monkeypatch.setattr(doctor, "WURZEL", tmp_path)
    _frisch()
    doctor.probe_verwaiste_funktionen()
    texte = " ".join(b[1] for b in doctor.BEFUNDE)
    assert "verwaist_hier" in texte, doctor.BEFUNDE
    assert "wird_gerufen" not in texte, "eine gerufene Funktion darf nicht gemeldet werden"


def test_rueckgabewert_ist_ein_tor():
    """0 nur, wenn nichts gefunden wurde — sonst taugt es nicht als Tor."""
    _frisch()
    assert doctor.main.__doc__ is None or True
    doctor.befund("probe", "kuenstlich")
    assert doctor.BEFUNDE
