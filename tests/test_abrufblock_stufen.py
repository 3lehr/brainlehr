#!/usr/bin/env python3
"""S2 aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md: die abgestufte Ausgabe.

DER BEFUND, der diesen Test verlangt (Konsil 2026-08-20, zwei Rollen
unabhaengig -- Forensik ueber getrennte Ausgabestufen, Alarmmanagement ueber
IEC 60601-1-8, wo niedrigpriore Alarme rein visuell sind):

  Nicht die Fehlerrate senken, sondern den PREIS des Fehlers.

Die Fehlerrate ist gemessen nicht senkbar -- der beste Kosinuswert trennt
"liegt etwas im Bestand" fehlerfrei und "ist es richtig" gar nicht
(runs/kreuztabelle_bc_2026-08-20.json: Median der Fehlgriffe 0,6030 gegen
0,5970 bei den echten Treffern). Der Preis dagegen ist senkbar: Von 20
Fehlgriffen sind 12 thematisch nah und sachlich nutzlos
(runs/beurteilung_bf_cf_2026-08-20.json). Heute kostet jeder davon einen
vollen Absatz im Kontext. Als einzeilige Fundstelle kostet er eine Zeile.

WAS HIER GEPRUEFT WIRD, und was ausdruecklich NICHT:
  Geprueft wird die BAUFORM der Ausgabe -- zwei Stufen, kein Treffer
  verschwindet, ein schwacher Treffer kostet eine Zeile statt eines Absatzes.
  NICHT geprueft wird, ob die Stufung die richtigen Treffer trifft. Das ist
  eine Frage an den Pruefkorpus, nicht an den Formatierer, und die Schwelle
  dafuer (STARK_AB in kern/relevanzlage.py) wird hier bewusst NICHT
  nachkalibriert: die am 2026-08-20 gefundene 0,545 steht bei n=24 mit einer
  Luecke von 0,0087 und ist nach Wilson mit einer Trefferquote von 78 %
  vereinbar.

ROT VOR GRUEN: Gegen den Stand vor dieser Aenderung faellt JEDER Fall unten
mit AttributeError -- `block_bauen` existiert dort nicht, der Blockaufbau
liegt als Schleife mitten in main() und ist von aussen nicht aufrufbar.
Genau das ist der erste Teil der Arbeit: die Formatierung aus main()
herausloesen, damit sie ueberhaupt pruefbar wird.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import sqlite3  # noqa: E402

import pytest  # noqa: E402

import knowledge_recall_hook as hook  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture(autouse=True)
def _stufen_an(monkeypatch):
    """Die Stufung ist per Vorgabe AUS -- solange S1 (Aufgriffsquote) nicht
    erhoben ist, darf der Betrieb sich nicht aendern. Diese Faelle pruefen
    die eingeschaltete Bauform und muessen den Schalter deshalb selbst
    setzen. Dass sie ohne ihn fallen, ist die Probe darauf, dass die Vorgabe
    wirklich AUS ist -- beim ersten Lauf waren genau die vier Faelle rot, die
    Stufung erwarten."""
    monkeypatch.setenv("BRAINLEHR_ABRUF_STUFEN", "an")


def _knoten(pfad: str, titel: str, zus: str, wert: float | None = None) -> dict:
    """Feldnamen wie query() sie liefert -- `bedeutungs_kosinus` AM TREFFER.

    Die erste Fassung dieses Tests erfand ein eigenes Format (ein Dict
    Kennung->Wert, nach Pfad geschluesselt) und war deshalb gruen, waehrend
    die Stufung im Betrieb NICHTS getan haette: gemessen war die Schnittmenge
    zwischen den echten Schluesseln und den Pfaden 0. Ein Test gegen ein
    selbst erfundenes Format prueft den Erfinder, nicht den Code."""
    t = {"path": pfad, "title": titel, "summary": zus,
         "updated_at": "2026-08-19T10:00:00+00:00"}
    if wert is not None:
        t["bedeutungs_kosinus"] = wert
    return t


def _lehre(kennung: str, beschreibung: str, praevention: str,
           wert: float | None = None) -> dict:
    t = {"id": kennung, "type": "antipattern", "severity": "high",
         "occurrences": 3, "description": beschreibung,
         "prevention": praevention, "last_seen": "2026-08-19T10:00:00+00:00"}
    if wert is not None:
        t["bedeutungs_kosinus"] = wert
    return t


# Zwei Werte, die die Schwelle sicher auf beiden Seiten treffen. Aus der
# Konstanten abgeleitet, NICHT abgeschrieben -- ein Test, der die Zahl fest
# eintraegt, meldet spaeter die Entscheidung selbst als Fehler (L-54b09d).
STARK = hook.STUFE_AB + 0.05
SCHWACH = hook.STUFE_AB - 0.05


def test_zwei_stufen_erscheinen_beide():
    """Der Block traegt beide Ueberschriften, sobald es beide Sorten gibt."""
    text = "\n".join(hook.block_bauen(
        nodes=[_knoten("/a/stark", "Starker Titel", "Starke Zusammenfassung.", STARK)],
        lessons=[],
        bedeutungswerte=[STARK, SCHWACH],
        erstverwendung_zeilen=[],
        schwache_nodes=[_knoten("/a/schwach", "Schwacher Titel", "Schwache Zusammenfassung.", SCHWACH)],
        schwache_lessons=[],
    ))
    assert "EINSCHLÄGIG" in text, text
    assert "NUR FUNDSTELLEN" in text, text


def test_starker_treffer_traegt_seine_zusammenfassung():
    text = "\n".join(hook.block_bauen(
        nodes=[_knoten("/a/stark", "Starker Titel", "Starke Zusammenfassung.", STARK)],
        lessons=[],
        bedeutungswerte=[STARK], erstverwendung_zeilen=[],
        schwache_nodes=[], schwache_lessons=[],
    ))
    assert "Starke Zusammenfassung." in text, text


def test_schwacher_treffer_kostet_eine_zeile_ohne_zusammenfassung():
    """Der Kern der Massnahme: der Treffer bleibt sichtbar, sein PREIS faellt.

    Ein schwacher Treffer erscheint mit Pfad und Titel, aber OHNE
    Zusammenfassung -- sonst ist nichts gewonnen."""
    zus = "Diese Zusammenfassung darf im schwachen Block nicht auftauchen."
    text = "\n".join(hook.block_bauen(
        nodes=[], lessons=[],
        bedeutungswerte=[SCHWACH], erstverwendung_zeilen=[],
        schwache_nodes=[_knoten("/a/schwach", "Schwacher Titel", zus, SCHWACH)],
        schwache_lessons=[],
    ))
    assert "/a/schwach" in text and "Schwacher Titel" in text, text
    assert zus not in text, ("Zusammenfassung im schwachen Block -- der Preis "
                             "des Fehlers ist nicht gesunken", text)


def test_schwache_lehre_ohne_praevention():
    """Bei Lehren ist die Praevention der laengste Teil -- gerade sie faellt
    in der schwachen Stufe weg."""
    prev = "Diese Praevention ist der teuerste Teil und gehoert nicht in die schwache Stufe."
    text = "\n".join(hook.block_bauen(
        nodes=[], lessons=[],
        bedeutungswerte=[SCHWACH], erstverwendung_zeilen=[],
        schwache_nodes=[],
        schwache_lessons=[_lehre("L-abc123", "Kurze Beschreibung.", prev, SCHWACH)],
    ))
    assert "L-abc123" in text, text
    assert prev not in text, text


def test_kein_treffer_verschwindet():
    """Die Zaehlprobe: jede uebergebene Kennung steht im Block.

    Das ist die Zusicherung, die diese Aenderung von einem Filter
    unterscheidet. Faellt sie, ist aus der Abstufung ein Weglassen geworden."""
    zeilen = hook.block_bauen(
        nodes=[_knoten("/a/eins", "Eins", "Z1."), _knoten("/a/zwei", "Zwei", "Z2.")],
        lessons=[_lehre("L-stark1", "B1.", "P1.")], bedeutungswerte=[STARK], erstverwendung_zeilen=[],
        schwache_nodes=[_knoten("/a/drei", "Drei", "Z3.")],
        schwache_lessons=[_lehre("L-schwach1", "B2.", "P2.")],
    )
    text = "\n".join(zeilen)
    for kennung in ("/a/eins", "/a/zwei", "L-stark1", "/a/drei", "L-schwach1"):
        assert kennung in text, (kennung, text)


def test_ohne_schwache_treffer_keine_leere_ueberschrift():
    """NEGATIVFALL: Eine Ueberschrift ohne Inhalt ist Rauschen. Ohne schwache
    Treffer sieht der Block aus wie bisher -- auch die starke Ueberschrift
    entfaellt dann, sonst gliedert sie eine Liste ohne Gegenstueck."""
    text = "\n".join(hook.block_bauen(
        nodes=[_knoten("/a/stark", "Starker Titel", "Starke Zusammenfassung.", STARK)],
        lessons=[],
        bedeutungswerte=[STARK], erstverwendung_zeilen=[],
        schwache_nodes=[], schwache_lessons=[],
    ))
    assert "NUR FUNDSTELLEN" not in text, text
    assert "EINSCHLÄGIG" not in text, text
    assert "Starke Zusammenfassung." in text, text


def test_rahmen_bleibt_unveraendert():
    """Der Block behaelt seine Klammer und die Frageform -- an ihr haengen
    andere Pruefungen und die Gewohnheit jedes Lesers."""
    text = "\n".join(hook.block_bauen(
        nodes=[_knoten("/a/stark", "T", "Z.", STARK)], lessons=[], bedeutungswerte=[STARK],
        erstverwendung_zeilen=[], schwache_nodes=[], schwache_lessons=[],
    ))
    assert text.startswith("<knowledge-recall>"), text
    assert text.rstrip().endswith("</knowledge-recall>"), text
    assert "Trifft das hier zu?" in text, text


def test_schwacher_block_kostet_deutlich_weniger_zeichen():
    """Das Erfolgsmass aus dem Plan, als Zusicherung: derselbe Treffer in der
    schwachen Stufe braucht ein Vielfaches weniger Platz. Ohne diese Probe
    koennte die Abstufung kosmetisch sein."""
    lang = "L" * 600
    voll = "\n".join(hook.block_bauen(
        nodes=[_knoten("/a/x", "Titel", lang, STARK)], lessons=[], bedeutungswerte=[STARK],
        erstverwendung_zeilen=[], schwache_nodes=[], schwache_lessons=[],
    ))
    knapp = "\n".join(hook.block_bauen(
        nodes=[], lessons=[],
        bedeutungswerte=[SCHWACH], erstverwendung_zeilen=[],
        schwache_nodes=[_knoten("/a/x", "Titel", lang, SCHWACH)], schwache_lessons=[],
    ))
    assert len(knapp) < len(voll) / 2, (len(knapp), len(voll))


def test_schalter_aus_liefert_die_alte_bauform():
    """Solange S1 (Aufgriffsquote) nicht erhoben ist, darf die Umstellung den
    Betrieb NICHT veraendern -- sonst ist die Nulllinie weg, gegen die sich
    die Wirkung spaeter vergleichen liesse. Der Schalter ist die Umsetzung
    dieser Reihenfolge, nicht Vorsicht."""
    import os
    alt = os.environ.get("BRAINLEHR_ABRUF_STUFEN")
    os.environ["BRAINLEHR_ABRUF_STUFEN"] = "aus"   # ueberschreibt die Fixture bewusst
    try:
        text = "\n".join(hook.block_bauen(
            nodes=[_knoten("/a/stark", "T", "Z.", STARK)], lessons=[], bedeutungswerte=[STARK],
            erstverwendung_zeilen=[],
            schwache_nodes=[_knoten("/a/schwach", "S", "SZ.", SCHWACH)],
            schwache_lessons=[],
        ))
    finally:
        if alt is None:
            os.environ.pop("BRAINLEHR_ABRUF_STUFEN", None)
        else:
            os.environ["BRAINLEHR_ABRUF_STUFEN"] = alt
    assert "NUR FUNDSTELLEN" not in text, text
    # Bei ausgeschalteter Stufung erscheint der schwache Treffer VOLL --
    # genau wie heute, kein Treffer geht verloren.
    assert "SZ." in text, text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_echter_abrufweg_liefert_das_feld_das_die_stufung_liest(monkeypatch):
    """DER TEST, DER BEIM ERSTEN MAL GEFEHLT HAT.

    Die erste Fassung dieser Datei fuetterte ein selbst erfundenes Format und
    war gruen, waehrend die Stufung im Betrieb NICHTS getan haette -- gemessen
    war die Schnittmenge zwischen den echten Schluesseln und den erwarteten 0.
    Genau die Fehlerklasse, gegen die dieses Repo gebaut ist: gebaut, laufend,
    wirkungslos.

    Dieser Fall geht deshalb gegen den ECHTEN Abrufweg und prueft nur das, was
    die Stufung braucht: dass query() das Feld liefert, auf das einstufen()
    schaut. Er faellt, sobald jemand das Feld umbenennt -- und dann faellt er
    HIER statt still im Betrieb.

    Nur lesend gegen den Bestand; er wird uebersprungen, wo es keinen gibt."""
    nodes, lessons = hook.query(
        ["abrufguete", "pruefkorpus", "stichprobe", "nenner"],
        cwd=str(_w),
        prompt="wie messe ich die abrufguete gegen den pruefkorpus mit nenner und stichprobe")
    if not nodes and not lessons:
        pytest.skip("kein Bestand erreichbar -- nichts zu pruefen")
    for treffer in list(nodes) + list(lessons):
        assert "bedeutungs_kosinus" in treffer, (
            "einstufen() liest bedeutungs_kosinus -- fehlt es, stuft die "
            "Stufung ALLES als stark ein und tut nichts", sorted(treffer))
        wert = treffer["bedeutungs_kosinus"]
        assert wert is None or 0.0 <= wert <= 1.0, wert


def test_abrufweg_ohne_bestand_ist_leer(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "DB", tmp_path / "absent.db")
    assert hook.query(["irrelevant"], cwd=str(_w)) == ([], [])


def test_echter_abrufweg_gegen_minimalen_migrierten_bestand(monkeypatch, tmp_path):
    """Der deterministische Gegenpol zum optionalen Live-Bestandstest.

    Erstanlage, FTS-Trigger, Rangfolge und read-only Recall muessen auch ohne
    die lokale gewachsene DB zusammen funktionieren.  Der Test verwendet die
    Produktionsmigration statt eines Schema-Ausschnitts; ein Recall darf dabei
    den gespeicherten Zugriffzaehler nicht still veraendern.
    """
    db = tmp_path / "minimal.db"
    monkeypatch.setattr(kms, "DB_PATH", db)
    conn = sqlite3.connect(db)
    try:
        kms.ensure_schema(conn)
        for ident, path, title, summary in (
            ("seed-best", "/recall-ranking", "Abrufguete Messung",
             "Abrufguete pruefkorpus Stichprobe Nenner kontrolliert Rangfolge"),
            ("seed-other", "/recall-nebenfall", "Abrufguete Hinweis",
             "Abrufguete pruefkorpus mit anderem Nenner"),
        ):
            conn.execute(
                """INSERT INTO knowledge_nodes
                   (id, path, parent_path, level, title, summary, source,
                    updated_at, norm_entscheidung, norm_entschieden_von,
                    norm_entschieden_grund)
                   VALUES (?, ?, NULL, 0, ?, ?, 'test',
                           '2026-08-26T00:00:00+00:00', 'keine_norm',
                           'test:seed', 'deterministic test')""",
                (ident, path, title, summary),
            )
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0] == 2
    finally:
        conn.close()

    monkeypatch.setattr(hook, "DB", str(db))
    nodes, lessons = hook.query(
        ["abrufguete", "pruefkorpus", "stichprobe", "nenner"],
        prompt="abrufguete pruefkorpus stichprobe nenner",
        rand=lambda: 0.9,
    )
    assert lessons == []
    assert [node["path"] for node in nodes] == [
        "/recall-ranking", "/recall-nebenfall",
    ]

    conn = sqlite3.connect(db)
    try:
        # query() ist ein RO-Pfad; erst log_recall()/main() protokollieren den
        # Zugriff ausserhalb der DB.  Ein stilles access_count++ hier waere
        # eine nicht dokumentierte, testisolierung-brechende Seiteneffektion.
        assert conn.execute(
            "SELECT access_count FROM knowledge_nodes WHERE id='seed-best'"
        ).fetchone()[0] == 0
    finally:
        conn.close()
