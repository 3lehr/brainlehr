"""B4.4: die dritte Stelle des Rechts wirkt auf Datensaetze.

`own` und `published` sind der Grund, warum ueberhaupt dieses Rollenmodell
uebernommen wurde (Knoten /brainlehr/was-brainlehr-fuer-b4-fehlt-liegt-in):
ohne die dritte Stelle gibt es nur ganz-oder-gar-nicht, und genau daran
scheitert jede Trennung innerhalb EINES gemeinsamen Bestands.

ROT VOR GRUEN: ohne den Filter sieht ein Gast (wissen:lesen:published) jeden
internen Knoten, und ein Fachkundiger (wissen:schreiben:own) jeden fremden.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import ausweis  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402

GRUENDER = ""  # wird von der Fixture gesetzt (Gruendungsakt)


@pytest.fixture()
def bestand(tmp_path, monkeypatch):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(tmp_path / "a.json"))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    monkeypatch.delenv("BRAINLEHR_DURCHSETZUNG", raising=False)
    ausweis._pruefe.cache_clear()
    # Gruendungsakt: ohne ihn darf niemand mehr einbuergern. Der Schluessel
    # wandert als Modulattribut zu den Tests, damit sie ihn nicht durchreichen
    # muessen.
    global GRUENDER
    GRUENDER = ausweis.anlegen("gruender", ["betreiber"], art="mensch",
                               pfad=tmp_path / "a.json")

    def anlegen(titel: str) -> None:
        kms.knowledge_add(parent_path="/", title=titel,
                          summary="Wetterbericht fuer die Bezugsprobe",
                          source="test_bezug", neuer_ast=True,
                          norm_entscheidung="keine_norm",
                          norm_entschieden_grund="Testknoten",
                          actor="fremder", session="s", model="m")

    # Zwei fremde Knoten OHNE Ausweis -> actor wird 'unbeglaubigt:fremder'.
    anlegen("Wetterbericht offen")
    anlegen("Wetterbericht intern")

    # Der eigene Knoten entsteht MIT Ausweis -- nur dann traegt er den
    # beglaubigten Namen. Das ist keine Testkosmetik, sondern die Regel: wer
    # ohne Ausweis schreibt, kann sich spaeter nicht als Eigentuemer ausgeben,
    # denn 'unbeglaubigt:fachmann' kann von jedem stammen. Der Herkunftstrigger
    # macht das unumkehrbar -- actor ist nachtraeglich nicht aenderbar, und
    # genau daran ist die erste Fassung dieses Tests gescheitert.
    g_fach = ausweis.anlegen("fachmann", ["fachkundig"], pfad=tmp_path / "a.json",
                             aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g_fach)
    ausweis._pruefe.cache_clear()
    anlegen("Wetterbericht eigen")
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    ausweis._pruefe.cache_clear()

    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET freigabe='offen' WHERE title LIKE '%offen%'")
    conn.commit()
    conn.close()
    return tmp_path


def _titel(werkzeug="knowledge_search", args=None) -> list[str]:
    res = kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": werkzeug, "arguments": args or {"query": "Wetterbericht"}},
    })["result"]
    if res.get("isError"):
        return []
    daten = json.loads(res["content"][0]["text"])
    return sorted(t.get("title", "") for t in (daten.get("results") or []))


def test_gast_sieht_nur_freigegebene(bestand, monkeypatch):
    """P6: published. Alle Knoten stehen auf 'intern' ausser einem."""
    g = ausweis.anlegen("gastnutzer", ["gast"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()

    titel = _titel()

    assert titel == ["Wetterbericht offen"], (
        f"Gast sah interne Knoten: {titel}")


def test_leser_sieht_alle(bestand, monkeypatch):
    """Gegenprobe: wer 'alle' hat, wird nicht gefiltert -- sonst saehe der
    Filter genauso aus wie 'gib nie etwas zurueck'."""
    g = ausweis.anlegen("leser1", ["leser"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()
    assert len(_titel()) == 3


def test_ohne_ausweis_wird_nicht_gefiltert(bestand):
    """B4.1-Zusage: ohne Ausweis aendert sich nichts. Ein Aufrufer ohne
    Ausweis darf nicht ploetzlich WENIGER sehen als vorher."""
    assert len(_titel()) == 3


def test_count_wandert_mit(bestand, monkeypatch):
    """Eine Zahl, die mehr behauptet als die Liste zeigt, ist schlimmer als
    keine Zahl."""
    g = ausweis.anlegen("gastnutzer", ["gast"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()
    res = kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "knowledge_search",
                   "arguments": {"query": "Wetterbericht"}}})["result"]
    daten = json.loads(res["content"][0]["text"])
    assert daten["count"] == len(daten["results"]) == 1
    assert daten.get("gefiltert_nach_bezug") == "published"


def test_freigegebene_lehre_ist_fuer_gast_sichtbar(bestand, monkeypatch):
    """Nachtrag zu B4.5: die Spalte macht aus dem groben Schnitt einen feinen.

    Vorher war KEINE Lehre je fuer einen Gast sichtbar -- korrekt (was kein
    Freigabemerkmal tragen kann, ist nicht freigegeben), aber grob. Mit der
    nachgezogenen Spalte ist eine ausdruecklich freigegebene Lehre sichtbar und
    eine interne nicht.
    """
    off = kms.lesson_record(type_="insight",
                            description="Wetterbericht offen: Regen am Montag",
                            projects=["shared"], actor="fremder", session="s")["id"]
    kms.lesson_record(type_="insight",
                      description="Wetterbericht intern: Personallage montags",
                      projects=["shared"], actor="fremder", session="s")
    conn = sqlite3.connect(str(kms.DB_PATH))
    conn.execute("UPDATE lessons_learned SET freigabe='offen' WHERE id=?", (off,))
    conn.commit()
    conn.close()

    g = ausweis.anlegen("gastnutzer", ["gast"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()

    res = kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "knowledge_search",
                   "arguments": {"query": "Wetterbericht"}}})["result"]
    treffer = json.loads(res["content"][0]["text"])["results"]
    lehren = [t["id"] for t in treffer if t.get("kind") == "lesson"]

    assert off in lehren, "freigegebene Lehre blieb unsichtbar"
    assert len(lehren) == 1, f"interne Lehre kam durch: {lehren}"


def test_lehren_sind_fuer_gast_nicht_freigegeben(bestand, monkeypatch):
    """Der Befund des Koederlaufs vom 2026-08-10.

    lessons_learned traegt keine freigabe-Spalte -- der Bezug ist dort nicht
    entscheidbar. Die erste Fassung liess solche Eintraege durch und markierte
    sie nur; im Lauf gegen den echten Bestand sah ein Gast dadurch 5 von 10
    Treffern statt 0, allesamt Lehren. Und Lehren sind das DESTILLAT, also
    gerade die kompakten, merkbaren Aussagen. "published" heisst "nur
    ausdruecklich Freigegebenes"; was kein Freigabemerkmal tragen KANN, ist
    nicht freigegeben.
    """
    kms.lesson_record(type_="insight",
                      description="Wetterbericht: montags faellt mehr Regen",
                      projects=["shared"], actor="fremder", session="s")
    g = ausweis.anlegen("gastnutzer", ["gast"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()

    res = kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "knowledge_search",
                   "arguments": {"query": "Wetterbericht"}}})["result"]
    daten = json.loads(res["content"][0]["text"])
    arten = [t.get("kind") for t in daten["results"]]

    assert "lesson" not in arten, (
        f"Gast sah Lehren, obwohl sie keine Freigabe tragen koennen: {arten}")
    assert daten["results"] and all(a == "node" for a in arten)


def test_own_greift_auf_den_schreiber(bestand, monkeypatch):
    """P5: own. Der Fachkundige darf nur EIGENE Knoten schreiben -- geprueft
    ueber die Sicht, weil der Bezug dort messbar wird."""
    import werkzeugrechte
    # Ausweis existiert bereits aus der Fixture -- nur wieder aktivieren.
    g = ausweis.anlegen("fachmann", ["fachkundig"], pfad=bestand / "a.json", aussteller=GRUENDER)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()
    a = ausweis.loese_auf()
    assert ausweis.bezug_fuer(a, "wissen:schreiben") == "own"

    ergebnis = kms.knowledge_search("Wetterbericht")
    gefiltert = werkzeugrechte.filtere("knowledge_add", ergebnis, ausw=a,
                                       db_pfad=kms.DB_PATH)
    titel = sorted(t["title"] for t in gefiltert["results"])
    assert titel == ["Wetterbericht eigen"], titel
