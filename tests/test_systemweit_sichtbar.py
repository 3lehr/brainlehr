"""Eine Lehre mit projects=['systemweit'] muss bei jedem scope gefunden werden.

ROT VOR GRUEN: Gegen den Stand vor dieser Aenderung filterte knowledge_search
mit gesetztem scope so --

    AND (l.projects LIKE '%"shared"%' OR l.projects LIKE ?)

Der Filter kennt 'shared', aber nicht 'systemweit'. Gemessen am 2026-08-10:
150 aktive Lehren tragen 'systemweit' OHNE 'shared' und waren damit bei
gesetztem scope unsichtbar, sofern sie nicht zufaellig das Zielprojekt
mittrugen; 98 davon auch ohne 'brainlehr'.

Das Wort, mit dem im ganzen Haus "gilt ueberall" ausgedrueckt wird (CLAUDE.md
durchgaengig 'systemweit'), war fuer die Suche kein Bereich, sondern ein
Projektname wie jeder andere.
"""
from __future__ import annotations

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

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _lehre(beschreibung: str, projects: list[str]) -> str:
    return kms.lesson_record(
        type_="insight", description=beschreibung, projects=projects,
        actor="test", model="test", session="test",
    )["id"]


def _gefunden(treffer: dict, lesson_id: str) -> bool:
    """Treffer stehen unter 'results', nicht unter 'lessons'. Ein falscher
    Schluessel liefert immer False -- dann sieht die Gegenprobe
    (test_fremdes_projekt_bleibt_gefiltert) gruen aus, obwohl sie nichts
    prueft. Beim Bau dieses Tests genau so passiert."""
    return any(t.get("id") == lesson_id for t in (treffer.get("results") or []))


def test_systemweit_ist_bei_jedem_scope_sichtbar(db):
    """Der Kern: 'systemweit' heisst ueberall, nicht 'im Projekt systemweit'."""
    lid = _lehre("Reconnect-Zaehler laeuft im Hintergrund weiter", ["systemweit"])

    treffer = kms.knowledge_search("Reconnect-Zaehler", scope="fahrtenbuch")

    assert _gefunden(treffer, lid), (
        "Eine Lehre mit projects=['systemweit'] war bei gesetztem scope "
        "unsichtbar -- der Filter kannte nur 'shared'."
    )


def test_shared_bleibt_sichtbar(db):
    """Nicht-Regression: der bisher einzige Universalbereich haelt."""
    lid = _lehre("Reconnect-Zaehler laeuft im Hintergrund weiter", ["shared"])
    assert _gefunden(kms.knowledge_search("Reconnect-Zaehler", scope="fahrtenbuch"), lid)


def test_fremdes_projekt_bleibt_gefiltert(db):
    """Gegenprobe in die andere Richtung: die Erweiterung darf den Filter
    nicht insgesamt aufheben. Ohne diese Probe wuerde ein 'immer alles
    zurueckgeben' genauso gruen aussehen wie der richtige Fix."""
    lid = _lehre("Reconnect-Zaehler laeuft im Hintergrund weiter", ["wohlair"])
    assert not _gefunden(kms.knowledge_search("Reconnect-Zaehler", scope="fahrtenbuch"), lid)


def test_ohne_scope_ist_alles_sichtbar(db):
    """Grenzfall: kein scope -> kein Bereichsfilter, auch fremde Projekte."""
    lid = _lehre("Reconnect-Zaehler laeuft im Hintergrund weiter", ["wohlair"])
    assert _gefunden(kms.knowledge_search("Reconnect-Zaehler"), lid)
