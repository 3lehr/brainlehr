"""Auftrag C (docs/PLAN_BETRIEBSPROFILE_2026-08-20.md): Erststart im Chat.

Abnahme fuer BDW-P11 (Einrichtungsassistent) und BDW-P12 (Fremdimporte
erfinden keine Herkunft), docs/REQUIREMENTS_BRAINLEHR.md Zeilen 119/120.

BEIDE Ausgangszustaende sind Pflicht -- leer UND gewachsen. Der gewachsene
ist der, den der Betrieb hat; auf ihm darf der Assistent NICHT von selbst
anspringen und nichts ueberschreiben. Zu jedem Positivfall steht der
Negativfall daneben: ein Durchlauf, der nie etwas aendert, waere in Test 4
genauso gruen wie einer, der richtig schweigt -- deshalb Test 5.

Rot-Probe gegen b55ecf16: kern/einrichtung.py existiert dort nicht, alle
Faelle scheitern am Import (ModuleNotFoundError). Das ist die Rot-Ausgabe,
die im Ergebnisprotokoll steht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

import json  # noqa: E402
import sqlite3  # noqa: E402

import pytest  # noqa: E402

import einrichtung  # type: ignore  # noqa: E402
import fremdimport  # type: ignore  # noqa: E402
import gattung_filter  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import speicher  # type: ignore  # noqa: E402

# Pflichtfelder eines Knotens, die Trigger erzwingen (wie in
# tests/test_achsen_b1.py) -- ohne sie scheitert jeder INSERT aus einem
# Grund, der mit diesem Auftrag nichts zu tun hat.
_BESTANDSKNOTEN = (
    "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, summary, "
    "source, updated_at, norm_entscheidung, norm_entschieden_von, "
    "norm_entschieden_grund) VALUES (?, ?, NULL, 0, ?, ?, 'Testvorrichtung', "
    "'jetzt', 'keine_norm', 'skript:test', 'Testvorrichtung')"
)


def _frische_db(tmp_path, monkeypatch, name="frisch.db"):
    db = tmp_path / name
    # Ohne diesen Griff sichert schema_nachzug beim ersten ALTER die ECHTE
    # Betriebsdatenbank weg (siehe tests/test_achsen_b1.py).
    monkeypatch.setattr(kms, "DB_PATH", db)
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def leer(tmp_path, monkeypatch):
    """Ausgangszustand 1: frisch angelegt, kein einziger Knoten."""
    return _frische_db(tmp_path, monkeypatch, "leer.db")


@pytest.fixture
def gewachsen(tmp_path, monkeypatch):
    """Ausgangszustand 2: derselbe Aufbau, aber mit Bestand -- der Zustand,
    den der Betrieb hat und den ein Labor sonst nie faehrt."""
    db = _frische_db(tmp_path, monkeypatch, "gewachsen.db")
    with speicher.schreiben(db) as conn:
        for i in range(3):
            conn.execute(_BESTANDSKNOTEN, (f"alt{i}", f"/alt{i}",
                                           f"Bestandsknoten {i}", "gewachsen"))
    return db


# --- BDW-P11-AC1: der Assistent springt an, aber nur beim leeren Bestand ---

def test_leerer_bestand_laesst_den_assistenten_anspringen(leer):
    lage = einrichtung.lage(leer)
    assert lage["bestand_leer"] is True
    assert lage["springt_an"] is True, "auf leerem Bestand muss die Einrichtung anspringen"
    assert lage["eingerichtet"] is False


def test_gewachsener_bestand_laesst_ihn_NICHT_anspringen(gewachsen):
    """Negativfall zum Test darueber -- ohne ihn belegt 'springt an' nichts."""
    lage = einrichtung.lage(gewachsen)
    assert lage["bestand_leer"] is False
    assert lage["springt_an"] is False, "auf gewachsenem Bestand darf nichts von selbst starten"


def test_lage_fragt_genau_die_vier_dinge(leer):
    """C1: vier Fragen, mehr nicht."""
    fragen = {f["feld"] for f in einrichtung.lage(leer)["fragen"]}
    assert fragen == {"profil", "sprache", "einbettungsdienst", "kataloge"}, fragen


def test_durchlauf_macht_den_frischen_bestand_benutzbar(leer):
    """BDW-P11-AC1. 'Benutzbar' wird nicht an einer Fahne abgelesen, sondern
    gefahren: ein Knoten wird geschrieben und ueber den Volltextindex wieder
    gefunden."""
    ergebnis = einrichtung.durchlaufen(profil="einzelplatz", sprache="de",
                                       kataloge=(), db=leer)
    assert ergebnis["geaendert"] is True
    assert ergebnis["profil"] == "einzelplatz"
    assert ergebnis["sprache"] == "de"

    lage = einrichtung.lage(leer)
    assert lage["eingerichtet"] is True
    assert lage["springt_an"] is False, "nach dem Durchlauf springt nichts mehr an"

    with speicher.schreiben(leer) as conn:
        conn.execute(_BESTANDSKNOTEN, ("neu1", "/neu1",
                                       "Kalibrierbremse am Messlauf", "Probe"))
    with speicher.lesen(leer) as conn:
        treffer = conn.execute(
            "SELECT n.path FROM knowledge_fts f JOIN knowledge_nodes n "
            "ON n.rowid = f.rowid WHERE knowledge_fts MATCH 'kalibrierbremse'"
        ).fetchall()
    assert [r["path"] for r in treffer] == ["/neu1"], "geschriebener Knoten nicht auffindbar"


def test_gewachsener_bestand_wird_ohne_bestaetigung_nicht_angefasst(gewachsen):
    """Negativfall aus dem Auftrag: nichts stillschweigend aendern."""
    def stand():
        with speicher.lesen(gewachsen) as conn:
            return (
                sorted(tuple(r) for r in conn.execute(
                    "SELECT key, value FROM knowledge_config")),
                conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0],
            )

    vorher = stand()
    ergebnis = einrichtung.durchlaufen(profil="unternehmen", mandant="kunde-x",
                                       sprache="en", db=gewachsen)
    assert ergebnis["geaendert"] is False
    assert "bestaetigt" in ergebnis.get("hinweis", "").lower()
    assert stand() == vorher, "gewachsener Bestand wurde stillschweigend geaendert"


def test_gewachsener_bestand_mit_bestaetigung_aendert_doch(gewachsen):
    """Gegenprobe: ohne sie waere der Test darueber auch dann gruen, wenn
    durchlaufen() gar nichts kann."""
    ergebnis = einrichtung.durchlaufen(profil="unternehmen", mandant="kunde-x",
                                       sprache="en", db=gewachsen, bestaetigt=True)
    assert ergebnis["geaendert"] is True
    assert einrichtung.lage(gewachsen)["profil"] == "unternehmen"


# --- C1: der Einbettungsdienst wird geprueft, nicht angenommen ------------

def test_einbettungsdienst_meldet_ausfall_statt_ihn_zu_verschweigen():
    """Der Anlass: am 2026-08-20 entstanden 13 Eintraege OHNE Vektor, ohne
    dass ein Fehler erschien. Port 1 ist Loopback (die Ausnahme in
    embeddings.embed_text greift also nicht) und nimmt nichts an."""
    befund = einrichtung.einbettungsdienst(base_url="http://127.0.0.1:1")
    assert befund["erreichbar"] is False
    assert befund["modell"], "auch bei Ausfall muss das erwartete Modell genannt sein"


# --- C2: Kataloge, vorgeschlagen statt versteckt -------------------------

def test_kataloge_werden_vorgefunden_nicht_behauptet():
    namen = {k["name"] for k in einrichtung.kataloge()}
    assert {"bsi", "nasa-llis", "wcag"} <= namen
    for k in einrichtung.kataloge():
        assert k["gattung"] == "nachschlagewerk", k
        assert isinstance(k["vorhanden"], bool)


def test_katalogimport_traegt_nachschlagewerk_und_bleibt_aus_dem_abruf(leer):
    ergebnis = einrichtung.katalog_einlesen("wcag", db=leer)
    assert ergebnis["knoten"] > 0
    with speicher.lesen(leer) as conn:
        gattungen = {r[0] for r in conn.execute(
            "SELECT DISTINCT gattung FROM knowledge_nodes")}
        # Genau der Filter, den der Abrufweg benutzt (haken/knowledge_recall_hook.py).
        sichtbar = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes n WHERE 1=1 "
            f"{gattung_filter.SQL_ARBEITSBESTAND_NUR}").fetchone()[0]
    assert gattungen == {"nachschlagewerk"}, gattungen
    assert sichtbar == 0, "eingelesener Katalog darf im Arbeitsbestand nicht auftauchen"


# --- BDW-P12: der Import erfindet keine Herkunft -------------------------

def test_importherkunft_nennt_den_weg_und_behauptet_keine_quelle():
    h = fremdimport.importherkunft("holographic memory_store.db")
    assert h.startswith("importiert aus holographic memory_store.db am ")
    fremdimport.pruefe_importherkunft(h)   # darf NICHT werfen


@pytest.mark.parametrize("behauptung", [
    "BGBl I S. 123",
    "laut § 5 Abs. 2 GmbHG",
    "Quelle: Handbuch der Betriebspruefung",
    "",
])
def test_import_der_eine_quelle_behauptet_wird_abgelehnt(behauptung):
    with pytest.raises(ValueError):
        fremdimport.pruefe_importherkunft(behauptung)


def test_holographic_import_traegt_den_importweg(tmp_path, monkeypatch, leer):
    fremd = tmp_path / "memory_store.db"
    with speicher.schreiben(fremd) as conn:
        conn.executescript(
            "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT, "
            "category TEXT, tags TEXT, trust_score REAL, created_at TEXT);"
            "INSERT INTO facts (content, category, tags, trust_score) VALUES "
            "('Der Dienst startet ueber launchd, nicht ueber cron', 'betrieb', 'launchd', 0.9),"
            "('Backups liegen auf demselben Traeger', 'betrieb', 'backup', 0.4);"
        )
    ergebnis = fremdimport.aus_holographic(fremd, ziel_db=leer)
    assert ergebnis["knoten"] == 2
    with speicher.lesen(leer) as conn:
        quellen = {r[0] for r in conn.execute(
            "SELECT DISTINCT source FROM knowledge_nodes WHERE level > 0")}
    assert len(quellen) == 1
    quelle = quellen.pop()
    assert quelle.startswith("importiert aus holographic memory_store.db am "), quelle
    fremdimport.pruefe_importherkunft(quelle)


def test_markdown_ordner_import_traegt_den_importweg(tmp_path, leer):
    ordner = tmp_path / "notizen"
    ordner.mkdir()
    (ordner / "a.md").write_text("# Titel A\n\nEin Satz aus einer Notiz.\n", encoding="utf-8")
    (ordner / "b.md").write_text("# Titel B\n\nNoch ein Satz.\n", encoding="utf-8")
    (ordner / "c.txt").write_text("keine Notiz", encoding="utf-8")

    ergebnis = fremdimport.aus_markdown_ordner(ordner, ziel_db=leer)
    assert ergebnis["knoten"] == 2, "nur .md-Dateien werden gelesen"
    with speicher.lesen(leer) as conn:
        zeilen = conn.execute(
            "SELECT title, source, gattung FROM knowledge_nodes WHERE level > 0"
        ).fetchall()
    assert {r["title"] for r in zeilen} == {"Titel A", "Titel B"}
    for r in zeilen:
        assert r["gattung"] == "nachschlagewerk"
        fremdimport.pruefe_importherkunft(r["source"])


def test_schreibweg_lehnt_eine_behauptete_quelle_ab(tmp_path, leer):
    """Der Negativtest zu BDW-P12-AC1 am WRITE-Pfad, nicht nur am Pruefer:
    ein Import, der eine Quelle behauptet, kommt nicht in den Bestand."""
    with pytest.raises(ValueError):
        fremdimport.eintragen(
            [{"titel": "Angebliche Rechtslage", "text": "Gilt seit jeher."}],
            quelle="laut BGBl I S. 123",
            projekt="fremd", wurzel="/fremd", db=leer)
    with speicher.lesen(leer) as conn:
        assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0] == 0


# --- Das Werkzeug selbst -------------------------------------------------

def test_werkzeug_ist_angemeldet():
    assert "einrichtung_starten" in kms.TOOLS
    spec = kms.TOOLS["einrichtung_starten"]
    schema = spec["inputSchema"]["properties"]
    assert {"profil", "sprache", "kataloge", "bestaetigt"} <= set(schema)


def test_werkzeug_ohne_argumente_fragt_nur(leer, monkeypatch):
    monkeypatch.setattr(einrichtung, "_vorgabe_db", lambda: leer)
    ergebnis = kms.TOOLS["einrichtung_starten"]["handler"]({})
    assert ergebnis["geaendert"] is False
    assert ergebnis["fragen"], "ohne Antworten muss das Werkzeug fragen"
    assert json.dumps(ergebnis)  # muss serialisierbar bleiben (MCP-Antwort)
