"""BDW-E07 gegen den ECHTEN Bestand statt gegen das Modul allein.

DER BEFUND, 2026-08-19. Die Katalogzeile las sich wie eine Testluecke:
"`pytest tests/test_kundenschluessel.py` gruen (7 Faelle) -- Inhalt ohne
Schluessel unlesbar. **Index und Backup noch nicht abgedeckt**: das AC
verlangt alle drei." Das klingt nach zwei von drei erledigt.

Gemessen ist es etwas anderes. `kern/kundenschluessel.py` ist eine
IN-PROZESS-Ablage (zwei dicts, wie ihr eigener Docstring sagt) und wird von
KEINEM Schreibpfad des Bestands benutzt -- `grep` ueber alle *.py ausserhalb
der Arbeitsbaeume findet als Aufrufer nur `kern/aufbewahrung.py` und Tests.
`knowledge_nodes.summary` und `.content` sind schlichte TEXT-Spalten; eine
Spalte fuer Chiffretext gibt es nicht.

Daraus folgt: Nicht zwei von drei Teilen sind belegt, sondern NULL von drei am
echten Gegenstand. Das gruene Modul beweist, dass das Verfahren stimmt -- nicht,
dass der Bestand es benutzt. Genau die Klasse "der Pruefstand ist nicht die
Wirklichkeit", nur diesmal mit einem ISOLIERTEN Modul als Pruefstand.

Diese Datei haelt den Ist-Zustand fest, statt ihn zu behaupten. Sie ist
absichtlich GRUEN: sie misst, was heute gilt. Wird der Bestand eines Tages
verschluesselt, wird sie rot und zeigt genau die Stelle -- ein `xfail` waere
hier falsch, denn nichts davon ist ein Fehlschlag, es ist der Befund.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

# Eine Zeichenfolge, die in keiner Schemadatei und keinem Testfixture sonst
# vorkommt -- sonst faende der Bytefund sie auch ohne unseren Knoten.
GEHEIM = "WEG-Beschluss Klaegerin Meiershofstrasse 12b Aktenzeichen 4711"


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db = tmp_path / "brainlehr_test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    return db


def _sensiblen_fall_anlegen(db: Path) -> None:
    # Der Rueckgabewert wird GEPRUEFT, nicht weggeworfen. Beim ersten Lauf
    # dieser Datei kam `{'error': 'source fehlt: ...'}` zurueck, der Knoten
    # wurde nie geschrieben -- und alle drei Zusicherungen schlugen fehl, was
    # sich wie "der Bestand ist verschluesselt" gelesen haette. Ein
    # ungeprueftes Ergebnis der Vorbereitung faelscht den Befund in die
    # angenehme Richtung.
    r = kms.knowledge_add(
        parent_path="/",
        title="Sensibler Testfall E07",
        summary=GEHEIM,
        content=GEHEIM,
        anlass="skript",
        norm_entscheidung="keine_norm",
        source="erzeugt aus tests/test_e07_bestand_im_klartext.py (BDW-E07)",
    )
    assert "error" not in r, r


def test_e07_daten_stehen_im_klartext_in_der_datei(temp_db):
    """TEIL 1 von 3 -- Daten. Der Klartext steht in den Rohbytes der Datei."""
    _sensiblen_fall_anlegen(temp_db)
    assert GEHEIM.encode() in temp_db.read_bytes(), (
        "Wenn diese Zusicherung faellt, ist der Bestand verschluesselt -- "
        "dann gehoert BDW-E07 neu vermessen, nicht dieser Test angepasst."
    )


def test_e07_der_index_gibt_den_klartext_ohne_schluessel_heraus(temp_db):
    """TEIL 2 von 3 -- Index. Der ist der unangenehmere Teil: selbst wenn die
    Spalte eines Tages Chiffretext traegt, gibt eine Volltextsuche den Klartext
    heraus, solange SIE ihn indiziert. Ein Index ueber verschluesselte Inhalte
    ist der klassische stille Ausweg um die Verschluesselung herum."""
    _sensiblen_fall_anlegen(temp_db)
    conn = sqlite3.connect(str(temp_db))
    treffer = conn.execute(
        "select summary from knowledge_fts where knowledge_fts match ?",
        ("Meiershofstrasse",),
    ).fetchall()
    conn.close()
    assert treffer and GEHEIM in treffer[0][0], treffer


def test_e07_die_sicherung_traegt_denselben_klartext(temp_db):
    """TEIL 3 von 3 -- Backup. Eine Sicherung ist eine Bytekopie; sie erbt
    jede Eigenschaft des Originals, auch diese. Seit 2026-08-19 liegt sie in
    einem eigenen Verzeichnis (BDW-E15) -- das trennt den ORT, nicht die
    Lesbarkeit. Zwei verschiedene Fragen, und E15 beantwortet E07 nicht."""
    _sensiblen_fall_anlegen(temp_db)
    sys.path.insert(0, str(WURZEL / "kern"))
    import sicherungen  # noqa: E402

    ziel = sicherungen.sicherungspfad(temp_db, "20260819T120000")
    shutil.copy2(temp_db, ziel)
    assert ziel.parent != temp_db.parent, "E15: eigener Ordner"
    assert GEHEIM.encode() in ziel.read_bytes(), "E07: trotzdem lesbar"


def test_e07_kein_schreibpfad_des_bestands_nutzt_den_schluesselspeicher():
    """DIE WURZEL, und sie ist der eigentliche Befund: Das Verfahren ist
    gebaut und gruen, aber an nichts angeschlossen. Waechst spaeter ein
    echter Aufrufer, wird dieser Test rot -- und das ist dann die gute
    Nachricht, die jemand sehen soll."""
    import subprocess

    roh = subprocess.run(
        ["grep", "-rln", "--include=*.py", "kundenschluessel", "."],
        cwd=WURZEL, capture_output=True, text=True,
    ).stdout.split()
    aufrufer = [
        p for p in roh
        if ".claude/worktrees" not in p
        and not p.startswith("./tests/")
        and p not in ("./kern/kundenschluessel.py", "./kern/risikoeinstufung.py")
    ]
    assert aufrufer == ["./kern/aufbewahrung.py"], (
        "Aufrufer ausserhalb Tests: %r -- wenn hier ein Schreibpfad des "
        "Bestands auftaucht, ist BDW-E07 neu zu vermessen." % (aufrufer,)
    )


def test_e07_gegenprobe_ohne_knoten_steht_die_zeichenfolge_nirgends(temp_db):
    """NEGATIVFALL. Ohne den Knoten darf die Zeichenfolge weder in der Datei
    noch im Index stehen -- sonst faende der Bytefund oben etwas, das aus
    schema.sql oder einem Fixture stammt, und alle drei Zusicherungen waeren
    wertlos, ohne je rot zu werden."""
    assert GEHEIM.encode() not in temp_db.read_bytes()
    conn = sqlite3.connect(str(temp_db))
    treffer = conn.execute(
        "select count(*) from knowledge_fts where knowledge_fts match ?",
        ("Meiershofstrasse",),
    ).fetchone()[0]
    conn.close()
    assert treffer == 0, treffer


# ─── BDW-E13: derselbe Befund, eine Ebene weiter ────────────────────────────

def test_e13_der_fristlauf_kann_den_bestand_gar_nicht_erreichen():
    """Die E13-Zeile sagt, der Fristlauf "greift auf den Schluesselspeicher,
    nicht auf Indizes, Caches und Kopien". Das klingt nach einem unfertigen
    Lauf. Gemessen ist es eine Frage der Signatur: `fristlauf()` nimmt einen
    `Kundenschluesselspeicher` und eine Zuordnung entgegen -- es gibt keinen
    Parameter, ueber den ihm der Bestand ueberhaupt bekannt werden koennte,
    und `kern/aufbewahrung.py` nennt weder sqlite noch `kern/speicher`.

    Nicht "drei von vier Teilen fehlen" also, sondern: der Lauf ist mit dem
    Gegenstand nicht verbunden. Waechst dieser Weg, wird der Test rot."""
    import inspect

    sys.path.insert(0, str(WURZEL / "kern"))
    import aufbewahrung  # noqa: E402

    quelle = Path(aufbewahrung.__file__).read_text(encoding="utf-8")
    assert "sqlite" not in quelle and "import speicher" not in quelle, (
        "aufbewahrung.py kennt jetzt den Bestand -- BDW-E13 neu vermessen."
    )
    namen = list(inspect.signature(aufbewahrung.fristlauf).parameters)
    assert namen == ["speicher", "ordnung", "zuordnung", "jetzt_ts", "nachweis_pfad"], namen
