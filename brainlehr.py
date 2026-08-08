#!/usr/bin/env python3
"""brainlehr — ein Ort anlegen, den Bestand herausschreiben, ihn wieder einlesen.

Drei Verben, ein Einstiegspunkt (Plan hub/docs/PLAN_BRAINLEHR_EIGENSTAENDIG_2026-08-08.md,
Schritte S2 und S3):

    python3 brainlehr.py init  <zielverzeichnis>
    python3 brainlehr.py raus  <auszug.jsonl> [--db <quelle.db>]
    python3 brainlehr.py rein  <auszug.jsonl>  --db <ziel.db>

WARUM ZEILENWEISE UND NICHT DIE DATEI KOPIEREN: eine SQLite-Datei laesst sich
nicht zusammenfuehren, git ueberschreibt sie. Zeilen lassen sich vergleichen,
zusammenfuehren und lesen. Der Auszug ist zugleich die Vorstufe zu C1 des
Dienst-Plans (anhaengendes Protokoll als Wahrheit, Datenbank als Ableitung).

WAS MITGEHT UND WARUM:
  knowledge_nodes, lessons_learned   der Bestand selbst
  knowledge_relations                Kanten zwischen Aussagen
  knowledge_config                   Betriebsentscheidungen (z.B. herkunftsmodus)
  access_log                         Nachpruefbarkeit -- wer hat wann was gelesen
                                     und geschrieben. Ohne sie ist der Bestand da,
                                     seine Geschichte nicht.
  eskalation_historie/-vorschlag     welche Lehre wann zur Regel wurde

WAS NICHT MITGEHT UND WARUM:
  knowledge_embeddings   ableitbar. Neu rechnen ist ehrlicher als mitschleppen --
                         ein Vektor aus einem anderen Modell waere still falsch.
                         Preis: die Bedeutungssuche ist nach dem Umzug schwaecher,
                         bis build_embeddings.py gelaufen ist.
  *_fts                  ableitbar, wird von den Triggern beim Einlesen gefuellt.
  lost_and_found         KEIN Bestand, sondern der Rohauswurf von `.recover` aus der
                         Bergung vom 2026-08-07 (L-84869f): Seitennummern und
                         namenlose Spalten c0..c28. Beim ersten Entwurf dieses
                         Werkzeugs faelschlich als "wiedergefundene Waisen" in den
                         Auszug genommen -- nachgesehen, es sind keine.
  mycel_*                Ableitung eines Analyseskripts, jederzeit neu erzeugbar.

DER EINE SONDERWEG, ausdruecklich benannt statt versteckt: 1919 von 1989 Knoten
tragen norm_entscheidung='offen' -- der Zustand des Altbestands, den die Regel vom
2026-08-08 bewusst NICHT rueckwirkend erzwingt. Der Pflicht-Trigger weist genau
diesen Wert beim Anlegen ab, also liesse sich der Bestand ohne Weiteres nirgends
wieder einlesen. `rein` nimmt den Pflicht-Trigger fuer die Dauer des Einlesens
heraus und stellt ihn danach ueber ensure_schema() wieder her; zum Schluss wird
die Trigger-Menge gegen die der Quelle geprueft. Die Alternative waere gewesen,
'offen' beim Import auf 'keine_norm' umzubiegen -- das haette behauptet, jemand
haette entschieden. Eine Geschichte zu faelschen ist schlimmer als einen Trigger
sichtbar und geprueft kurz beiseitezunehmen.
"""
from __future__ import annotations

import argparse
import base64
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import knowledge_mcp_server as kms  # noqa: E402

TABELLEN = (
    "knowledge_nodes",
    "lessons_learned",
    "knowledge_relations",
    "knowledge_config",
    "access_log",
    "eskalation_historie",
    "eskalation_vorschlag",
)

# Nur dieser eine Trigger steht dem Wiedereinlesen des Altbestands im Weg
# (siehe Modulkopf). Bewusst namentlich, nicht per Muster -- ein Muster wuerde
# beim naechsten neuen Trigger stillschweigend mehr abschalten.
PFLICHT_TRIGGER = ("knowledge_nodes_norm_entscheidung_pflicht_bi",)


def _wert_raus(v):
    """SQLite kennt BLOBs (z.B. in lost_and_found), JSON nicht. Base64 mit
    Markierung, damit das Einlesen den Unterschied zu einem echten String
    sieht -- ein blosser Base64-String waere beim Rueckweg nicht mehr von
    Text zu unterscheiden."""
    return {"__blob__": base64.b64encode(v).decode("ascii")} if isinstance(v, bytes) else v


def _wert_rein(v):
    if isinstance(v, dict) and set(v) == {"__blob__"}:
        return base64.b64decode(v["__blob__"])
    return v


def _jetzt() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def _oeffnen(pfad: Path, schreibend: bool = False) -> sqlite3.Connection:
    if schreibend:
        conn = sqlite3.connect(str(pfad))
    else:
        conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _trigger(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}


def _vorhandene_tabellen(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def init(ziel: Path) -> int:
    """Legt an einem beliebigen Ort eine leere, vollstaendig regelbewehrte
    brainlehr an. Ein bestehender Bestand wird nie angefasst."""
    ziel = ziel.resolve()
    db = ziel / "knowledge.db" if ziel.is_dir() or not ziel.suffix else ziel
    if db.exists() and db.stat().st_size > 0:
        print(f"FEHLER: {db} existiert bereits und ist nicht leer. "
              f"Nichts getan -- eine Erstanlage ueberschreibt keinen Bestand.")
        return 1
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    kms.ensure_schema(conn)
    conn.commit()
    trigger = _trigger(conn)
    tabellen = _vorhandene_tabellen(conn)
    conn.close()
    print(f"angelegt: {db}")
    print(f"  Tabellen: {len(tabellen)}")
    print(f"  Regeln (Trigger): {len(trigger)}")
    print(f"  Herkunftsschranke: {'ja' if 'knowledge_nodes_herkunft_bu' in trigger else 'NEIN -- FEHLER'}")
    print(f"\nBenutzen: BEGOD_KNOWLEDGE_DB={db} python3 knowledge_mcp_server.py")
    return 0 if "knowledge_nodes_herkunft_bu" in trigger else 1


def raus(ziel_datei: Path, db: Path) -> int:
    """Schreibt den Bestand zeilenweise heraus. Erste Zeile ist ein Kopf mit
    Herkunft und Sollzahlen -- ohne ihn waere der Auszug selbst eine Aussage
    ohne Herkunft."""
    conn = _oeffnen(db)
    vorhanden = _vorhandene_tabellen(conn)
    zeilen: dict[str, int] = {}
    with ziel_datei.open("w", encoding="utf-8") as f:
        f.write("")  # Kopf kommt ans Ende der Zaehlung, deshalb Platzhalterlauf unten
        rumpf: list[str] = []
        for tabelle in TABELLEN:
            if tabelle not in vorhanden:
                zeilen[tabelle] = 0
                continue
            n = 0
            # Eltern vor Kindern: der Trigger knowledge_nodes_parent_check_bi
            # weist ein Kind ab, dessen Elternknoten noch fehlt. Beim Auszug
            # sortieren statt beim Einlesen umzuordnen -- so ist die Datei
            # selbst schon in einer einlesbaren Reihenfolge und bleibt es,
            # egal wer sie spaeter einliest.
            ordnung = " ORDER BY level, path" if tabelle == "knowledge_nodes" else ""
            for row in conn.execute(f"SELECT * FROM {tabelle}{ordnung}"):
                zeile = {k: _wert_raus(row[k]) for k in row.keys()}
                rumpf.append(json.dumps({"tabelle": tabelle, "zeile": zeile},
                                        ensure_ascii=False))
                n += 1
            zeilen[tabelle] = n
        kopf = {
            "brainlehr_auszug": 1,
            "erzeugt": _jetzt(),
            "quelle": str(db.resolve()),
            "trigger": sorted(_trigger(conn)),
            "zeilen": zeilen,
        }
        f.write(json.dumps(kopf, ensure_ascii=False) + "\n")
        f.write("\n".join(rumpf))
        if rumpf:
            f.write("\n")
    conn.close()
    print(f"Auszug: {ziel_datei}")
    for t, n in zeilen.items():
        print(f"  {t}: {n}")
    print(f"  (nicht enthalten: knowledge_embeddings und *_fts -- ableitbar, "
          f"nach dem Einlesen build_embeddings.py laufen lassen)")
    return 0


def rein(quelle_datei: Path, db: Path) -> int:
    """Baut den Bestand in einer Zieldatenbank wieder auf. Legt sie an, falls
    sie fehlt. Bricht ab, wenn dort schon Knoten liegen -- Zusammenfuehren ist
    eine andere Aufgabe als Wiederherstellen und wird hier nicht geraten."""
    with quelle_datei.open(encoding="utf-8") as f:
        kopf = json.loads(f.readline())
    if kopf.get("brainlehr_auszug") != 1:
        print("FEHLER: kein brainlehr-Auszug (Kopfzeile fehlt oder unbekannte Fassung).")
        return 1

    conn = sqlite3.connect(str(db))
    kms.ensure_schema(conn)
    conn.commit()
    vorher = conn.execute("SELECT count(*) FROM knowledge_nodes").fetchone()[0]
    if vorher:
        print(f"FEHLER: {db} enthaelt bereits {vorher} Knoten. Nichts getan.")
        conn.close()
        return 1

    # Sonderweg, siehe Modulkopf: der Pflicht-Trigger weist den Altbestand ab.
    for name in PFLICHT_TRIGGER:
        conn.execute(f"DROP TRIGGER IF EXISTS {name}")

    gezaehlt: dict[str, int] = {t: 0 for t in TABELLEN}
    fehler: list[str] = []
    with quelle_datei.open(encoding="utf-8") as f:
        f.readline()
        for nr, line in enumerate(f, start=2):
            line = line.strip()
            if not line:
                continue
            satz = json.loads(line)
            tabelle, zeile = satz["tabelle"], satz["zeile"]
            spalten = ", ".join(zeile)
            platz = ", ".join("?" for _ in zeile)
            # knowledge_config ist die einzige Tabelle, die ensure_schema mit
            # Vorgabewerten vorbelegt (embed_model). Der Auszug ist die
            # Wahrheit ueber die Betriebsentscheidungen und sticht die Vorgabe.
            verb = "INSERT OR REPLACE" if tabelle == "knowledge_config" else "INSERT"
            try:
                conn.execute(f"{verb} INTO {tabelle} ({spalten}) VALUES ({platz})",
                             [_wert_rein(v) for v in zeile.values()])
                gezaehlt[tabelle] += 1
            except sqlite3.Error as e:
                fehler.append((tabelle, str(e).split(":")[0], nr))
    conn.commit()

    # Regeln wiederherstellen und beweisen, dass sie wieder da sind.
    kms.ensure_schema(conn)
    conn.commit()
    trigger_jetzt = _trigger(conn)
    trigger_soll = set(kopf.get("trigger") or [])
    conn.close()

    print(f"eingelesen nach {db}")
    for t in TABELLEN:
        soll = kopf["zeilen"].get(t, 0)
        ist = gezaehlt[t]
        marke = "ok" if ist == soll else "ABWEICHUNG"
        print(f"  {t}: {ist} von {soll} {marke}")
    fehlend = trigger_soll - trigger_jetzt
    print(f"  Regeln: {len(trigger_jetzt)} von {len(trigger_soll)} "
          f"{'ok' if not fehlend else 'FEHLT: ' + ', '.join(sorted(fehlend))}")
    if fehler:
        gebuendelt: dict[tuple[str, str], list[int]] = {}
        for tabelle, grund, nr in fehler:
            gebuendelt.setdefault((tabelle, grund), []).append(nr)
        print(f"\n{len(fehler)} Zeilen abgewiesen, {len(gebuendelt)} Ursachen:")
        for (tabelle, grund), nrn in sorted(gebuendelt.items(),
                                            key=lambda x: -len(x[1])):
            print(f"  {len(nrn):5d}x {tabelle}: {grund}  (erste Zeile {nrn[0]})")
    alles_gleich = all(gezaehlt[t] == kopf["zeilen"].get(t, 0) for t in TABELLEN)
    return 0 if (alles_gleich and not fehlend and not fehler) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    unter = p.add_subparsers(dest="verb", required=True)

    p_init = unter.add_parser("init", help="leere, regelbewehrte brainlehr anlegen")
    p_init.add_argument("ziel", type=Path)

    p_raus = unter.add_parser("raus", help="Bestand zeilenweise herausschreiben")
    p_raus.add_argument("datei", type=Path)
    p_raus.add_argument("--db", type=Path, default=HIER / "knowledge.db")

    p_rein = unter.add_parser("rein", help="Bestand in eine Datenbank einlesen")
    p_rein.add_argument("datei", type=Path)
    p_rein.add_argument("--db", type=Path, required=True)

    a = p.parse_args(argv)
    if a.verb == "init":
        return init(a.ziel)
    if a.verb == "raus":
        return raus(a.datei, a.db)
    return rein(a.datei, a.db)


if __name__ == "__main__":
    raise SystemExit(main())
