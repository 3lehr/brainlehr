"""Tests fuer die Ablage-Disziplin von knowledge_add() (Plan 2026-08-05, P1).

Befund, der diese Arbeit ausgeloest hat: 180 von 219 Knoten wurden nie
abgerufen. Zwei der drei Ursachen sitzen hier:

  U1  parent_path wurde woertlich uebernommen, ohne Pruefung, ob dieser
      Elternknoten ueberhaupt existiert. Jeder schreibende Agent konnte
      seinen eigenen Ast erfinden -- Wissen landete an Stellen, die kein
      spaeterer Abruf je betritt.
  U2  Der Slug kappte hart bei 40 Zeichen, mitten im Wort, und liess
      Satzzeichen im Pfad stehen. Ergebnis im Live-Bestand:
        /openlehr/steuer/ui/adr-—-frontend-framework-(vue-3),-arbeit
        /apps/fahrtenbuch/café-international-konsil-einstellungseb

Gegenprobe in beide Richtungen: ein *vorhandener* Elternpfad muss weiterhin
ohne Reibung durchgehen, sonst hat die Sperre nur das Schreiben kaputtgemacht.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, source) "
        "VALUES (?, ?, ?, 'shared', ?, ?, ?, 'test')",
        [
            ("r1", "/shared", None, "Shared", "Wurzel fuer projektuebergreifendes", 0),
            ("r2", "/shared/arch", "/shared", "Architektur", "Architekturentscheidungen", 1),
            ("r3", "/apps", None, "Apps", "Wurzel je App", 0),
            ("r4", "/apps/fahrtenbuch", "/apps", "Fahrtenbuch", "Die Fahrtenbuch-App", 1),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# --- U1: Elternpfad muss existieren -----------------------------------------

def test_unbekannter_elternpfad_wird_abgelehnt(temp_db):
    """Der Fall, der 219 Knoten ueber erfundene Aeste verstreut hat."""
    res = kms.knowledge_add("/erfundener/ast", "Irgendein Fund", "Eine Zusammenfassung")
    assert "error" in res, f"unbekannter Elternpfad wurde angelegt: {res}"
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/erfundener%'"
    ).fetchone()[0] == 0, "Knoten wurde trotz Fehler geschrieben"
    conn.close()


def test_fehler_nennt_naheliegende_echte_pfade(temp_db):
    """Eine Ablehnung ohne Wegweiser erzeugt nur einen zweiten Rateversuch."""
    res = kms.knowledge_add("/apps/fahrtenbuc", "Tippfehler im Ast", "Zusammenfassung", source="test")
    assert "error" in res
    vorschlaege = " ".join(res.get("vorhandene_pfade", []))
    assert "/apps/fahrtenbuch" in vorschlaege, res


def test_vorhandener_elternpfad_geht_weiterhin_durch(temp_db):
    """Gegenprobe: die Sperre darf das normale Schreiben nicht treffen."""
    res = kms.knowledge_add("/shared/arch", "MCP Serverwahl", "Warum stdio statt HTTP", source="test")
    assert res.get("status") == "created", res
    assert res["path"] == "/shared/arch/mcp-serverwahl"


def test_wurzel_darf_ohne_elternknoten_beschrieben_werden(temp_db):
    """'/' hat per Definition keinen Elternknoten -- sonst kaeme nie einer rein."""
    res = kms.knowledge_add("/", "Neue Wurzel", "Ein Ast auf oberster Ebene", source="test")
    assert res.get("status") == "created", res
    assert res["path"] == "/neue-wurzel"


def test_neuer_ast_nur_mit_ausdruecklicher_erlaubnis(temp_db):
    """Ein neuer Ast muss moeglich bleiben -- aber als Entscheidung, nicht als
    Nebenwirkung eines Tippfehlers."""
    res = kms.knowledge_add("/apps/openlehr", "Erster Fund", "Zusammenfassung",
                            neuer_ast=True, source="test")
    assert res.get("status") == "created", res
    assert res["path"] == "/apps/openlehr/erster-fund"


# --- U2: Slug -----------------------------------------------------------------

def test_slug_kappt_nicht_mitten_im_wort(temp_db):
    """Live-Beispiel: '...konsil-einstellungseb' -- 'einstellungsebene' halbiert."""
    res = kms.knowledge_add(
        "/apps/fahrtenbuch",
        "Café International Konsil Einstellungsebene und Nachlauf",
        "Zusammenfassung",
        source="test",
    )
    slug = res["path"].rsplit("/", 1)[-1]
    assert not slug.endswith("einstellungseb"), res
    assert all(t in ("cafe", "international", "konsil", "einstellungsebene", "und", "nachlauf")
               for t in slug.split("-")), slug


def test_satzzeichen_landen_nicht_im_pfad(temp_db):
    """Live-Beispiel: '/…/adr-—-frontend-framework-(vue-3),-arbeit'."""
    res = kms.knowledge_add(
        "/shared/arch",
        "ADR — Frontend-Framework (Vue 3), Arbeitsstand",
        "Zusammenfassung",
        source="test",
    )
    slug = res["path"].rsplit("/", 1)[-1]
    for zeichen in ("—", "(", ")", ",", "."):
        assert zeichen not in slug, (zeichen, slug)
    assert "--" not in slug, slug
    assert not slug.startswith("-") and not slug.endswith("-"), slug


def test_slug_bleibt_bei_einem_ueberlangen_wort_nutzbar(temp_db):
    """Grenzfall: ein einzelnes Wort laenger als das Limit. Es an der
    Wortgrenze zu kappen hiesse, gar nichts uebrig zu lassen."""
    res = kms.knowledge_add("/shared/arch", "Donaudampfschifffahrtsgesellschaftskapitaenspatent",
                            "Zusammenfassung", source="test")
    slug = res["path"].rsplit("/", 1)[-1]
    assert 0 < len(slug) <= kms.SLUG_MAX_LEN, slug


def test_umlaute_werden_gefaltet_nicht_verschluckt(temp_db):
    res = kms.knowledge_add("/shared/arch", "Prüfung äußerer Größen", "Zusammenfassung", source="test")
    assert res["path"] == "/shared/arch/pruefung-aeusserer-groessen", res
