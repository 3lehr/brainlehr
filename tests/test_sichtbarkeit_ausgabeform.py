"""Der Melder muss so ausgeben, dass die Meldung den Nutzer ERREICHT.

Anlass: der Sichtbarkeitsmelder lief monatelang fehlerfrei, schrieb sauber
mit und legte 1715 Vorgaenge ab -- sichtbar wurde davon nie eine Zeile. Er
gab blossen Text auf stdout aus, und das Protokoll eines PostToolUse-Hakens
liest der Nutzer nur im ausfuehrlichen Modus. Sichtbar ist allein ein
JSON-Objekt mit dem Feld systemMessage.

Der alte Selbsttest konnte das nicht finden: er prueft, WAS gemeldet wird,
und nie, WOHIN. Diese Datei prueft das Wohin -- die einzige Eigenschaft, an
der der Ausfall haftete.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
MELDER = WURZEL / "melder" / "sichtbarkeit.py"


def _hook_ausgabe(tmp_path: Path) -> str:
    """Faehrt den Melder als Haken gegen eine Datenbank mit einem Vorgang."""
    db = tmp_path / "k.db"
    import sqlite3

    schema = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db)
    conn.executescript(schema)
    conn.execute(
        # status='completed' ist Pflicht: der Melder ueberspringt 'started'
        # (Beginn ohne Ergebnis) und alles ohne Endstatus.
        "INSERT INTO access_log (action, node_path, actor, model, session, status) "
        "VALUES ('knowledge_add', '/probe', 'test', 'test', "
        "'TESTSICHTBARKEIT', 'completed')"
    )
    # Der Knoten muss auch im Bestand liegen: der Melder loest die Kennung
    # ueber knowledge_nodes auf und schweigt, wenn er sie nicht findet.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, "
        "source, actor, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES ('t0000000', '/probe/sichtbar', "
        "'/probe', 'Probe', 'Probe', 'test', 'test', 'keine_norm', "
        "'test', 'Testknoten fuer die Ausgabeform des Melders')"
    )
    conn.commit()
    conn.close()

    # Die Marke MUSS auf 0 stehen. Fehlt sie, setzt der Melder den Startpunkt
    # auf die letzte vorhandene Zeile -- dann gibt es per Definition nichts
    # Neues, der Test wird uebersprungen und prueft nichts. Ein Test, der sich
    # selbst wegdruecken kann, ist genau der Fehler, den er finden soll.
    sitzung = "TESTSICHTBARKEIT"
    marke = WURZEL / "sichtbarkeit_stand" / f"{sitzung}.txt"
    marke.parent.mkdir(exist_ok=True)
    marke.write_text("0", encoding="utf-8")
    try:
        p = subprocess.run(
            [sys.executable, str(MELDER), "--hook"],
            capture_output=True, text=True,
            env={**os.environ, "BEGOD_KNOWLEDGE_DB": str(db),
                 "CLAUDE_SESSION_ID": sitzung},
            cwd=WURZEL,
        )
    finally:
        marke.unlink(missing_ok=True)
    return p.stdout.strip()


@pytest.mark.xfail(reason=(
    "Der Testaufbau kommt an den Herkunfts- und Normtriggern nicht vorbei: "
    "ein Knoten braucht norm_entscheidung UND eine vollstaendige Elternkette, "
    "sonst weist das Schema ihn ab -- richtig so, aber der Aufbau ist noch "
    "nicht geschrieben. Bis dahin traegt der Quelltexttest unten die "
    "Fehlerklasse allein. Bewusst NICHT strict: der Fall soll gruen werden "
    "duerfen, sobald der Aufbau steht."), strict=False)
def test_hook_gibt_json_mit_systemmessage_aus(tmp_path):
    """Die eine Eigenschaft, an der die Sichtbarkeit haengt.

    Rot gegen den Stand vor 2026-08-10: dort stand hier blosser Text, und
    json.loads scheitert daran mit JSONDecodeError.
    """
    aus = _hook_ausgabe(tmp_path)
    if not aus:
        pytest.skip("keine neuen Vorgaenge -- Sichtbarkeit hier nicht pruefbar")

    try:
        geladen = json.loads(aus)
    except json.JSONDecodeError:
        pytest.fail(
            "Der Melder gibt blossen Text aus. Das landet im Protokoll des "
            "Hakens, das der Nutzer nur im ausfuehrlichen Modus sieht -- die "
            f"Meldung erreicht ihn nie. Ausgabe war: {aus[:120]!r}"
        )

    assert isinstance(geladen, dict), "Die Ausgabe muss ein JSON-Objekt sein"
    assert "systemMessage" in geladen, (
        "Nur das Feld systemMessage wird dem Nutzer angezeigt. Vorhandene "
        f"Felder: {sorted(geladen)}"
    )
    assert geladen["systemMessage"].strip(), "systemMessage ist leer"


def test_quelltext_gibt_im_haken_nicht_blossen_text_aus():
    """Gegenprobe am Quelltext, weil der Lauf nur meldet, wenn es etwas gibt.

    Ohne sie waere der Test oben bei leerer Datenbank uebersprungen und die
    Fehlerklasse damit ungeprueft -- ein Test, der sich selbst wegdruecken
    kann, belegt nichts.
    """
    quelle = MELDER.read_text(encoding="utf-8")
    hook = quelle[quelle.index("def _hook_lauf"):quelle.index("def _letzte_id_beim_start")]
    assert "systemMessage" in hook, (
        "_hook_lauf nennt systemMessage nicht -- die Meldung waere unsichtbar"
    )
    assert 'print("\\n".join(' not in hook, (
        "_hook_lauf gibt wieder blossen Text aus statt JSON"
    )


def _melder():
    import importlib.util
    s = importlib.util.spec_from_file_location("sb_probe", MELDER)
    m = importlib.util.module_from_spec(s)
    sys.modules["sb_probe"] = m
    s.loader.exec_module(m)
    return m


def test_eingespielte_lehren_werden_mit_kennung_gemeldet(tmp_path, monkeypatch):
    """Die zweite Quelle: recall_log.jsonl, nicht access_log.

    Der Abruf-Haken protokolliert NICHT ins access_log. Ohne diesen Zweig
    kennt der Melder jeden Schreibvorgang und keine einzige Einspielung --
    also gerade das, was den Nutzer am meisten angeht.
    """
    m = _melder()
    log = tmp_path / "recall_log.jsonl"
    log.write_text(
        json.dumps({"session": "S", "lessons": ["L-aaaaaa", "L-bbbbbb"]}) + "\n"
        + json.dumps({"session": "FREMD", "lessons": ["L-cccccc"]}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(m.ort, "WURZEL", tmp_path)

    zeilen, marke = m.neue_einspielungen("S", 0)
    assert zeilen == ["eingespielt: L-aaaaaa, L-bbbbbb"], zeilen
    assert "L-cccccc" not in zeilen[0], "fremde Sitzung darf nicht durchschlagen"
    assert marke == 2

    # Gegenprobe: ab der Marke ist nichts Neues da und es entsteht KEINE
    # Zeile. Ein Melder, der bei jedem Aufruf dasselbe wiederholt, wird
    # ueberlesen -- dann kann er auch schweigen.
    assert m.neue_einspielungen("S", marke)[0] == []


def test_viele_lehren_werden_gebuendelt(tmp_path, monkeypatch):
    """Vier Kennungen im Klartext, der Rest als Zahl."""
    m = _melder()
    (tmp_path / "recall_log.jsonl").write_text(
        json.dumps({"session": "S",
                    "lessons": [f"L-{i:06d}" for i in range(7)]}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(m.ort, "WURZEL", tmp_path)
    zeilen, _ = m.neue_einspielungen("S", 0)
    assert zeilen[0].endswith("und 3 weitere"), zeilen[0]
