"""Rot-vor-gruen fuer den Formatdrift-Fehler in normkraft.py::in_kraft
(Aufgabe 88, Linie B, docs/PLAN_GESAMT_2026-08-13.md).

BEFUND (gemessen 2026-08-15 gegen den echten Bestand, brainlehr.db):
26 von 85 gilt_ab-Werten sind reines Datum 'YYYY-MM-DD' ohne Offset, 59 volle
Zeitstempel mit '+01:00'. Beide gilt_bis-Werte im gesamten Bestand ('e4c346ea'
gilt_bis='2026-08-06', '1d0fd081' gilt_bis='2026-07-31') sind reines Datum.

Vor diesem Auftrag verglich in_kraft() per SQL-WHERE als reinen Text:
'gilt_bis >= ?'. Ein Stichtag mit Uhrzeit (z.B. der Vorgabewert now_iso(),
seit Aufgabe 111 immer volles UTC-'...Z') ist als STRING groesser als ein
reines Datum desselben Tages ('2026-08-06T18:00:00Z' > '2026-08-06'), obwohl
derselbe Kalendertag -- und gilt_bis ist laut Docstring von in_kraft INKLUSIV,
der letzte Geltungstag zaehlt VOLLSTAENDIG. Der alte Vergleich erklaerte die
Norm schon ab Tagesbeginn (genauer: ab jedem Zeitpunkt mit einer Uhrzeit
ueberhaupt) fuer abgelaufen -- den ganzen letzten Tag lang falsch.

Seit diesem Auftrag normalisiert geltungszeitpunkt() beide Seiten auf einen
echten, tz-bewussten Zeitpunkt (reines Datum -> Tagesanfang bzw. -ende UTC)
und in_kraft() vergleicht damit statt per SQL-Text.

NACHTRAG 2026-08-15: knowledge_mcp_server.py::_geltung_status (der Pfad, den
knowledge_search() beim Abruf tatsaechlich nimmt) trug bis dahin denselben
Stringvergleich und denselben Fehler -- war zunaechst als xfail
(test_geltung_status_bleibt_am_formatdrift_falsch) festgehalten, weil
ausserhalb des Schreibbereichs jenes Auftrags. Jetzt auf denselben
kanonischen Vergleich umgestellt (test_geltung_status_folgt_geltungszeitpunkt).
Wirkt erst nach Neustart eines MCP-Serverprozesses -- stdio kennt keinen
zentralen Neustart, laufende Sitzungen tragen den alten Codestand weiter.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import normkraft  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


def test_geltungszeitpunkt_reines_datum_grenzwerte():
    # gilt_ab: reines Datum -> Tagesanfang UTC.
    ab = normkraft.geltungszeitpunkt("2026-08-05", ende_des_tages=False)
    assert ab.isoformat() == "2026-08-05T00:00:00+00:00"
    # gilt_bis: reines Datum -> Tagesende UTC (INKLUSIV, siehe Moduldoc).
    bis = normkraft.geltungszeitpunkt("2026-08-06", ende_des_tages=True)
    assert bis.isoformat() == "2026-08-06T23:59:59+00:00"
    # voller Zeitstempel wird direkt geparst, Sommer-Fehlwert +01:00 eingeschlossen.
    voll = normkraft.geltungszeitpunkt("2026-08-05T13:07:16+01:00", ende_des_tages=False)
    assert voll.isoformat() == "2026-08-05T12:07:16+00:00"
    # None/leer -> None, kein Raten.
    assert normkraft.geltungszeitpunkt(None, ende_des_tages=False) is None
    assert normkraft.geltungszeitpunkt("", ende_des_tages=True) is None


def test_in_kraft_gegen_echten_bestand_reines_datum_gilt_bis():
    """Rot vor gruen: Knoten 'e4c346ea' (/ops/buckeberg-anbieterabend-2026-08-05)
    traegt echt gilt_ab='2026-08-05', gilt_bis='2026-08-06' -- beides reines
    Datum, kein Offset. Vor der Korrektur meldete in_kraft() diesen Knoten ab
    JEDEM Stichtag mit Uhrzeit am 06.08. (auch morgens) als abgelaufen."""
    db = normkraft.DB_PATH
    assert db.exists(), "echte brainlehr.db fehlt -- Pruefstand-Regel verlangt echten Bestand"

    # Grenzwert: letzter Geltungstag, kurz nach Mitternacht.
    treffer = {r["path"]: r for r in normkraft.in_kraft(db, stichtag="2026-08-06T00:00:01Z")}
    assert "/ops/buckeberg-anbieterabend-2026-08-05" in treffer

    # Grenzwert: letzter Geltungstag, kurz vor Mitternacht (voll ausgeschoepft).
    treffer = {r["path"]: r for r in normkraft.in_kraft(db, stichtag="2026-08-06T23:59:59Z")}
    assert "/ops/buckeberg-anbieterabend-2026-08-05" in treffer

    # Grenzwert: einen Tag danach -> abgelaufen.
    treffer = {r["path"]: r for r in normkraft.in_kraft(db, stichtag="2026-08-07T00:00:00Z")}
    assert "/ops/buckeberg-anbieterabend-2026-08-05" not in treffer

    # Grenzwert: gilt_ab-Tag selbst (reines Datum), erste Sekunde -> gilt schon.
    treffer = {r["path"]: r for r in normkraft.in_kraft(db, stichtag="2026-08-05T00:00:00Z")}
    assert "/ops/buckeberg-anbieterabend-2026-08-05" in treffer

    # Negativfall: Tag vor gilt_ab -> noch nicht in Kraft.
    treffer = {r["path"]: r for r in normkraft.in_kraft(db, stichtag="2026-08-04T23:59:59Z")}
    assert "/ops/buckeberg-anbieterabend-2026-08-05" not in treffer


def test_in_kraft_mischform_gilt_ab_voller_zeitstempel_gilt_bis_reines_datum():
    """Grenzwert: ein Knoten kann gilt_ab als vollen Zeitstempel und gilt_bis
    als reines Datum tragen (die zwei Formen mischen sich PRO ZEILE nicht im
    echten Bestand, aber nichts in der Datenbank verbietet es) -- beide Seiten
    muessen unabhaengig normalisiert werden."""
    db_path_tmp = _w / "tests" / "_tmp_formatdrift.db"
    if db_path_tmp.exists():
        db_path_tmp.unlink()
    try:
        normkraft._init_temp_db(db_path_tmp)
        conn = sqlite3.connect(str(db_path_tmp))
        try:
            normkraft._insert_node(
                conn, "n-mix", "/adr/mix", norm_rang=3,
                gilt_ab="2026-08-05T22:00:00+01:00",  # =21:00 UTC
                gilt_bis="2026-08-06",  # reines Datum -> bis 23:59:59 UTC
            )
            conn.commit()
        finally:
            conn.close()

        # Vor gilt_ab (in UTC gerechnet): 20:59 UTC = 21:59 Ortszeit +01:00 -> noch nicht in Kraft.
        assert "/adr/mix" not in {r["path"] for r in normkraft.in_kraft(db_path_tmp, "2026-08-05T20:59:00Z")}
        # Ab gilt_ab: in Kraft.
        assert "/adr/mix" in {r["path"] for r in normkraft.in_kraft(db_path_tmp, "2026-08-05T21:00:00Z")}
        # Letzter Geltungstag, spaeter Nachmittag: weiterhin in Kraft (reines Datum inklusiv).
        assert "/adr/mix" in {r["path"] for r in normkraft.in_kraft(db_path_tmp, "2026-08-06T18:00:00Z")}
        # Danach: abgelaufen.
        assert "/adr/mix" not in {r["path"] for r in normkraft.in_kraft(db_path_tmp, "2026-08-07T00:00:00Z")}
    finally:
        if db_path_tmp.exists():
            db_path_tmp.unlink()


def test_negativfall_ohne_gilt_bis_unveraendert():
    """Gegenprobe: ein unbefristeter Knoten (gilt_bis NULL) ist von der
    Korrektur unberuehrt -- weiterhin dauerhaft in Kraft ab gilt_ab."""
    db_path_tmp = _w / "tests" / "_tmp_formatdrift_unbefristet.db"
    if db_path_tmp.exists():
        db_path_tmp.unlink()
    try:
        normkraft._init_temp_db(db_path_tmp)
        conn = sqlite3.connect(str(db_path_tmp))
        try:
            normkraft._insert_node(conn, "n-u", "/adr/u", norm_rang=3, gilt_ab="2026-01-01")
            conn.commit()
        finally:
            conn.close()
        assert "/adr/u" in {r["path"] for r in normkraft.in_kraft(db_path_tmp, "2099-01-01T00:00:00Z")}
    finally:
        if db_path_tmp.exists():
            db_path_tmp.unlink()


def test_geltung_status_folgt_geltungszeitpunkt():
    """War xfail bis 2026-08-15: knowledge_mcp_server.py::_geltung_status (der
    tatsaechliche Abrufpfad von knowledge_search) verglich roh als String und
    trug denselben Formatdrift-Fehler wie in_kraft() vor dessen Korrektur.
    Seit diesem Auftrag nutzt _geltung_status denselben kanonischen Vergleich
    (normkraft.geltungszeitpunkt) -- Fix wirkt erst nach Neustart des
    MCP-Servers (stdio, kein zentraler Neustart), nicht in bereits laufenden
    Sitzungen."""
    # identischer Fall wie test_in_kraft_gegen_echten_bestand_reines_datum_gilt_bis,
    # Grenzwert 'letzter Geltungstag, kurz nach Mitternacht'.
    status = kms._geltung_status(6, "2026-08-05", "2026-08-06", "2026-08-06T00:00:01Z")
    assert status == "in_kraft"
    # Gegenprobe: unbefristete Norm bleibt in_kraft (gilt_bis None), auch mit
    # Uhrzeit im Stichtag.
    assert kms._geltung_status(6, "2026-08-05", None, "2099-01-01T00:00:01Z") == "in_kraft"
    # Gegenprobe: voller Zeitstempel auf beiden Seiten, ein Tag nach gilt_bis -> abgelaufen.
    assert kms._geltung_status(
        6, "2026-08-05T00:00:00+01:00", "2026-08-06T23:59:59+01:00", "2026-08-08T00:00:00Z"
    ) == "abgelaufen"
