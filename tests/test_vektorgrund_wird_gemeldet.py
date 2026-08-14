"""Ein verschluckter Grund ist schlimmer als kein Mechanismus -- er sieht aus,
als haette nichts stattgefunden.

GEMESSEN 2026-08-14, nachgestellt und Schritt fuer Schritt belegt:
knowledge_add() legte den Knoten c87b937c an und schrieb NULL Vektorzeilen.
Ursache war NICHT der Einbettungsdienst (bge-m3 lief, 200 auf /api/tags),
sondern die Modellsperre: der laufende MCP-Serverprozess war um 21:44
gestartet, die Identitaetsaenderung auf 'bge-m3@ctx2048' kam um 23:51
(Commit cd56071). Der alte Prozess schrieb weiter den rohen Namen 'bge-m3',
knowledge_config fuehrte schon die Identitaet -- der Trigger
knowledge_embeddings_model_check_bi wies den INSERT ab. Gegen eine frische
Schema-DB nachgestellt: 'bge-m3' abgewiesen, 'bge-m3@ctx2048' angenommen.

DER TRIGGER SAGT WOERTLICH, WAS ZU TUN IST ("Prozess laeuft vermutlich mit
veraltetem Code ... Sitzung neu starten") -- und `except sqlite3.IntegrityError:
pass` hat diese Meldung verschluckt. Der naechste build_embeddings.py-Lauf
flickte die Luecke stillschweigend; auffaellig wurde es erst, als ein Test
dreimal hintereinander an derselben Stelle rot wurde.

Und die zweite Haelfte, die es so lange unsichtbar hielt: Der Melder dafuer
EXISTIERT (haken/mcp_veraltet.py), ist in ~/.claude/settings.json verdrahtet
und meldet korrekt ("8 laufende Prozess(e) veraltet"). Er haengt aber an
UserPromptSubmit -- und im Selbstlauf gibt es keine Prompts. Der Melder ist
also genau dann blind, wenn niemand zusieht. Deshalb muss der Grund am
SCHREIBVORGANG haengen, nicht am Haken.

RUECKGABE STATT AUSNAHME: Werfen wuerde den Schreibvorgang scheitern lassen,
obwohl der Eintrag selbst gueltig ist -- dieselbe Fehlklasse wie die
norm_art-Sperre vom 2026-08-13, die laufende fremde Sitzungen blockierte.

Rot vor gruen: gegen den Stand davor liefern beide Bauer None statt eines
Grundes, und das Feld 'vektor' fehlt im Ergebnis.
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


def _db(tmp_path):
    pfad = tmp_path / "probe.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("UPDATE knowledge_config SET value = ? WHERE key = 'embed_model'",
                 (embeddings.DEFAULT_EMBED_MODEL,))
    conn.commit()
    return conn


def test_modellsperre_meldet_ihren_grund_statt_zu_schweigen(tmp_path, monkeypatch):
    """Der Kern: ein abgewiesener INSERT gibt den Trigger-Text zurueck."""
    conn = _db(tmp_path)
    # Prozess mit veraltetem Code nachgestellt: schreibt den ROHEN Namen,
    # waehrend knowledge_config die Identitaet fuehrt.
    monkeypatch.setattr(embeddings, "DEFAULT_EMBED_MODEL", "bge-m3")
    monkeypatch.setattr(embeddings, "embed_text", lambda *a, **k: [0.1, 0.2])

    grund = kms._rebuild_node_embedding(conn, "n1", "shared", "/p", "T", "S", None)

    assert grund, "Der abgewiesene INSERT muss seinen Grund zurueckgeben"
    assert "veraltetem Code" in grund and "neu starten" in grund, (
        f"Der Grund muss den Trigger-Text durchreichen, bekam: {grund!r}")


def test_gegenprobe_erfolg_meldet_nichts(tmp_path, monkeypatch):
    """Ohne diese Richtung bestuende der Test darueber auch bei einem Bauer,
    der IMMER einen Grund meldet -- und dann waere jedes Ergebnis voller
    Rauschen."""
    conn = _db(tmp_path)
    monkeypatch.setattr(embeddings, "embed_text", lambda *a, **k: [0.1, 0.2])

    assert kms._rebuild_node_embedding(conn, "n2", "shared", "/p", "T", "S", None) is None
    zeilen = conn.execute(
        "SELECT COUNT(*) FROM knowledge_embeddings WHERE ref_id='n2'").fetchone()[0]
    assert zeilen == 1


def test_toter_dienst_meldet_anderen_grund_als_die_modellsperre(tmp_path, monkeypatch):
    """Zwei verschiedene Ursachen duerfen nicht denselben Satz erzeugen --
    sonst startet jemand die Sitzung neu, obwohl nur Ollama tot war."""
    conn = _db(tmp_path)
    monkeypatch.setattr(embeddings, "embed_text", lambda *a, **k: None)

    grund = kms._rebuild_node_embedding(conn, "n3", "shared", "/p", "T", "S", None)

    assert grund and "Einbettungsdienst" in grund
    assert "veraltetem Code" not in grund


def test_lehrenbauer_meldet_ebenso(tmp_path, monkeypatch):
    """Dieselbe Zusicherung fuer Lehren -- sie liefen durch denselben
    stillen except-Zweig."""
    conn = _db(tmp_path)
    monkeypatch.setattr(embeddings, "DEFAULT_EMBED_MODEL", "bge-m3")
    monkeypatch.setattr(embeddings, "embed_text", lambda *a, **k: [0.1, 0.2])

    grund = kms._rebuild_lesson_embedding(conn, "L-000001", None, '["brainlehr"]',
                                          "Beschreibung", None, None)

    assert grund and "veraltetem Code" in grund


def test_kein_stiller_except_zweig_mehr():
    """Ratsche: wer den Zweig spaeter wieder auf `pass` setzt, faellt hier
    auf. Der Grund fuer die Ratsche steht im Modulkopf -- die Meldung war
    jahrelang da und wurde nie gelesen."""
    quelle = (WURZEL / "knowledge_mcp_server.py").read_text(encoding="utf-8")
    for zeile in quelle.splitlines():
        assert not zeile.strip().startswith("except sqlite3.IntegrityError:") or True
    # Genauer: kein `except sqlite3.IntegrityError:` unmittelbar gefolgt von `pass`
    zeilen = quelle.splitlines()
    for i, zeile in enumerate(zeilen[:-1]):
        if zeile.strip() == "except sqlite3.IntegrityError:":
            assert zeilen[i + 1].strip() != "pass", (
                f"Zeile {i + 2}: verschluckter IntegrityError. Der Trigger nennt "
                "die Ursache im Klartext -- gib sie zurueck, statt sie "
                "wegzuwerfen (siehe Modulkopf dieses Tests)."
            )
