"""Auftrag B3 (docs/PLAN_GESAMTBAU_2026-08-21.md §2): die Achsen aus B1 werden
ERZWUNGEN -- BDW-E03, BDW-E06, BDW-E22, BDW-E23.

B1 hat `mandant`, `kreis` und `geltung_je_kreis` ins Schema gelegt. Eine Spalte
trennt nichts; sie beschreibt nur. Hier steht die Durchsetzung.

DREI SORTEN VON ZUSICHERUNG, und die dritte ist die, die man vergisst:

1. NEGATIV -- der fremde Mandant/Kreis sieht den Eintrag nicht. Je Weg ein
   eigener Test, weil BDW-E06-AC1 sechs Wege woertlich aufzaehlt
   (Lesen, Suche, Relation, Export, Backup, Admin) und ein Weg, der nicht
   geprueft ist, offen ist.
2. POSITIV -- der eigene Mandant/Kreis sieht ihn WEITERHIN VOLLSTAENDIG. Eine
   Trennung, die alles sperrt, ist keine Trennung, und der echte Bestand
   (5240 Knoten, alle mandant='lokal', kreis='') muss unveraendert sichtbar
   bleiben.
3. ZAEHLUNG -- BDW-E22-AC2. Der Hausmeister muss die Regel nicht lesen; es
   genuegt, dass er eine VERAENDERUNG bemerkt: gestern drei Treffer, heute
   zwei. Dagegen hilft keine Rechtepruefung, weil nichts Verbotenes gelesen
   wurde -- es wurde nur gezaehlt. Deshalb pruefen die Zaehl-Tests jede
   Ausgabe, die eine ZAHL nennt: Trefferzahl, children_count, Kantenzahl,
   knowledge_stats.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "pflege")]

import sqlite3  # noqa: E402

import pytest  # noqa: E402

import ausweis  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import trennung  # type: ignore  # noqa: E402

import export_offen  # type: ignore  # noqa: E402
import knowledge_db_snapshot  # type: ignore  # noqa: E402

# Pflichtfelder eines Knotens (Trigger erzwingen sie) -- ohne sie scheitert
# jeder INSERT aus einem Grund, der mit diesem Auftrag nichts zu tun hat.
_SPALTEN = ("id, path, parent_path, level, title, summary, source, updated_at, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, "
            "mandant, kreis, freigabe")

# Ein Wort, das in JEDEM Testknoten steht: eine Anfrage findet damit alles,
# was sichtbar ist -- und nur daran laesst sich eine Trefferzahl vergleichen.
STICHWORT = "trennungsprobe"


def _knoten(conn, ident, pfad, mandant="lokal", kreis="", freigabe="intern",
            eltern=None, level=0):
    conn.execute(
        f"INSERT INTO knowledge_nodes ({_SPALTEN}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ident, pfad, eltern, level, f"Titel {ident}",
         f"{STICHWORT} Inhalt von {ident}", "test", "jetzt", "keine_norm",
         "skript:test", "Testvorrichtung", mandant, kreis, freigabe))


def _lehre(conn, ident, mandant="lokal", kreis=""):
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, status, mandant, kreis) "
        "VALUES (?, 'insight', ?, 'active', ?, ?)",
        (ident, f"{STICHWORT} Lehre {ident}", mandant, kreis))


def _ausweis(name, mandant="lokal", kreise=(), rollen=("leser",)):
    return ausweis.Ausweis(name=name, rollen=tuple(rollen), beglaubigt=True,
                           mandant=mandant, kreise=tuple(kreise))


@pytest.fixture
def welt(tmp_path, monkeypatch):
    """Drei Knoten, drei Lehren, eine Kante -- ueber zwei Mandanten und zwei
    Kreise verteilt. Klein genug, dass jede Zahl von Hand nachzaehlbar ist."""
    db = tmp_path / "trennung.db"
    monkeypatch.setattr(kms, "DB_PATH", db)
    monkeypatch.setattr(knowledge_db_snapshot, "DB", db)
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    _knoten(conn, "n_allg", "/allg", freigabe="offen")
    _knoten(conn, "n_eng", "/eng", kreis="vorstand", freigabe="offen")
    _knoten(conn, "n_fremd", "/fremd", mandant="fremd", freigabe="offen")
    _lehre(conn, "L-allg")
    _lehre(conn, "L-eng", kreis="vorstand")
    _lehre(conn, "L-fremd", mandant="fremd")
    conn.execute(
        "INSERT INTO knowledge_relations (id, source_path, target_path, "
        "relation_type, source, updated_at) VALUES "
        "('r1','/allg','/eng','relates_to','test','jetzt')")
    conn.commit()
    conn.close()
    yield db


def _als(monkeypatch, ausw):
    """Ausweis setzen. Der Server loest ihn ueber ausweis.loese_auf() auf --
    genau die eine Stelle wird umgebogen, damit die Tests keine zweite
    Aufloesung erfinden."""
    monkeypatch.setattr(ausweis, "loese_auf", lambda *a, **k: ausw)


def _pfade(treffer):
    return {t.get("path") or t.get("id") for t in treffer}


# ── BDW-E06-AC1: die sechs Wege, je einer ein eigener Testfall ────────────
# "Cross-Tenant-Lesen, -Suche, -Relation, -Export, -Backup und -Admin
# scheitern." Ein Positivtest allein belegt keine Trennung -- deshalb steht
# unter jedem Negativtest die Gegenprobe in test_e06_eigener_mandant_*.

def test_e06_lesen_cross_tenant_scheitert(welt, monkeypatch):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd"))
    for ref in ("n_allg", "/allg"):
        erg = kms.knowledge_read(ref)
        assert "error" in erg, f"fremder Mandant las {ref}: {erg}"
        # NICHT-GEFUNDEN, nicht "verweigert": ein "zugriff verweigert" verraet,
        # DASS es den Knoten gibt -- dieselbe Kroete wie bei FREIGABE_GESPERRT.
        assert "not found" in erg["error"].lower()


def test_e06_suche_cross_tenant_scheitert(welt, monkeypatch):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd"))
    erg = kms.knowledge_search(STICHWORT, max_results=50)
    gefunden = _pfade(erg["results"])
    assert "/allg" not in gefunden and "/eng" not in gefunden, gefunden
    assert "L-allg" not in gefunden and "L-eng" not in gefunden, gefunden
    # Gegenprobe innerhalb desselben Tests: der fremde Mandant sieht SEINEN
    # Knoten sehr wohl. Ohne sie belegt ein leeres Ergebnis nur, dass die
    # Suche kaputt ist.
    assert "/fremd" in gefunden, gefunden


def test_e06_relation_cross_tenant_scheitert(welt, monkeypatch):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd"))
    erg = kms.knowledge_relation_list()
    assert erg["count"] == 0, erg
    # Und die Kante darf auch nicht QUER angelegt werden koennen.
    with pytest.raises(Exception):
        kms.knowledge_relation_add("/fremd", "/allg", "relates_to")


def test_e06_export_cross_tenant_scheitert(welt, monkeypatch):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd"))
    zeilen = export_offen.sammle(welt)
    ids = {z["zeile"]["id"] for z in zeilen}
    assert "n_allg" not in ids and "n_eng" not in ids, ids
    assert "L-allg" not in ids, ids


def test_e06_backup_cross_tenant_scheitert(welt, monkeypatch, tmp_path):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd"))
    # Eine Datei-Kopie kennt keine WHERE-Klausel: sie nimmt alles mit oder
    # nichts. Deshalb ist die einzig ehrliche Durchsetzung die Verweigerung,
    # solange fremde Zeilen in der Datei liegen.
    ziel = tmp_path / "ziel"
    with pytest.raises(PermissionError):
        knowledge_db_snapshot.freeze(ziel, quelle=welt)
    assert not ziel.exists() or not list(ziel.glob("*.db")), \
        "die Sicherung wurde trotz Abweisung geschrieben"
    # Gegenprobe: derselbe Aufruf im eigenen Mandanten muss laufen -- eine
    # Sicherung, die nie geht, ist keine Schranke, sondern ein Defekt.
    _als(monkeypatch, _ausweis("heimisch"))
    conn = sqlite3.connect(welt)
    conn.execute("DELETE FROM knowledge_nodes WHERE mandant='fremd'")
    conn.execute("DELETE FROM lessons_learned WHERE mandant='fremd'")
    conn.commit(); conn.close()
    assert knowledge_db_snapshot.freeze(ziel, quelle=welt)["bestand_knowledge_nodes"] == 2


def test_e06_admin_cross_tenant_scheitert(welt, monkeypatch):
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd", rollen=("betreiber",)))
    erg = kms.freigabe_setzen("n_allg", "offen")
    assert "error" in erg, erg
    erg = kms.knowledge_update("n_allg", summary="uebernommen")
    assert "error" in erg, erg
    conn = sqlite3.connect(welt)
    assert conn.execute("SELECT summary FROM knowledge_nodes WHERE id='n_allg'"
                        ).fetchone()[0].startswith(STICHWORT)
    conn.close()


def test_e06_eigener_mandant_sieht_seinen_bestand_vollstaendig(welt, monkeypatch):
    """Gegenprobe in die andere Richtung -- ohne sie waere 'alles gesperrt'
    ein bestandener Test."""
    _als(monkeypatch, _ausweis("heimisch", rollen=("betreiber",)))
    assert kms.knowledge_read("n_allg")["path"] == "/allg"
    gefunden = _pfade(kms.knowledge_search(STICHWORT, max_results=50)["results"])
    assert {"/allg", "L-allg"} <= gefunden, gefunden
    assert "/fremd" not in gefunden, gefunden
    ids = {z["zeile"]["id"] for z in export_offen.sammle(welt)}
    assert "n_allg" in ids and "n_fremd" not in ids, ids
    assert kms.freigabe_setzen("n_allg", "intern").get("error") is None
    assert kms.knowledge_relation_list()["count"] == 0   # /eng ist enger Kreis
    _als(monkeypatch, _ausweis("innen", kreise=("vorstand",), rollen=("betreiber",)))
    assert kms.knowledge_relation_list()["count"] == 1


# ── BDW-E22-AC1: der fremde Kreis sieht den engen Teil nicht ──────────────

def test_e22_fremder_kreis_sieht_engen_eintrag_nicht(welt, monkeypatch):
    _als(monkeypatch, _ausweis("heimisch"))          # mandant lokal, KEIN Kreis
    assert "not found" in kms.knowledge_read("n_eng").get("error", "").lower()
    gefunden = _pfade(kms.knowledge_search(STICHWORT, max_results=50)["results"])
    assert "/eng" not in gefunden and "L-eng" not in gefunden, gefunden


def test_e22_eigener_kreis_sieht_engen_eintrag(welt, monkeypatch):
    _als(monkeypatch, _ausweis("innen", kreise=("vorstand",)))
    assert kms.knowledge_read("n_eng")["path"] == "/eng"
    gefunden = _pfade(kms.knowledge_search(STICHWORT, max_results=50)["results"])
    # Der eigene Kreis sieht BEIDES -- den engen Teil UND den allgemeinen.
    assert {"/eng", "/allg", "L-eng", "L-allg"} <= gefunden, gefunden


# ── BDW-E22-AC2: die ZAEHLUNG verraet nichts ──────────────────────────────

def _zahlen(conn_pfad):
    """Jede Ausgabe, die eine ZAHL nennt. Wer hier eine vergisst, hat die
    Rechtepruefung gebaut und das Leck offen gelassen."""
    stats = kms.knowledge_stats()
    return {
        "suche": kms.knowledge_search(STICHWORT, max_results=50)["count"],
        "browse_wurzel": kms.knowledge_browse("/")["count"],
        "kinder": sum(c["children_count"] for c in kms.knowledge_browse("/")["children"]),
        "kanten": kms.knowledge_relation_list()["count"],
        "stats_knoten": stats["nodes_total"],
        "stats_lehren": stats["lessons_total"],
        "stats_lehren_aktiv": stats["lessons_active"],
    }


def test_e22_neuer_enger_eintrag_aendert_die_zahlen_des_fremden_kreises_nicht(
        welt, monkeypatch):
    _als(monkeypatch, _ausweis("heimisch"))
    vorher = _zahlen(welt)

    conn = sqlite3.connect(welt)
    _knoten(conn, "n_eng2", "/allg/eng2", kreis="vorstand", eltern="/allg", level=1)
    _lehre(conn, "L-eng2", kreis="vorstand")
    conn.execute("INSERT INTO knowledge_relations (id, source_path, target_path, "
                 "relation_type, source, updated_at) VALUES "
                 "('r2','/allg','/allg/eng2','relates_to','test','jetzt')")
    conn.commit()
    conn.close()

    nachher = _zahlen(welt)
    assert vorher == nachher, (
        "ein neu angelegter enger Eintrag hat die Zahlen des fremden Kreises "
        f"veraendert: {vorher} -> {nachher}")


def test_e22_eigener_kreis_sieht_die_zahl_sehr_wohl(welt, monkeypatch):
    """Gegenprobe zur Zaehlung: waeren die Zahlen fuer JEDEN eingefroren,
    wuerde der Test oben auch bei einer kaputten Suche bestehen."""
    _als(monkeypatch, _ausweis("heimisch"))
    ohne_kreis = _zahlen(welt)
    _als(monkeypatch, _ausweis("innen", kreise=("vorstand",)))
    mit_kreis = _zahlen(welt)
    assert mit_kreis["suche"] > ohne_kreis["suche"]
    assert mit_kreis["stats_knoten"] > ohne_kreis["stats_knoten"]
    assert mit_kreis["kanten"] > ohne_kreis["kanten"]


# ── BDW-E23-AC1: Geltung je Kreis, zweiseitig ─────────────────────────────

def test_e23_dieselbe_regel_gilt_fuer_zwei_kreise_verschieden_lang(welt, monkeypatch):
    conn = sqlite3.connect(welt)
    conn.execute("UPDATE knowledge_nodes SET norm_rang=3, gilt_ab='2020-01-01', "
                 "gilt_bis='2026-12-31', kreis='', norm_entscheidung='norm_befristet' "
                 "WHERE id='n_allg'")
    for kreis, bis in (("kurz", "2021-12-31"), ("lang", "2099-12-31")):
        conn.execute("INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, "
                     "gilt_ab, gilt_bis) VALUES ('knoten','n_allg',?, '2020-01-01', ?)",
                     (kreis, bis))
    conn.commit()
    conn.close()

    _als(monkeypatch, _ausweis("kurzer", kreise=("kurz",)))
    assert kms.knowledge_read("n_allg")["gilt_bis"] == "2021-12-31"
    _als(monkeypatch, _ausweis("langer", kreise=("lang",)))
    assert kms.knowledge_read("n_allg")["gilt_bis"] == "2099-12-31"
    # Wer keinen Eintrag hat, bekommt die SPALTENVORGABE -- nicht nichts und
    # nicht den Wert eines fremden Kreises.
    _als(monkeypatch, _ausweis("ohne"))
    assert kms.knowledge_read("n_allg")["gilt_bis"] == "2026-12-31"


def test_e23_geltung_eines_kreises_faerbt_nicht_auf_die_suche_ab(welt, monkeypatch):
    conn = sqlite3.connect(welt)
    conn.execute("UPDATE knowledge_nodes SET norm_rang=3, gilt_ab='2020-01-01', "
                 "gilt_bis='2099-12-31', norm_entscheidung='norm_befristet' "
                 "WHERE id='n_allg'")
    conn.execute("INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, "
                 "gilt_ab, gilt_bis) VALUES ('knoten','n_allg','kurz','2020-01-01','2021-12-31')")
    conn.commit()
    conn.close()

    _als(monkeypatch, _ausweis("kurzer", kreise=("kurz",)))
    treffer = [t for t in kms.knowledge_search(STICHWORT, max_results=50,
                                               stichtag="2026-08-21T00:00:00Z")["results"]
               if t.get("path") == "/allg"]
    assert treffer and treffer[0].get("geltung") == "abgelaufen", treffer
    _als(monkeypatch, _ausweis("ohne"))
    treffer = [t for t in kms.knowledge_search(STICHWORT, max_results=50,
                                               stichtag="2026-08-21T00:00:00Z")["results"]
               if t.get("path") == "/allg"]
    assert treffer and treffer[0].get("geltung") in (None, "gueltig"), treffer


# ── BDW-E03-AC1: Negativmatrix Rolle × Objekt × Zweck × Mandant ───────────

# Der Erwartungswert steht HIER und wird von Hand aus zwei vorhandenen
# Tabellen hergeleitet -- nicht aus einem Lauf von wirksames_recht()
# abgelesen. Ein abgelesener Erwartungswert kann nie widersprechen.
#
#   kern/ausweis.py::ROLLEN            -> welche Rolle darf welches OBJEKT lesen
#   knowledge_mcp_server.py::_KNOWLEDGE_READ_VOLLZUGRIFF / _PROJEKTION
#                                      -> zu welchem ZWECK
#
# betreiber('*'), schreiber, fachkundig, leser tragen wissen:/lehre:/kante:lesen
# und stehen in VOLLZUGRIFF -> alle drei Objekte, Zweck 'allgemein'.
# raumplaner traegt NUR wissen:lesen und in der Projektion ('raumplanung', ...)
# -> knoten × raumplanung, sonst nichts.
# gast traegt wissen:lesen:published UND lehre:lesen:published und in der
# Projektion ('wartung', ...) -> knoten und lehre × wartung, keine Kante.
# meldeamt traegt nur ausweis:ausstellen -> gar nichts.
# Und nichts davon gilt im fremden Mandanten.
ERWARTET_ERLAUBT = (
    {(r, o, "allgemein", "lokal")
     for r in ("betreiber", "schreiber", "fachkundig", "leser")
     for o in ("knoten", "lehre", "kante")}
    | {("raumplaner", "knoten", "raumplanung", "lokal")}
    | {("gast", "knoten", "wartung", "lokal"), ("gast", "lehre", "wartung", "lokal")}
)


def test_e03_negativmatrix_verweigert_jede_fehlende_freigabe():
    """Vorgabe ist DENY. Der Test zaehlt nicht die Erlaubnisse nach, sondern
    faehrt das VOLLE Kreuzprodukt und verlangt, dass alles ausserhalb der
    Tabelle verweigert wird -- eine neue Rolle ist damit automatisch gesperrt,
    bis jemand sie eintraegt."""
    erlaubt, verweigert = set(), set()
    for rolle in sorted(ausweis.ROLLEN):
        ausw = _ausweis("x", mandant="lokal", rollen=(rolle,))
        for objekt in trennung.OBJEKTE:
            for zweck in trennung.ZWECKE:
                for m in ("lokal", "fremd"):
                    fall = (rolle, objekt, zweck, m)
                    (erlaubt if trennung.wirksames_recht(
                        ausw, objekt=objekt, zweck=zweck, mandant=m)
                     else verweigert).add(fall)

    assert erlaubt == ERWARTET_ERLAUBT, (
        f"zuviel erlaubt: {sorted(erlaubt - ERWARTET_ERLAUBT)} / "
        f"fehlend: {sorted(ERWARTET_ERLAUBT - erlaubt)}")
    # Kein einziger Fall des FREMDEN Mandanten darf erlaubt sein -- die
    # Mandantenachse verengt, sie erweitert nie.
    assert not [f for f in erlaubt if f[3] == "fremd"]
    assert len(verweigert) == 7 * 3 * 3 * 2 - len(ERWARTET_ERLAUBT)


def test_e03_unbekannte_rolle_bekommt_nichts():
    ausw = _ausweis("x", rollen=("erfundene_rolle",))
    assert not trennung.wirksames_recht(ausw, objekt="knoten", zweck="allgemein",
                                        mandant="lokal")


def test_e03_vorhandene_blaupause_bleibt_erhalten():
    """kern/ausweis.py::raumplaner hatte VOR diesem Auftrag einen engen Zugang
    je Datensatz (Zweckprojektion im Server). Die Achse ersetzt sie nicht --
    sie verengt sie zusaetzlich."""
    rp = _ausweis("planer", rollen=("raumplaner",))
    assert trennung.wirksames_recht(rp, objekt="knoten", zweck="raumplanung",
                                    mandant="lokal")
    assert not trennung.wirksames_recht(rp, objekt="knoten", zweck="allgemein",
                                        mandant="lokal")
    assert not trennung.wirksames_recht(rp, objekt="knoten", zweck="raumplanung",
                                        mandant="fremd")


# ── Die Schreibseite: ohne Erzeuger waere die Achse ein toter Melder ──────

def test_neuer_eintrag_traegt_den_mandanten_des_ausweises(welt, monkeypatch):
    """Ohne diesen Zug schriebe der fremde Mandant in den EIGENEN Bestand
    hinein -- und saehe seinen eigenen Eintrag im naechsten Moment nicht mehr.
    Der Mandant kommt aus dem Ausweis, nicht aus einem Parameter: waere er ein
    Parameter, waere er eine Anrede und keine Trennung."""
    _als(monkeypatch, _ausweis("fremdling", mandant="fremd", rollen=("schreiber",)))
    erg = kms.knowledge_add("/fremd", "Neuer Punkt", f"{STICHWORT} neu",
                            norm_entscheidung="keine_norm",
                            norm_entschieden_grund="Testvorrichtung",
                            source="test")
    assert erg.get("error") is None, erg
    lehre = kms.lesson_record("insight", f"{STICHWORT} neue Lehre")
    conn = sqlite3.connect(welt)
    assert conn.execute("SELECT mandant FROM knowledge_nodes WHERE id=?",
                        (erg["id"],)).fetchone()[0] == "fremd"
    assert conn.execute("SELECT mandant FROM lessons_learned WHERE id=?",
                        (lehre["id"],)).fetchone()[0] == "fremd"
    conn.close()
    # Und der eigene Mandant sieht davon nichts -- Gegenprobe zum Schreibweg.
    _als(monkeypatch, _ausweis("heimisch"))
    assert "not found" in kms.knowledge_read(erg["id"]).get("error", "").lower()


def test_kreis_nur_der_eigene_beim_anlegen(welt, monkeypatch):
    """Ein Kreis, dem der Schreiber nicht angehoert, wird abgewiesen statt
    angenommen -- sonst legte er einen Eintrag an, den er selbst nicht mehr
    findet, und suchte den Fehler in der Suche."""
    _als(monkeypatch, _ausweis("innen", kreise=("vorstand",), rollen=("schreiber",)))
    assert "error" in kms.knowledge_add(
        "/allg", "Fremdkreis", f"{STICHWORT} x", norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testvorrichtung", source="test", kreis="aufsicht")
    assert kms.lesson_record("insight", f"{STICHWORT} y",
                             kreis="aufsicht")["status"] == "rejected"

    erg = kms.knowledge_add("/allg", "Eigenkreis", f"{STICHWORT} z",
                            norm_entscheidung="keine_norm",
                            norm_entschieden_grund="Testvorrichtung",
                            source="test", kreis="vorstand")
    assert erg.get("error") is None, erg
    assert kms.knowledge_read(erg["id"])["path"].endswith("eigenkreis")
    # Der Nachbar ohne diesen Kreis sieht ihn nicht -- auch nicht als Zahl.
    _als(monkeypatch, _ausweis("heimisch"))
    assert "not found" in kms.knowledge_read(erg["id"]).get("error", "").lower()
    assert kms.knowledge_stats()["nodes_total"] == 1


# ── Der echte Bestand bleibt unveraendert sichtbar ────────────────────────

def test_bestand_ohne_achsen_bleibt_vollstaendig_sichtbar(welt, monkeypatch):
    """Alle 5240 Zeilen des Betriebs tragen mandant='lokal', kreis=''. Ein
    Aufrufer OHNE Ausweis (der Normalfall im Betrieb: 'KEIN ABWEISEN OHNE
    AUSWEIS', kern/ausweis.py) muss sie weiterhin vollstaendig sehen."""
    _als(monkeypatch, ausweis.Ausweis(name="unbekannt", rollen=(), beglaubigt=False))
    gefunden = _pfade(kms.knowledge_search(STICHWORT, max_results=50)["results"])
    assert {"/allg", "L-allg"} <= gefunden, gefunden
    assert kms.knowledge_read("n_allg")["path"] == "/allg"
    # Genau EIN Knoten traegt mandant='lokal' UND kreis='' -- /eng gehoert
    # dem Kreis 'vorstand', /fremd dem Mandanten 'fremd'.
    assert kms.knowledge_stats()["nodes_total"] == 1
