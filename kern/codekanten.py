#!/usr/bin/env python3
"""Welche Datei betrifft diese Lehre — und was weiss der Speicher ueber diese Datei?

ZWECK: Ein zweiter Weg ins Wissen, der NICHT raet. Der Abruf sucht nach
Aehnlichkeit und hat dabei eine gemessene Schwaeche (2026-08-11: 15 von 35
Faellen, Deckel 10/7, und 18 Prozent der Nachrichten erreichen den Haltepunkt
gar nicht). Ein Dateipfad dagegen ist ein exakter Schluessel: Wissen zu
`features/obd/data/ble_trip_trigger.dart` ist da oder nicht -- keine
Trefferquote, kein Deckel, keine Rangfolge.

DATENLAGE, gemessen 2026-08-11: 456 von 763 Lehren (60 Prozent) und 255 von
2102 Knoten nennen einen Dateinamen im Klartext. Der Schluessel liegt also
bereits im Bestand; er ist nur nicht adressierbar.

WARUM EINE EIGENE TABELLE und nicht knowledge_relations: dort verlangen beide
Enden einen bestehenden Knoten (FOREIGN KEY auf knowledge_nodes.path). Eine
Datei zum Knoten zu machen, waere Code im Trefferpool -- genau das, wogegen
am selben Tag gemessen wurde: sobald eine grosse Gattung um dieselben Plaetze
konkurriert, verschwindet die kleinere vollstaendig (Lehren fielen von 9 auf 0
Treffer). Die Datei bleibt draussen; nur die Kante wird gespeichert.

AUFLOESUNG STATT VERTRAUEN: Ein aus Text geklaubter Dateiname ist ein
KANDIDAT, keine Tatsache. Gespeichert wird nur, was sich im Verbund auf eine
existierende Datei aufloesen laesst. Damit filtert die Wirklichkeit den
regulaeren Ausdruck -- und was sich NICHT aufloest, ist selbst ein Befund:
entweder Rauschen des Musters oder eine Datei, die es nicht mehr gibt (dann
zeigt die Lehre auf etwas Verschwundenes und ist zu pruefen).

Mehrdeutigkeit wird NICHT stillschweigend aufgeloest: `ort.py` gibt es
mehrfach im Verbund. Solche Kandidaten werden mit allen Fundstellen und einem
Merker gespeichert, nicht auf die erstbeste geraten.

Aufruf:
    python3 codekanten.py --bauen          # Kanten erheben und ablegen
    python3 codekanten.py --zu <pfad>      # was weiss der Speicher ueber diese Datei
    python3 codekanten.py --bericht        # Zahlen und nicht aufloesbare Kandidaten
    python3 codekanten.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
ROOT = WURZEL.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(ROOT / "haken"))

import ort  # noqa: E402
import speicher  # noqa: E402

VERBUND = ort.VERBUND
ENDUNGEN = ("py", "dart", "sh", "sql", "yaml", "yml", "json", "md", "ts", "js", "swift", "kt")
# Kandidat: optional Verzeichnisteile, dann name.endung. Mindestens drei
# Zeichen im Namen -- '/.py' und 'a.py' sind Rauschen, das die erste Fassung
# noch mitgenommen hat (gemessen: '/.py' und '/STAND.md' unter den Funden).
_KANDIDAT = re.compile(
    r"(?:[\w.\-]+/)*[\w\-]{3,}\.(?:" + "|".join(ENDUNGEN) + r")\b")
_AUSGENOMMEN = {".git", "node_modules", "build", ".dart_tool", "__pycache__", "Pods",
                "archive", ".pytest_cache", "vendor", "Carthage"}
# Wurzeln, die KOPIEN des Verbunds enthalten -- gemessen 2026-08-11: 'ort.py'
# lag fuenfmal vor, viermal davon in _probe_*/_brainlehr_open/_repos. Ohne
# diesen Schnitt sind 95 Prozent aller Kanten mehrdeutig und damit wertlos.
_KOPIEN = ("_", "archive")
# Mehr als so viele Fundstellen: der Kandidat ist keine Adresse, sondern ein
# Wort. 'README.md' kommt 1940-mal vor, '__init__.py' 5933-mal. Solche Namen
# ergeben keine Kante, sie ergeben Rauschen -- sie werden gezaehlt, nicht
# gespeichert.
MAX_FUNDSTELLEN = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS code_kanten (
    id            TEXT PRIMARY KEY,
    quelle_art    TEXT NOT NULL CHECK(quelle_art IN ('lehre','knoten')),
    quelle_id     TEXT NOT NULL,
    kandidat      TEXT NOT NULL,
    pfad          TEXT NOT NULL,
    mehrdeutig    INTEGER NOT NULL DEFAULT 0,
    erhoben_am    TEXT NOT NULL,
    UNIQUE(quelle_art, quelle_id, pfad)
);
CREATE INDEX IF NOT EXISTS code_kanten_pfad ON code_kanten(pfad);
"""


# Zweite Wurzel: die Hauswerkzeuge liegen NICHT im Verbund, sondern unter
# ~/.claude (Faehigkeiten, Haken, Einstellungen). Gemessen 2026-08-11: von den
# 106 angeblich toten Verweisen war ui_guard.py keiner -- die Datei existiert,
# nur eben dort. Ein Index, der die Wurzel des Werkzeugkastens auslaesst,
# erklaert fremde Wirklichkeit fuer verschwunden.
ZWEITE_WURZEL = Path.home() / ".claude"


def dateiindex(wurzel: Path = VERBUND,
               wurzeln: list[Path] | None = None) -> dict[str, list[str]]:
    """Basisname -> alle Pfade. Arbeitsbaeume (.claude/worktrees/) werden
    uebersprungen: dieselbe Datei laege sonst dutzendfach vor und jede Kante
    waere mehrdeutig, ohne dass es einen Unterschied machte. Der Rest von
    .claude/ zaehlt aber sehr wohl -- dort stehen die Werkzeuge."""
    index: dict[str, list[str]] = defaultdict(list)
    for w in (wurzeln if wurzeln is not None else [wurzel]):
        if not w.exists():
            continue
        for pfad in w.rglob("*"):
            if not pfad.is_file() or pfad.suffix.lstrip(".") not in ENDUNGEN:
                continue
            teile = pfad.parts
            if set(teile) & _AUSGENOMMEN or "worktrees" in teile:
                continue
            rel = pfad.relative_to(w)
            if rel.parts and rel.parts[0].startswith(_KOPIEN):
                continue
            index[pfad.name].append(str(rel if w == wurzel else Path("~/.claude") / rel))
    return dict(index)


def kandidaten(text: str) -> set[str]:
    return set(_KANDIDAT.findall(text or ""))


def aufloesen(kandidat: str, index: dict[str, list[str]],
              projekte: list[str] | None = None) -> list[str]:
    """Kandidat -> tatsaechliche Pfade. Mehrere Treffer werden ueber die
    Projektangabe der Quelle eingegrenzt, wenn das eindeutig macht; sonst
    bleiben alle stehen und die Kante gilt als mehrdeutig."""
    treffer = index.get(Path(kandidat).name, [])
    if len(treffer) > 1 and kandidat.count("/"):
        genauer = [t for t in treffer if t.endswith(kandidat)]
        if genauer:
            treffer = genauer
    if len(treffer) > 1 and projekte:
        gefiltert = [t for t in treffer if any(p and t.startswith(p) for p in projekte)]
        if gefiltert:
            treffer = gefiltert
    # Bleibt es breit, ist der Kandidat kein Verweis auf eine Datei, sondern
    # ein gaengiger Name im Fliesstext. Lieber keine Kante als zwanzig falsche.
    # Der Aufrufer unterscheidet das an der Rueckgabe: leere Liste bei zu
    # vielen Fundstellen, None wenn es die Datei gar nicht gibt. Beides ergibt
    # keine Kante, bedeutet aber Verschiedenes -- 'knowledge_mcp_server.py'
    # existiert (16-mal), 'oem_odometer_probe_screen.dart' nicht mehr.
    if len(treffer) > MAX_FUNDSTELLEN:
        return []
    return treffer or None


def erheben(index: dict[str, list[str]], conn: sqlite3.Connection) -> dict:
    """Liest Lehren und Knoten, klaubt Kandidaten, loest sie auf. Gibt Kanten
    und die NICHT aufgeloesten Kandidaten zurueck -- beides ist ein Ergebnis."""
    kanten: list[dict] = []
    offen: dict[str, list[str]] = defaultdict(list)      # Datei gibt es nicht
    zu_haeufig: dict[str, list[str]] = defaultdict(list)  # Name ist keine Adresse

    quellen = [
        ("lehre", "SELECT id, projects, description, root_cause, resolution, prevention "
                  "FROM lessons_learned WHERE status='active'"),
        ("knoten", "SELECT path AS id, project_id AS projects, title, summary, content "
                   "FROM knowledge_nodes WHERE zurueckgezogen=0"),
    ]
    for art, sql in quellen:
        for zeile in conn.execute(sql):
            felder = dict(zeile)
            quelle_id = felder.pop("id")
            roh = felder.pop("projects", None)
            try:
                projekte = json.loads(roh) if roh and roh.startswith("[") else ([roh] if roh else [])
            except (json.JSONDecodeError, AttributeError):
                projekte = [roh] if roh else []
            text = " ".join(str(v or "") for v in felder.values())
            for kand in kandidaten(text):
                pfade = aufloesen(kand, index, projekte)
                if pfade is None:
                    offen[kand].append(f"{art}:{quelle_id}")
                    continue
                if not pfade:
                    zu_haeufig[kand].append(f"{art}:{quelle_id}")
                    continue
                for p in pfade:
                    kanten.append({"quelle_art": art, "quelle_id": quelle_id,
                                    "kandidat": kand, "pfad": p,
                                    "mehrdeutig": int(len(pfade) > 1)})
    return {"kanten": kanten, "nicht_aufgeloest": dict(offen),
            "zu_haeufig": dict(zu_haeufig)}


def ablegen(kanten: list[dict], conn: sqlite3.Connection, jetzt: str) -> int:
    conn.executescript(SCHEMA)
    n = 0
    for k in kanten:
        kennung = f"ck-{abs(hash((k['quelle_art'], k['quelle_id'], k['pfad']))):012x}"
        conn.execute(
            "INSERT OR IGNORE INTO code_kanten "
            "(id, quelle_art, quelle_id, kandidat, pfad, mehrdeutig, erhoben_am) "
            "VALUES (?,?,?,?,?,?,?)",
            (kennung, k["quelle_art"], k["quelle_id"], k["kandidat"], k["pfad"],
             k["mehrdeutig"], jetzt))
        n += 1
    return n


def wissen_zu(pfad: str, conn: sqlite3.Connection) -> list[dict]:
    """Die Frage, fuer die das Ganze gebaut ist -- und sie kennt keine
    Trefferquote. Sucht auch mit Teilpfad (eine Station der Flusskarte nennt
    'features/obd/data/ble_trip_trigger.dart', die Kante traegt den vollen
    Pfad ab der Verbundwurzel)."""
    zeilen = conn.execute(
        "SELECT quelle_art, quelle_id, pfad, mehrdeutig FROM code_kanten "
        "WHERE pfad = ? OR pfad LIKE '%' || ? ORDER BY quelle_art, quelle_id",
        (pfad, pfad)).fetchall()
    return [dict(z) for z in zeilen]


def _selftest() -> None:
    import tempfile
    from datetime import datetime

    tmp = Path(tempfile.mkdtemp())
    (tmp / "app" / "lib").mkdir(parents=True)
    (tmp / "app" / "lib" / "trip_service.dart").write_text("x")
    (tmp / "app" / "lib" / "ort.py").write_text("x")
    (tmp / "zweit").mkdir()
    (tmp / "zweit" / "ort.py").write_text("x")
    (tmp / ".claude" / "worktrees" / "kopie").mkdir(parents=True)
    (tmp / ".claude" / "worktrees" / "kopie" / "trip_service.dart").write_text("x")
    (tmp / ".claude" / "skills").mkdir(parents=True)
    (tmp / ".claude" / "skills" / "waechter.py").write_text("x")

    index = dateiindex(tmp)
    assert "trip_service.dart" in index and len(index["trip_service.dart"]) == 1, \
        "Arbeitsbaeume unter .claude/worktrees/ duerfen nicht mitgezaehlt werden"
    # Gegenprobe zur Korrektur vom 2026-08-11: der REST von .claude/ zaehlt,
    # dort liegen die Werkzeuge. Vorher fielen sie mit den Arbeitsbaeumen
    # zusammen heraus und galten als verschwunden.
    assert "waechter.py" in index, "Werkzeuge unter .claude/ fehlen im Index"
    assert len(index["ort.py"]) == 2

    # 1) Kandidaten klauben: Rauschen faellt raus.
    k = kandidaten("siehe lib/trip_service.dart und ort.py, aber nicht /.py oder a.py")
    assert "lib/trip_service.dart" in k and "ort.py" in k, k
    assert not any(x.endswith("/.py") or x == "a.py" for x in k), k

    # 2) Aufloesung an der Wirklichkeit: erfundene Datei wird NICHT gespeichert.
    assert aufloesen("gibtsnicht.dart", index) is None, "fehlende Datei muss None ergeben"
    assert aufloesen("lib/trip_service.dart", index) == ["app/lib/trip_service.dart"]

    # 3) Mehrdeutigkeit wird nicht geraten -- beide bleiben stehen.
    assert len(aufloesen("ort.py", index)) == 2
    # ... aber die Projektangabe grenzt ein, wenn sie eindeutig macht.
    assert aufloesen("ort.py", index, ["zweit"]) == ["zweit/ort.py"]

    # 4) Ablegen und wiederfinden, auch ueber den Teilpfad einer Flusskarte.
    db = tmp / "probe.db"
    with speicher.schreiben(db) as conn:
        ablegen([{"quelle_art": "lehre", "quelle_id": "L-1",
                  "kandidat": "lib/trip_service.dart",
                  "pfad": "app/lib/trip_service.dart", "mehrdeutig": 0}],
                conn, datetime(2026, 8, 11).isoformat())
    with speicher.lesen(db) as conn:
        assert len(wissen_zu("app/lib/trip_service.dart", conn)) == 1
        assert len(wissen_zu("lib/trip_service.dart", conn)) == 1, \
            "Teilpfad-Suche fehlt -- Flusskarten nennen nicht den vollen Pfad"
        assert wissen_zu("app/lib/anderes.dart", conn) == []

    # 5) Gegenprobe zur Ablage: zweimal dasselbe erzeugt EINE Kante.
    with speicher.schreiben(db) as conn:
        ablegen([{"quelle_art": "lehre", "quelle_id": "L-1",
                  "kandidat": "lib/trip_service.dart",
                  "pfad": "app/lib/trip_service.dart", "mehrdeutig": 0}],
                conn, datetime(2026, 8, 11).isoformat())
    with speicher.lesen(db) as conn:
        assert len(wissen_zu("app/lib/trip_service.dart", conn)) == 1, "Dublette angelegt"

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    from datetime import datetime, timedelta, timezone

    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bauen", action="store_true")
    p.add_argument("--zu", metavar="PFAD")
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.zu:
        with speicher.lesen() as conn:
            treffer = wissen_zu(a.zu, conn)
        if not treffer:
            print(f"Kein Wissen zu {a.zu}")
            return
        print(f"{len(treffer)} Eintrag/Eintraege zu {a.zu}:")
        for t in treffer:
            merker = " (mehrdeutig)" if t["mehrdeutig"] else ""
            print(f"  {t['quelle_art']:7s} {t['quelle_id']}{merker}")
        return

    if a.bauen or a.bericht:
        print("Dateiindex wird gebaut ...", flush=True)
        index = dateiindex(wurzeln=[VERBUND, ZWEITE_WURZEL])
        print(f"  {sum(len(v) for v in index.values())} Dateien, "
              f"{len(index)} verschiedene Namen", flush=True)
        with speicher.lesen() as conn:
            ergebnis = erheben(index, conn)
        kanten = ergebnis["kanten"]
        quellen = {(k["quelle_art"], k["quelle_id"]) for k in kanten}
        print(f"  {len(kanten)} Kanten aus {len(quellen)} Eintraegen")
        print(f"  davon mehrdeutig: {sum(1 for k in kanten if k['mehrdeutig'])}")
        print(f"  Kandidaten OHNE Datei im Verbund (tote Verweise oder Rauschen): "
              f"{len(ergebnis['nicht_aufgeloest'])}")
        print(f"  Kandidaten ZU HAEUFIG (Name existiert, ist aber keine Adresse): "
              f"{len(ergebnis['zu_haeufig'])}")
        for kand, wo in sorted(ergebnis["nicht_aufgeloest"].items(),
                                key=lambda x: -len(x[1]))[:8]:
            print(f"    {kand:44s} genannt in {len(wo)}")
        if a.bauen:
            jetzt = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%dT%H:%M:%S%z")
            with speicher.schreiben() as conn:
                n = ablegen(kanten, conn, jetzt)
            print(f"\nAbgelegt: {n} Kanten in code_kanten")
        if a.out:
            a.out.write_text(json.dumps(
                {"kanten": len(kanten), "quellen": len(quellen),
                 "mehrdeutig": sum(1 for k in kanten if k["mehrdeutig"]),
                 "nicht_aufgeloest": ergebnis["nicht_aufgeloest"]},
                ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Geschrieben: {a.out}")
        return

    p.print_help()


if __name__ == "__main__":
    main()
