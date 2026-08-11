#!/usr/bin/env python3
"""Ein Prüfspruch gehört dem Prüfer, nicht dem Geprüften.

ANLASS, 2026-08-11: Ein Konsil aus drei unabhängigen Stimmen verwarf den
Vorschlag seines Auftraggebers. Genau das leistet eine Prüfinstanz. Der
Betreiber wies darauf hin, dass damit die Voraussetzung "zweite Person"
erfüllt ist -- und die Prüfung ergab: teilweise. Sie zerfällt in drei Teile:

  a) eigener Kontext        -- getrennte Fenster, aber dieselbe CLAUDE.md,
                               derselbe Speicher, dieselbe Modellfamilie
  b) eigener Zugang zum Rohmaterial -- fehlte: die Fakten standen im Auftrag,
                               Recherche war untersagt
  c) Urteil nicht still unterdrückbar -- fehlte vollständig: derselbe, der
                               den Auftrag schrieb, schrieb auch das Ergebnis

Diese Datei baut (c), und nur (c). Sie ist der billigste der drei Teile: er
kostet keine Token, nur die Entscheidung, dass ein Urteil ein eigener Eintrag
wird statt eines Absatzes im Bericht des Geprüften.

WIE DIE UNTERDRÜCKUNG VERHINDERT WIRD -- und was das NICHT leistet:
Jede Zeile trägt einen Kettenhash über ihre Vorgängerin (dasselbe Verfahren wie
knowledge_mcp_server.compute_ketten_hash für access_log, hier eigenständig
nachgebaut, weil es eine andere Tabelle ist). Wird eine Zeile gelöscht oder
geändert, bricht die Kette und `--pruefen` sagt es.

Die Grenze ist dieselbe wie dort und wird hier ausdrücklich wiederholt: das
weist eine nachträgliche Änderung NACH, es verhindert sie nicht. Wer
Schreibrechte auf die Datei hat, kann die Kette neu rechnen. Der Schutz ist
also kein technischer, sondern ein sozialer: ein gebrochener Anker ist eine
Aussage, die man erklären muss. Ein Prüfspruch, der stillschweigend
verschwindet, war vorher unsichtbar -- jetzt hinterlässt er ein Loch.

WER SCHREIBT: der Prüfer selbst, mit seiner eigenen Kennung. Ein Auftraggeber,
der den Spruch seines eigenen Prüfers einträgt, hat wieder nur eine Stimme --
dann ist `pruefer` und `auftraggeber` derselbe Wert, und genau das meldet
`--liste` als Befund statt es zu verschweigen.

Aufruf:
    python3 pruefspruch.py --schreiben --frage "..." --urteil "..." \
        --begruendung "..." --pruefer "..." --auftraggeber "..."
    python3 pruefspruch.py --liste
    python3 pruefspruch.py --pruefen        # Kette nachrechnen
    python3 pruefspruch.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import speicher  # noqa: E402

CET = timezone(timedelta(hours=2))
GENESIS = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS pruefsprueche (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    frage         TEXT NOT NULL,
    urteil        TEXT NOT NULL,
    begruendung   TEXT NOT NULL,
    pruefer       TEXT NOT NULL,
    auftraggeber  TEXT NOT NULL,
    modell        TEXT,
    sitzung       TEXT,
    erstellt_am   TEXT NOT NULL,
    ketten_hash   TEXT NOT NULL
);
"""


def _jetzt() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S%z")


def kettenhash(vorher: str | None, *, frage: str, urteil: str, begruendung: str,
               pruefer: str, auftraggeber: str, modell: str | None,
               sitzung: str | None, erstellt_am: str) -> str:
    """Feldreihenfolge ist Teil des Vertrags -- eine Änderung hier bricht jede
    bereits geschriebene Kette rückwirkend."""
    felder = (vorher or GENESIS, frage, urteil, begruendung, pruefer,
              auftraggeber, modell, sitzung, erstellt_am)
    nutzlast = "|".join("" if f is None else str(f) for f in felder)
    return hashlib.sha256(nutzlast.encode("utf-8")).hexdigest()


def schreiben(conn: sqlite3.Connection, *, frage: str, urteil: str,
              begruendung: str, pruefer: str, auftraggeber: str,
              modell: str | None = None, sitzung: str | None = None,
              erstellt_am: str | None = None) -> dict:
    """Ein Spruch. Kein Feld ist optional ausser Modell und Sitzung -- wer
    prüft, wer beauftragt hat, was gefragt war und warum das Urteil so lautet,
    ist der ganze Inhalt. Fehlt die Begründung, ist es kein Spruch, sondern
    eine Behauptung."""
    for name, wert in (("frage", frage), ("urteil", urteil),
                        ("begruendung", begruendung), ("pruefer", pruefer),
                        ("auftraggeber", auftraggeber)):
        if not (wert or "").strip():
            raise ValueError(f"pruefspruch: {name} fehlt -- ohne dieses Feld ist der "
                             "Spruch nicht nachvollziehbar")
    conn.executescript(SCHEMA)
    letzte = conn.execute(
        "SELECT ketten_hash FROM pruefsprueche ORDER BY id DESC LIMIT 1").fetchone()
    stamp = erstellt_am or _jetzt()
    kh = kettenhash(letzte["ketten_hash"] if letzte else None,
                    frage=frage, urteil=urteil, begruendung=begruendung,
                    pruefer=pruefer, auftraggeber=auftraggeber, modell=modell,
                    sitzung=sitzung, erstellt_am=stamp)
    conn.execute(
        "INSERT INTO pruefsprueche (frage, urteil, begruendung, pruefer, "
        "auftraggeber, modell, sitzung, erstellt_am, ketten_hash) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (frage, urteil, begruendung, pruefer, auftraggeber, modell, sitzung,
         stamp, kh))
    return {"ketten_hash": kh, "erstellt_am": stamp,
            "eigenpruefung": pruefer.strip() == auftraggeber.strip()}


def pruefen(conn: sqlite3.Connection) -> dict:
    """Rechnet die Kette nach. Ein Loch heisst: eine Zeile wurde gelöscht oder
    geändert. Das ist die einzige Aussage, die dieses Verfahren macht."""
    zeilen = conn.execute(
        "SELECT * FROM pruefsprueche ORDER BY id").fetchall()
    vorher = None
    for z in zeilen:
        erwartet = kettenhash(vorher, frage=z["frage"], urteil=z["urteil"],
                              begruendung=z["begruendung"], pruefer=z["pruefer"],
                              auftraggeber=z["auftraggeber"], modell=z["modell"],
                              sitzung=z["sitzung"], erstellt_am=z["erstellt_am"])
        if erwartet != z["ketten_hash"]:
            return {"heil": False, "bruch_bei_id": z["id"], "zeilen": len(zeilen),
                    "befund": f"Kette bricht bei Spruch {z['id']} -- eine Zeile "
                              "davor wurde geaendert oder entfernt"}
        vorher = z["ketten_hash"]
    return {"heil": True, "zeilen": len(zeilen),
            "letzter_hash": vorher, "befund": "Kette geschlossen"}


def liste(conn: sqlite3.Connection) -> list[dict]:
    zeilen = conn.execute("SELECT * FROM pruefsprueche ORDER BY id").fetchall()
    ergebnis = []
    for z in zeilen:
        d = dict(z)
        # Der Befund, der sonst verschwiegen würde: hat sich hier jemand selbst
        # geprüft? Das ist kein Fehler, aber es ist keine zweite Stimme.
        d["eigenpruefung"] = (z["pruefer"] or "").strip() == (z["auftraggeber"] or "").strip()
        ergebnis.append(d)
    return ergebnis


def _selftest() -> None:
    import tempfile

    db = Path(tempfile.mkdtemp()) / "probe.db"
    gemeinsam = dict(frage="Traegt X?", begruendung="weil Y gemessen wurde")

    with speicher.schreiben(db) as conn:
        a = schreiben(conn, urteil="nein", pruefer="stimme-1",
                      auftraggeber="orchestrator", **gemeinsam)
        b = schreiben(conn, urteil="ja", pruefer="stimme-2",
                      auftraggeber="orchestrator", **gemeinsam)
    assert a["ketten_hash"] != b["ketten_hash"]

    # 1) Heile Kette.
    with speicher.lesen(db) as conn:
        assert pruefen(conn)["heil"] is True
        assert len(liste(conn)) == 2

    # 2) DER FALL, FUER DEN ES GEBAUT IST: ein Spruch verschwindet still.
    with speicher.schreiben(db) as conn:
        conn.execute("DELETE FROM pruefsprueche WHERE urteil='nein'")
    with speicher.lesen(db) as conn:
        e = pruefen(conn)
        assert e["heil"] is False, "geloeschter Spruch blieb unbemerkt"
        assert e["bruch_bei_id"] == 2, e

    # 3) Gegenprobe: auch das stille AENDERN eines Urteils bricht die Kette --
    #    sonst koennte man ein 'nein' in ein 'ja' verwandeln statt zu loeschen.
    db2 = Path(tempfile.mkdtemp()) / "probe2.db"
    with speicher.schreiben(db2) as conn:
        schreiben(conn, urteil="nein", pruefer="p", auftraggeber="o", **gemeinsam)
        schreiben(conn, urteil="nein", pruefer="p2", auftraggeber="o", **gemeinsam)
        conn.execute("UPDATE pruefsprueche SET urteil='ja' WHERE id=1")
    with speicher.lesen(db2) as conn:
        assert pruefen(conn)["heil"] is False, "geaendertes Urteil blieb unbemerkt"

    # 4) Negativfall: eine unveraenderte Kette darf NICHT anschlagen, sonst
    #    waere der Melder wertlos.
    db3 = Path(tempfile.mkdtemp()) / "probe3.db"
    with speicher.schreiben(db3) as conn:
        for i in range(5):
            schreiben(conn, urteil=f"urteil-{i}", pruefer=f"p{i}",
                      auftraggeber="o", **gemeinsam)
    with speicher.lesen(db3) as conn:
        assert pruefen(conn)["heil"] is True and pruefen(conn)["zeilen"] == 5

    # 5) Selbstpruefung wird benannt, nicht verschwiegen.
    with speicher.schreiben(db3) as conn:
        s = schreiben(conn, urteil="alles gut", pruefer="orchestrator",
                      auftraggeber="orchestrator", **gemeinsam)
    assert s["eigenpruefung"] is True
    with speicher.lesen(db3) as conn:
        assert liste(conn)[-1]["eigenpruefung"] is True

    # 6) Ohne Begruendung kein Spruch.
    with speicher.schreiben(db3) as conn:
        try:
            schreiben(conn, frage="F", urteil="U", begruendung="  ",
                      pruefer="p", auftraggeber="o")
            raise AssertionError("Spruch ohne Begruendung wurde angenommen")
        except ValueError:
            pass

    print("selftest ok (6 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schreiben", action="store_true")
    p.add_argument("--frage"), p.add_argument("--urteil")
    p.add_argument("--begruendung"), p.add_argument("--pruefer")
    p.add_argument("--auftraggeber"), p.add_argument("--modell")
    p.add_argument("--sitzung")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.schreiben:
        with speicher.schreiben() as conn:
            e = schreiben(conn, frage=a.frage or "", urteil=a.urteil or "",
                          begruendung=a.begruendung or "", pruefer=a.pruefer or "",
                          auftraggeber=a.auftraggeber or "", modell=a.modell,
                          sitzung=a.sitzung)
        print(f"Spruch abgelegt, Kettenhash {e['ketten_hash'][:16]}...")
        if e["eigenpruefung"]:
            print("HINWEIS: pruefer und auftraggeber sind derselbe -- das ist "
                  "eine Selbstauskunft, keine zweite Stimme.")
        return

    if a.pruefen:
        with speicher.lesen() as conn:
            e = pruefen(conn)
        print(f"{e['zeilen']} Spruch/Sprueche -- {e['befund']}")
        sys.exit(0 if e["heil"] else 1)

    if a.liste:
        with speicher.lesen() as conn:
            for s in liste(conn):
                merker = "  [SELBSTAUSKUNFT]" if s["eigenpruefung"] else ""
                print(f"#{s['id']} {s['erstellt_am']} {s['pruefer']} "
                      f"(beauftragt von {s['auftraggeber']}){merker}")
                print(f"    Frage:   {s['frage']}")
                print(f"    Urteil:  {s['urteil']}")
                print(f"    Grund:   {s['begruendung'][:160]}")
        return

    p.print_help()


if __name__ == "__main__":
    main()
