"""Die Probe-Instanz muss vom Bestand getrennt bleiben -- nachweislich.

ANLASS (Betreiberfrage 2026-08-11): "warum testest du nicht auf einer zweiten
instanz? waere auch ungefaehrlicher". Bis dahin lief jede Probe gegen dieselbe
Datenbank, mit der auch gearbeitet wird; dass nichts passierte, war Sorgfalt,
nicht Bauart.

Geprueft wird die TRENNUNG, nicht die Einrichtung: dass ein Schreibvorgang mit
gesetztem BEGOD_KNOWLEDGE_DB in der einen Datenbank landet und in der anderen
nichts veraendert. Ohne diesen Nachweis waere "wir testen auf einer zweiten
Instanz" genau die Sorte Behauptung, die diese Suite sonst nicht durchgehen
laesst.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent


def _leere_db(pfad: Path) -> None:
    conn = sqlite3.connect(str(pfad))
    try:
        conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def _knoten(pfad: Path) -> int:
    conn = sqlite3.connect(str(pfad))
    try:
        return conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    finally:
        conn.close()


def test_umgebungsvariable_lenkt_den_schreibvorgang(tmp_path):
    """Der Kern: BEGOD_KNOWLEDGE_DB entscheidet, wohin geschrieben wird.

    Als eigener Prozess, nicht per monkeypatch -- die Variable wird beim IMPORT
    ausgewertet (DB_PATH ist ein Modul-Attribut). Ein Test im laufenden
    Interpreter wuerde das ueberspringen und damit nicht den Weg pruefen, den
    der Klient nimmt."""
    ziel, daneben = tmp_path / "ziel.db", tmp_path / "daneben.db"
    _leere_db(ziel)
    _leere_db(daneben)

    lauf = subprocess.run(
        [sys.executable, "-c",
         "import knowledge_mcp_server as k;"
         "print(k.knowledge_add(parent_path='/', title='Probe', summary='x.',"
         " source='test_probeinstanz.py', norm_entscheidung='keine_norm',"
         " norm_entschieden_grund='Probe.').get('id',''))"],
        capture_output=True, text=True, timeout=120, cwd=str(_w),
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
             "BEGOD_KNOWLEDGE_DB": str(ziel),
             "BRAINLEHR_AUSWEISE": str(tmp_path / "ausweise.json")},
    )
    assert lauf.returncode == 0, lauf.stderr[-600:]
    assert _knoten(ziel) == 1, "nichts in der Ziel-Datenbank"
    assert _knoten(daneben) == 0, "die andere Datenbank wurde beruehrt"


def test_einrichtung_nimmt_keine_kopie_des_bestands(tmp_path, monkeypatch):
    """Die Probe entsteht aus schema.sql, nicht als Kopie.

    Eine Kopie braechte echte Inhalte in eine Umgebung, in der absichtlich
    Kaputtes probiert wird -- und verwischt die Trennung, fuer die sie da ist."""
    sys.path.insert(0, str(_w / "pflege"))
    import probeinstanz  # noqa: E402

    heimat = tmp_path / "probe"
    konfig = tmp_path / ".claude.json"
    konfig.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    monkeypatch.setattr(probeinstanz, "HEIMAT", heimat)
    monkeypatch.setattr(probeinstanz, "KONFIG", konfig)

    erg = probeinstanz.einrichten()
    assert erg["frisch"] is True
    assert _knoten(Path(erg["db"])) == 0, "die Probe startet nicht leer"

    konf = json.loads(konfig.read_text(encoding="utf-8"))
    env = konf["mcpServers"]["knowledge-probe"]["env"]
    assert env["BEGOD_KNOWLEDGE_DB"] == erg["db"]
    assert "BRAINLEHR_GEHEIMNIS" not in env, \
        "das echte Geheimnis hat in einer Wegwerf-Umgebung nichts verloren"
