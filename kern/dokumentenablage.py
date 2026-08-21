#!/usr/bin/env python3
"""Dokumentenablage: drei Schichten, und nur die mittlere geht in den Index.

ADR-032 (2026-08-21), Katalogzeile BDW-P15.

    | Schicht | Inhalt                                             | Index          |
    |---------|----------------------------------------------------|----------------|
    | Ablage  | die Datei selbst, unveraendert, mit Pruefsumme      | keiner         |
    | Knoten  | Verweis, Pruefsumme, Herkunft, Geltung, Kurzfassung | Arbeitsbestand |
    | Auszug  | eine einzelne belegte Stelle, mit Fundstelle        | Arbeitsbestand |

DER ORT IST EINE EINSTELLUNG JE DOMAENE, nicht je Haus:
`ablage.<domaene>` in knowledge_config -- `domaene` (Vorgabe, die Datei bleibt
wo sie ist) oder `brainlehr` (sie wandert in brainlehrs Ablage). Bauform
uebernommen von `mitstart.<domaene>` (ADR-023): Praefix + Domaenenname, weil
ein nackter Domaenenname in einem geteilten Schluesselraum eine Kollision
waere, die niemand bemerkt. Kein zweites Muster.

WAS DIE EINSTELLUNG NICHT ENTSCHEIDET: ob eine Pruefsumme gefuehrt wird. Die
wird IMMER gefuehrt, an beiden Orten -- durchgesetzt nicht hier im Python,
sondern als Trigger (`knowledge_nodes_dokument_quellhash_pflicht_bi/bu`,
schema.sql am Dateiende). Bauform von `norm_entscheidung` uebernommen: die
Pflicht gehoert in die Datenbank, weil MCP ueber stdio keinen zentralen
Neustart kennt und eine Codeaenderung laufende Sitzungen nie erreicht
(CLAUDE.md dieses Repos).

KEIN ZWEITER VEKTORRAUM (Konsil 2026-08-21, 2:1 gegen den Betreibervorschlag,
Nachtrag in ADR-032). Der Auszug liegt im vorhandenen Index.

KEINE VERSCHLUESSELUNG. `sensibel` ist fuer Dokumente Dritter das falsche
Werkzeug -- gemessen Rang 854/1130/2571 statt 1-3, und im Volltextindex steht
ein sensibler Knoten gar nicht (die FTS-Trigger haengen an `sensibel = 0`,
schema.sql). Geschuetzt wird ueber `mandant`/`kreis`
(kern/trennung.py::sichtbar_sql) oder ueber `freigabe`: Abfragefilter,
umkehrbar, und sie lassen den Kanal intakt, der Namen findet.

BETEILIGTE SIND GEGENSTAENDE, KEINE NAMEN IM TEXT (ADR-028). Ein Dokument hat
Aussteller, Empfaenger, Betroffene; sie werden ueber `gegenstand_bezug` mit
Rolle gebunden. Die Tabelle traegt das seit 5403a71b ohne jede Aenderung --
`rolle` ist Freitext mit genau diesen Beispielen im Schemakommentar
(`betrifft | verfasst_von | gerichtet_an`), `art` ebenso. Heute steht dort
keine Person; wenn Personen entstehen, entstehen sie hier.

Aufruf:
    python3 kern/dokumentenablage.py --selftest
    python3 kern/dokumentenablage.py --ort buckeberg
    python3 kern/dokumentenablage.py --ort buckeberg --setzen brainlehr
    python3 kern/dokumentenablage.py --pruefen        # der Waechter
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
while not (WURZEL / "schema.sql").exists() and WURZEL != WURZEL.parent:
    WURZEL = WURZEL.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern"), str(WURZEL / "haken")]

import gegenstand  # noqa: E402

ORT_DOMAENE = "domaene"
ORT_BRAINLEHR = "brainlehr"
ORTE = (ORT_DOMAENE, ORT_BRAINLEHR)

# Die Ablage, in die bei `= brainlehr` verschoben wird. Ueber die Umgebung
# uebersteuerbar und NICHT verdrahtet -- ein Selbsttest darf nicht in den
# Bestand des Hauses schreiben.
ENV_ABLAGE = "BRAINLEHR_ABLAGE"


def ablage_wurzel() -> Path:
    return Path(os.environ.get(ENV_ABLAGE) or (WURZEL / "ablage"))


# --------------------------------------------------------------- Pruefsumme

def pruefsumme(datei: Path | str) -> str:
    """sha256 der GANZEN Datei, blockweise -- eine PDF passt nicht sinnvoll in
    den Speicher, und sie hat auch keine '## '-Abschnitte, an denen sich der
    Abschnittshash aus normbestand.py orientiert."""
    h = hashlib.sha256()
    with open(datei, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------- Einstellung

def _schluessel(domaene: str) -> str:
    return f"ablage.{domaene}"


def ort(conn: sqlite3.Connection, domaene: str) -> str:
    """Vorgabe ist `domaene`, weil sie nichts bewegt -- und zwar auch dann,
    wenn zum Schluessel gar nichts gespeichert ist. Ein fehlender Schluessel
    ist hier keine Luecke, sondern die Entscheidung, nichts zu tun."""
    zeile = conn.execute("SELECT value FROM knowledge_config WHERE key = ?",
                         (_schluessel(domaene),)).fetchone()
    wert = (zeile[0] if zeile else None) or ORT_DOMAENE
    if wert not in ORTE:
        raise ValueError(f"ablage.{domaene} = {wert!r} -- erlaubt sind {ORTE}")
    return wert


def ort_setzen(conn: sqlite3.Connection, domaene: str, wert: str, *, ts: str) -> None:
    if wert not in ORTE:
        raise ValueError(f"ablage.{domaene} = {wert!r} -- erlaubt sind {ORTE}")
    conn.execute(
        "INSERT INTO knowledge_config (key, value, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (_schluessel(domaene), wert, ts))


# ------------------------------------------------------------------ Ablegen

def _knoten_id(pfad: str) -> str:
    return hashlib.sha1(pfad.encode("utf-8")).hexdigest()[:8]


def _geltung(gilt_ab: str | None, gilt_bis: str | None) -> tuple[str, int | None]:
    """Geltung eines Dokuments in die vorhandene Norm-Achse uebersetzt --
    statt einer zwoelften Spalte daneben.

    Die drei Trigger, die das erzwingen, widersprechen sich nicht, sie
    verzahnen sich: `keine_norm` verlangt norm_rang UND gilt_ab leer,
    `norm_befristet` verlangt gilt_bis gesetzt, `norm_unbefristet` verlangt es
    leer, und ein gesetzter norm_rang verlangt gilt_ab. Rang 4 (nicht 1/2):
    ein Vertrag ist keine Hausnorm, und Rang 1/2 verlangte zusaetzlich einen
    menschlichen Entscheider samt Belegart."""
    if gilt_ab is None:
        if gilt_bis is not None:
            raise ValueError("gilt_bis ohne gilt_ab -- ab wann gilt das Dokument?")
        return "keine_norm", None
    return ("norm_befristet" if gilt_bis else "norm_unbefristet"), 4


def ablegen(conn: sqlite3.Connection, datei: Path | str, *, domaene: str,
            titel: str, zusammenfassung: str, herkunft: str, ts: str,
            knotenpfad: str | None = None,
            gilt_ab: str | None = None, gilt_bis: str | None = None,
            mandant: str = "lokal", kreis: str = "",
            freigabe: str = "intern",
            beteiligte: list[dict] | tuple = (),
            actor: str = "skript:kern/dokumentenablage.py") -> dict:
    """Legt EIN Dokument ab und gibt zurueck, was daraus geworden ist.

    Der Ort entscheidet nur ueber die Datei, nie ueber den Knoten: in beiden
    Stellungen entsteht derselbe Knoten mit derselben Pflicht-Pruefsumme.
    `dokument_pfad` zeigt danach auf den HEUTIGEN Ort -- eine Spalte, keine
    zwei, sonst altern zwei Wahrheiten nebeneinander.
    """
    quelle = Path(datei).resolve()
    if not quelle.is_file():
        raise FileNotFoundError(f"{quelle} ist keine Datei")

    stellung = ort(conn, domaene)
    hash_vorher = pruefsumme(quelle)

    ziel = quelle
    if stellung == ORT_BRAINLEHR:
        ordner = ablage_wurzel() / domaene
        ordner.mkdir(parents=True, exist_ok=True)
        ziel = ordner / f"{hash_vorher[:12]}-{quelle.name}"
        if ziel.resolve() != quelle:
            shutil.move(str(quelle), str(ziel))
        ziel = ziel.resolve()
        # Nach dem Umzug erneut rechnen statt den Wert von vorher zu glauben:
        # ein Umzug, der die Datei beschaedigt, faellt sonst erst dem Waechter
        # auf -- und der prueft gegen genau diesen Wert.
        if pruefsumme(ziel) != hash_vorher:
            raise OSError(f"Umzug hat {quelle.name} veraendert -- Ablage abgebrochen")

    pfad = knotenpfad or f"/dokumente/{domaene}/{_slug(quelle.name)}"
    entscheidung, rang = _geltung(gilt_ab, gilt_bis)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level,"
        " source, created_at, updated_at, quell_hash, dokument_pfad, anlass, actor,"
        " norm_entscheidung, norm_entschieden_von, norm_entschieden_grund,"
        " norm_rang, gilt_ab, gilt_bis, gattung, freigabe, mandant, kreis)"
        " VALUES (?,?,?,?,?,1,?,?,?,?,?, 'skript',?, ?,?,?, ?,?,?, 'arbeitsbestand',?,?,?)",
        (_knoten_id(pfad), pfad, domaene, titel, zusammenfassung, herkunft, ts, ts,
         hash_vorher, str(ziel), actor,
         entscheidung, actor, f"Dokumentenablage {domaene} (ADR-032/BDW-P15)",
         rang, gilt_ab, gilt_bis, freigabe, mandant, kreis))

    gegenstand.ensure_schema(conn)
    gebunden = []
    for b in beteiligte:
        gid = _gegenstand_id(conn, b["art"], b["name"], beleg=herkunft, ts=ts)
        gegenstand.bezug_setzen(conn, pfad, gid, beleg=herkunft, ts=ts,
                                rolle=b.get("rolle", "betrifft"))
        gebunden.append({"gegenstand_id": gid, "name": b["name"],
                         "art": b["art"], "rolle": b.get("rolle", "betrifft")})

    return {"knoten": pfad, "ort": stellung, "datei": str(ziel),
            "quell_hash": hash_vorher, "beteiligte": gebunden}


def _slug(name: str) -> str:
    roh = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        roh = roh.replace(a, b)
    return "".join(c if c.isalnum() else "-" for c in roh).strip("-")


def _gegenstand_id(conn: sqlite3.Connection, art: str, name: str, *,
                   beleg: str, ts: str) -> str:
    """Vorhandenen Gegenstand wiederverwenden, sonst anlegen. Ein
    MEHRDEUTIGER Name wird durchgereicht und nicht aufgeloest -- genau dafuer
    gibt es die Ausnahme (kern/gegenstand.py: "drei Sprints heissen S12, und
    die richtige Antwort darauf ist eine Auskunft ueber drei Kandidaten,
    keine Auswahl")."""
    try:
        return gegenstand.aufloesen_eindeutig(conn, name, ts)["id"]
    except gegenstand.UnbekannterName:
        return gegenstand.anlegen(conn, art, name, beleg=beleg, ts=ts)


# ------------------------------------------------------------------- Auszug

def auszug(conn: sqlite3.Connection, dokument_knoten: str, *, titel: str,
           text: str, fundstelle: str, ts: str,
           actor: str = "skript:kern/dokumentenablage.py") -> str:
    """Eine EINZELNE belegte Stelle. Erbt Datei, Pruefsumme und Trennung vom
    Dokumentknoten -- ein Auszug, der seine eigene Sichtbarkeit mitbraechte,
    waere eine zweite Wahrheit ueber dieselbe Datei."""
    d = conn.execute(
        "SELECT project_id, dokument_pfad, quell_hash, mandant, kreis, freigabe"
        " FROM knowledge_nodes WHERE path = ?", (dokument_knoten,)).fetchone()
    if d is None:
        raise LookupError(f"kein Dokumentknoten unter {dokument_knoten}")
    projekt, datei, qhash, mandant, kreis, freigabe = tuple(d)
    if not datei:
        raise ValueError(f"{dokument_knoten} ist kein Dokumentknoten (dokument_pfad leer)")

    pfad = f"{dokument_knoten}/{_slug(fundstelle)}"
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary,"
        " content, level, source, created_at, updated_at, quell_hash, dokument_pfad,"
        " anlass, actor, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund,"
        " gattung, freigabe, mandant, kreis)"
        " VALUES (?,?,?,?,?,?,?,2,?,?,?,?,?, 'skript',?, 'keine_norm',?,?,"
        " 'arbeitsbestand',?,?,?)",
        (_knoten_id(pfad), pfad, dokument_knoten, projekt, titel, text[:400],
         text, f"Auszug aus {datei}, {fundstelle}", ts, ts, qhash, datei, actor,
         actor, f"Auszug mit Fundstelle (ADR-032/BDW-P15): {fundstelle}",
         freigabe, mandant, kreis))
    return pfad


# ------------------------------------------------------------------ Waechter

def pruefen(conn: sqlite3.Connection) -> list[dict]:
    """Meldet Dokumente, deren Datei nicht mehr zur Pruefsumme passt.

    Gibt eine LEERE Liste zurueck, wenn nichts auseinandergelaufen ist. Das
    ist die halbe Zusicherung und nicht die Nebensache: ein Waechter, der
    immer anschlaegt, wird weggeklickt.

    Zwei Befundarten, weil sie verschiedene Antworten verlangen: `fehlt`
    (Datei weg -- Verweis ins Leere) und `geaendert` (Datei da, Inhalt
    anders). Ein unbemerkter Auseinanderlauf ist schlimmer als gar keine
    Pruefsumme, weil er Sicherheit vortaeuscht (ADR-032, "Was das kostet").

    ponytail: Diese Funktion haengt an keinem Ereignis -- sie laeuft nur
    ueber `--pruefen`. Ein Mechanismus, der nirgends haengt, zaehlt als
    keiner (CLAUDE.md, gemessen 2026-08-20). Die Verdrahtung gehoert nach
    melder/ bzw. in die SOLLEN_LAUFEN-Liste und damit in einen Auftrag,
    der melder/ besitzt -- dieser hier tut es ausdruecklich nicht.
    """
    befunde = []
    gesehen: dict[str, str] = {}
    for pfad, datei, qhash in conn.execute(
            "SELECT path, dokument_pfad, quell_hash FROM knowledge_nodes"
            " WHERE dokument_pfad IS NOT NULL AND TRIM(dokument_pfad) <> ''"
            " ORDER BY path"):
        p = Path(datei)
        if not p.is_file():
            befunde.append({"knoten": pfad, "datei": datei, "befund": "fehlt"})
            continue
        ist = gesehen.get(datei) or pruefsumme(p)
        gesehen[datei] = ist
        if ist != qhash:
            befunde.append({"knoten": pfad, "datei": datei, "befund": "geaendert",
                            "erwartet": qhash, "ist": ist})
    return befunde


# ------------------------------------------------------------------ Selbsttest

def _kulisse(tmp: Path) -> sqlite3.Connection:
    """Frisch aus schema.sql -- Trigger UND Indizes inhaltsbestimmt, nicht
    nachgebaut (L-e12296). Der gewachsene Fall steht in
    tests/test_dokumentenablage.py."""
    conn = sqlite3.connect(":memory:")   # Testkulisse, keine Tuer zum Bestand
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _selftest() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    os.environ[ENV_ABLAGE] = str(tmp / "ablage")
    conn = _kulisse(tmp)
    ts = "2026-08-21T12:00:00+0200"

    quelle = tmp / "vertrag.txt"
    quelle.write_text("Verwaltervertrag\nGrundverguetung 50,00 EUR\n", encoding="utf-8")

    # Vorgabe ist `domaene` -- ohne jede Zeile in knowledge_config.
    assert ort(conn, "buckeberg") == ORT_DOMAENE

    r = ablegen(conn, quelle, domaene="buckeberg", titel="Verwaltervertrag",
                zusammenfassung="Grundverguetung und Laufzeit der Verwaltung",
                herkunft="Ablage buckeberg, Handprobe", ts=ts,
                beteiligte=[{"art": "person", "name": "Doeldissen",
                             "rolle": "verfasst_von"}])
    assert r["ort"] == ORT_DOMAENE
    assert Path(r["datei"]) == quelle.resolve(), "Vorgabe hat die Datei bewegt"
    assert r["beteiligte"][0]["rolle"] == "verfasst_von"

    # Findbarkeit ueber die ZUSAMMENFASSUNG (BDW-P15-AC1), nicht ueber den Titel.
    treffer = conn.execute(
        "SELECT path FROM knowledge_fts WHERE knowledge_fts MATCH ?",
        ('"grundverguetung"',)).fetchall()
    assert any(t[0].startswith("/dokumente/buckeberg/") for t in treffer), treffer

    # Negativfall: Verweis ohne Pruefsumme -> abgewiesen, und zwar vom TRIGGER.
    try:
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level,"
            " source, created_at, updated_at, dokument_pfad, norm_entscheidung,"
            " norm_entschieden_von, norm_entschieden_grund)"
            " VALUES ('x1','/dokumente/x','p','t','s',1,'h',?,?,?,'keine_norm','x','y')",
            (ts, ts, str(quelle)))
        raise AssertionError("Dokumentknoten ohne quell_hash wurde angenommen")
    except sqlite3.IntegrityError as exc:
        assert "quell_hash fehlt" in str(exc), exc

    # Waechter: unveraendert -> schweigt.
    assert pruefen(conn) == [], pruefen(conn)
    # ... veraendert -> meldet.
    quelle.write_text("Verwaltervertrag\nGrundverguetung 60,00 EUR\n", encoding="utf-8")
    b = pruefen(conn)
    assert len(b) == 1 and b[0]["befund"] == "geaendert", b
    # ... weg -> meldet anders.
    quelle.unlink()
    assert pruefen(conn)[0]["befund"] == "fehlt"

    # Zweite Stellung: dieselbe Datei, anderer Ort, gleiche Pflicht.
    zweite = tmp / "protokoll.txt"
    zweite.write_text("Eigentuemerversammlung 2026\nBeschluss ueber die Dachsanierung\n",
                      encoding="utf-8")
    ort_setzen(conn, "buckeberg", ORT_BRAINLEHR, ts=ts)
    assert ort(conn, "buckeberg") == ORT_BRAINLEHR
    r2 = ablegen(conn, zweite, domaene="buckeberg", titel="Protokoll 2026",
                 zusammenfassung="Beschluss ueber die Dachsanierung",
                 herkunft="Ablage buckeberg, Handprobe", ts=ts)
    assert r2["ort"] == ORT_BRAINLEHR
    assert not zweite.exists(), "bei = brainlehr muss die Datei wandern"
    assert Path(r2["datei"]).is_file()
    assert str(ablage_wurzel()) in r2["datei"], r2["datei"]
    treffer2 = conn.execute(
        "SELECT path FROM knowledge_fts WHERE knowledge_fts MATCH ?",
        ('"dachsanierung"',)).fetchall()
    assert any(t[0] == r2["knoten"] for t in treffer2), treffer2

    # Auszug erbt Datei und Pruefsumme.
    a = auszug(conn, r2["knoten"], titel="Dachsanierung beschlossen",
               text="Die Versammlung beschliesst die Dachsanierung einstimmig.",
               fundstelle="Seite 2, TOP 4", ts=ts)
    zeile = conn.execute("SELECT dokument_pfad, quell_hash, parent_path"
                         " FROM knowledge_nodes WHERE path = ?", (a,)).fetchone()
    assert zeile[0] == r2["datei"] and zeile[1] == r2["quell_hash"]
    assert zeile[2] == r2["knoten"]

    conn.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest ok")
    return 0


def main() -> int:
    import speicher  # noqa: E402 -- nur der CLI-Zweig braucht den Bestand

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--ort", metavar="DOMAENE")
    p.add_argument("--setzen", choices=ORTE)
    p.add_argument("--pruefen", action="store_true")
    args = p.parse_args()

    if args.selftest:
        return _selftest()
    if args.pruefen:
        with speicher.lesen() as conn:
            befunde = pruefen(conn)
        print(json.dumps(befunde, ensure_ascii=False, indent=2))
        return 1 if befunde else 0
    if args.ort and args.setzen:
        from datetime import datetime, timezone
        with speicher.schreiben() as conn:
            # UTC mit 'Z', kein lokaler Versatz (tests/test_zeitform_utc.py) --
            # frueher stand hier lokale Zeit + %z, gemessen 2026-08-21 als
            # knowledge_config.updated_at-Verstoss aufgefallen.
            ort_setzen(conn, args.ort, args.setzen,
                       ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        print(f"ablage.{args.ort} = {args.setzen}")
        return 0
    if args.ort:
        with speicher.lesen() as conn:
            print(f"ablage.{args.ort} = {ort(conn, args.ort)}")
        return 0
    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
