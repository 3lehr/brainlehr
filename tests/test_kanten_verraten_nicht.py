"""Eine Kante darf keinen Knoten verraten, den man nicht sehen darf.

DER BEFUND (2026-08-20, ausgeloest durch eine Betreiberfrage): Ein gesperrter
Knoten wird in knowledge_search und in children_count sorgfaeltig
unterdrueckt -- "damit ein gesperrter Knoten weder auftaucht noch in
children_count" (knowledge_mcp_server.py:2017). Auch die ZAEHLUNG, denn
"3 Treffer, davon 1 gesperrt" waere selbst die Information.

knowledge_relation_list prueft davon NICHTS. Gemessen: die Woerter gesperrt,
freigabe, ausweis und rolle kommen in der ganzen Funktion nicht vor. Und sie
liefert per JOIN die TITEL beider Enden mit (source_title, target_title) --
ein unsichtbarer Knoten erscheint also ueber eine Kante zu einem sichtbaren
Nachbarn, mit Namen.

Dieselbe Klasse, die ADR-031 beim Volltextindex beschreibt: der stille Weg um
jede Sperre herum. Dort war es der Index, hier die Kantenliste.

WARUM DAS HEUTE FOLGENLOS IST und trotzdem behoben gehoert: Im Bestand steht
`gesperrt` bei 0 von 5 232. Die Luecke waere der erste Fehler, sobald die
Kreis-Achse aus B3b kommt -- und dann faellt sie niemandem auf, weil die
sichtbare Haelfte der Sperre funktioniert.

Anlass war die Betreiberfrage nach einem Eintrag, den ein Hausmeister von
Anfang an nicht sehen kann: "kann dieser nicht messen?!" -- richtig, ueber
Trefferzahlen nicht. Ueber eine Kante schon.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent),
                str(Path(__file__).resolve().parent.parent / "kern"),
                str(Path(__file__).resolve().parent.parent / "haken")]


def _bestand(tmp_path, monkeypatch):
    """Zwei Knoten, einer gesperrt, mit einer Kante dazwischen."""
    import knowledge_mcp_server as kms
    db = tmp_path / "probe.db"
    monkeypatch.setattr(kms, "DB_PATH", db, raising=False)
    # Partitions set BRAINLEHR_DB.  Set both supported names so this isolated
    # fixture, rather than the partition database, remains the server source.
    monkeypatch.setenv("BRAINLEHR_DB", str(db))
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    # The server imports haken.ort once.  A partition may have loaded it with
    # its own DB already, so invalidate that location cache before reload.
    sys.modules.pop("haken.ort", None)
    sys.modules.pop("ort", None)
    import sqlite3
    c = sqlite3.connect(db)
    c.executescript((Path(__file__).resolve().parent.parent / "schema.sql").read_text())
    # Elternknoten zuerst -- der Trigger verlangt ihn, und das ist richtig so.
    c.execute("""insert into knowledge_nodes
                 (id, path, parent_path, title, summary, source, freigabe,
                  norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
                  norm_entschieden_grund, created_at, updated_at)
                 values ('wurzel','/x',NULL,'Wurzel','s','Probe','intern',
                         'keine_norm','probe',datetime('now'),'Probe',
                         datetime('now'),datetime('now'))""")
    for pfad, frei in (("/x/offen", "intern"), ("/x/geheim", "gesperrt")):
        c.execute("""insert into knowledge_nodes
                     (id, path, parent_path, title, summary, source, freigabe,
                      norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
                      norm_entschieden_grund, created_at, updated_at)
                     values (?,?,?,?,?,?,?,'keine_norm','probe',datetime('now'),
                             'Probe',datetime('now'),datetime('now'))""",
                  (pfad[-6:], pfad, "/x", f"Titel {pfad}", "s", "Probe", frei))
    c.execute("""insert into knowledge_relations (source_path, target_path, relation_type, created_at)
                 values ('/x/offen','/x/geheim','betrifft',datetime('now'))""")
    c.commit(); c.close()
    return db


def test_kante_verraet_gesperrten_knoten_nicht(tmp_path, monkeypatch):
    """DIE PROBE: Wer die Kanten des SICHTBAREN Knotens abfragt, darf den
    gesperrten Nachbarn weder als Pfad noch als Titel bekommen."""
    _bestand(tmp_path, monkeypatch)
    import importlib, knowledge_mcp_server as kms
    importlib.reload(kms)
    aus = kms.knowledge_relation_list(node="/x/offen")
    text = str(aus)
    assert "/x/geheim" not in text, "der gesperrte Pfad steht in der Kantenliste"
    assert "Titel /x/geheim" not in text, "der gesperrte TITEL steht in der Kantenliste"


def test_kante_zwischen_sichtbaren_bleibt_sichtbar(tmp_path, monkeypatch):
    """NEGATIVFALL: Die Sperre darf nicht alles wegfiltern -- sonst waere die
    Kantenliste fuer den Normalfall kaputt, und das faellt erst spaeter auf."""
    db = _bestand(tmp_path, monkeypatch)
    import sqlite3, importlib, knowledge_mcp_server as kms
    c = sqlite3.connect(db)
    c.execute("""insert into knowledge_nodes
                 (id, path, parent_path, title, summary, source, freigabe,
                  norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
                  norm_entschieden_grund, created_at, updated_at)
                 values ('zwei2','/x/zwei','/x','Titel zwei','s','Probe','intern',
                         'keine_norm','probe',datetime('now'),'Probe',
                         datetime('now'),datetime('now'))""")
    c.execute("""insert into knowledge_relations (source_path, target_path, relation_type, created_at)
                 values ('/x/offen','/x/zwei','betrifft',datetime('now'))""")
    c.commit(); c.close()
    importlib.reload(kms)
    aus = str(kms.knowledge_relation_list(node="/x/offen"))
    assert "/x/zwei" in aus, "sichtbare Kanten muessen sichtbar bleiben"
