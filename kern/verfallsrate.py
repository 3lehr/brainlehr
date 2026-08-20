#!/usr/bin/env python3
"""Verfallsrate je Ast -- E1 aus docs/PLAN_BETRIEBSPROFILE_2026-08-20.md,
Abnahme BDW-P13 (docs/REQUIREMENTS_BRAINLEHR.md:121).

DIE SACHE: Ein Modell hat keine Uhr und beantwortet eine Frage von heute mit
derselben Zuversicht wie eine von vor Monaten. brainlehr soll deshalb wissen,
was das Modell NICHT wissen kann -- und die Verfallsrate ist eine Eigenschaft
des THEMAS (Ast), nicht der einzelnen Frage: man muss nicht wissen, was
gefragt wird, nur dass Steuerrecht sich jaehrlich aendert und Zahlentheorie
nicht.

Dieser Auftrag baut nur E1, und davon nur zwei der drei Quellen:

1. SCHAETZUNG JE AST -- keine eigene Zahl hier, siehe unten "verworfen".
2. WIDERRUFSQUOTE -- rueckwaerts, aus der eigenen Historie: wie oft wurde in
   einem Ast etwas zurueckgezogen, ueberholt oder korrigiert. Das ist die
   einzige Quelle, die dieses Modul tatsaechlich MISST.

VERWORFEN, und warum: Eine "Schaetzung je Ast" ohne Messgrundlage waere eine
geratene Zahl je Themenname ("Steuerrecht=schnell, Mathematik=langsam") --
genau die Sorte Behauptung, die die Hausregel "jede Zahl vor dem Weitertragen
pruefen" verbietet. Sie ist hier NICHT eingebaut. Was bleibt: Wo die Historie
keinen einzigen Widerruf hergibt, bekommt der Ast "unbekannt" statt eine
erfundene Rate -- das ist der Negativfall aus dem Auftrag, nicht eine
Verletzung von Punkt 1.

WAS ALS WIDERRUF ZAEHLT (das Modul MISST diese drei, mehr gibt der Bestand
nicht her -- siehe schema.sql):
  - knowledge_nodes.zurueckgezogen = 1                    (explizit)
  - der Knoten hat >=1 Zeile in knowledge_fassungen        (Inhalt korrigiert;
    der Trigger knowledge_fassung_au schreibt dort nur bei echter
    Aenderung von title/summary/content/tags)
  - der Knoten ist target_path einer knowledge_relations-Zeile vom Typ
    supersedes/loest_ab/replaces_component                (von einem
    anderen Knoten ueberholt)
lessons_learned.status traegt KEINEN Widerrufswert (die vorhandenen Werte
sind active/open/resolved/escalated_to_rule/in_claude_md -- "resolved" heisst
"Fehler behoben", nicht "Lehre war falsch"). Deshalb bleibt lessons_learned
hier aussen vor, statt eine Spalte zu ueberdehnen.

DIE FALLE (aus dem Auftrag): "selten geprueft -> selten Funde -> Rate sinkt
-> noch seltener geprueft". Gegenmittel hier: UNTERGRENZE (a). Jeder Ast
bekommt eine naechste_pruefung_spaetestens_tage, die nie ueber
OBERGRENZE_TAGE hinausgeht -- auch ein Ast mit Rate 0 wird spaetestens nach
einem Jahr wieder angefasst, unabhaengig davon, wie stabil er bisher aussah.
Verworfen: (b) Stichprobe -- das waere ein zweiter Lauf (Ziehung + Pruefung
durch einen Menschen oder ein Modell), keine Eigenschaft dieser Messung, und
gehoert eher zu E2/E3. (c) Asymmetrie -- ohne zweite Messung nach einem Fund
gibt es hier nichts, dessen Intervall sich verkuerzen liesse.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Wurzel am Merkmal schema.sql finden, wie in kern/abrufguete.py und
# haken/ort.py -- eine feste Ebenenzahl bricht beim naechsten Umzug lautlos.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import speicher

WURZEL = _w

# Relationstypen, die im Bestand tatsaechlich vorkommen und "ueberholt"
# bedeuten (gemessen 2026-08-21: 6 Zeilen im ganzen Bestand). "widerspricht"
# gibt es nicht -- 0 Treffer, deckungsgleich mit dem Befund in
# docs/PLAN_BETRIEBSPROFILE_2026-08-20.md ("Widerspruchserkennung fehlt").
SUPERSEDE_TYPEN = ("supersedes", "loest_ab", "replaces_component")

# Unter dieser Zahl an Eintraegen ist jede Rate Zufallsrauschen -- ein Ast mit
# einem Knoten hat entweder 0% oder 100% Widerrufe, keine dritte Moeglichkeit.
# Bewusst niedrig (3): mehr als zwei Drittel der 29 Aeste haben unter 20
# Knoten, eine hoehere Schwelle liesse fast alles auf "unbekannt" fallen.
MIN_HISTORIE = 3

# Gegenmittel gegen die Falle (Variante a, Untergrenze): auch ein Ast ohne
# jeden Fund gilt spaetestens nach einem Jahr wieder als pruefbeduerftig.
OBERGRENZE_TAGE = 365


def ast_von(pfad: str) -> str:
    """Erstes Pfadsegment nach dem fuehrenden '/': /brainlehr/x/y -> brainlehr."""
    rest = pfad.lstrip("/")
    return rest.split("/", 1)[0] if rest else ""


def _alter_tage(created_at: str, jetzt: datetime) -> float:
    dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return max((jetzt - dt).total_seconds() / 86400.0, 0.0)


def widerrufene_pfade(conn: sqlite3.Connection) -> set[str]:
    """Menge aller Pfade, die als widerrufen gelten -- Vereinigung der drei
    gemessenen Quellen (siehe Modul-Docstring)."""
    pfade: set[str] = set()
    for row in conn.execute("SELECT path FROM knowledge_nodes WHERE zurueckgezogen = 1"):
        pfade.add(row["path"])
    for row in conn.execute("SELECT DISTINCT path FROM knowledge_fassungen"):
        pfade.add(row["path"])
    platzhalter = ",".join("?" * len(SUPERSEDE_TYPEN))
    for row in conn.execute(
        f"SELECT DISTINCT target_path FROM knowledge_relations "
        f"WHERE relation_type IN ({platzhalter})",
        SUPERSEDE_TYPEN,
    ):
        pfade.add(row["target_path"])
    return pfade


def halbwertszeit_tage(rate: float, median_alter_tage: float) -> float | None:
    """Schaetzt die Halbwertszeit aus Rate und beobachtetem Durchschnittsalter,
    unter der Annahme einer konstanten Widerrufsrate (Exponentialmodell):
    ueberlebend(t) = exp(-lambda*t), beobachtete Rate = 1 - exp(-lambda*t_alt)
    -> lambda = -ln(1-rate)/t_alt, Halbwertszeit = ln(2)/lambda.

    Bei Rate 0 gibt es keinen Zerfall zu schaetzen (kein Fund, keine
    Zeitbasis dafuer) -- None statt einer erfundenen "unendlich" -- der
    Aufrufer setzt an dieser Stelle die Untergrenze (OBERGRENZE_TAGE)."""
    if rate <= 0.0 or median_alter_tage <= 0.0:
        return None
    if rate >= 1.0:
        return 0.0
    lam = -math.log(1.0 - rate) / median_alter_tage
    return math.log(2) / lam


def berechne(conn: sqlite3.Connection, jetzt: datetime | None = None) -> dict:
    """Verfallsrate je Ast. Rueckgabe: {ast: {...}}, sortiert ist Sache des
    Aufrufers."""
    jetzt = jetzt or datetime.now(timezone.utc)
    widerrufen = widerrufene_pfade(conn)

    gruppen: dict[str, list[tuple[str, float]]] = {}
    for row in conn.execute("SELECT path, created_at FROM knowledge_nodes"):
        ast = ast_von(row["path"])
        if not ast:
            continue
        gruppen.setdefault(ast, []).append((row["path"], _alter_tage(row["created_at"], jetzt)))

    ergebnis: dict[str, dict] = {}
    for ast, eintraege in gruppen.items():
        gesamt = len(eintraege)
        treffer = sum(1 for pfad, _ in eintraege if pfad in widerrufen)
        alter = sorted(a for _, a in eintraege)
        median_alter = alter[len(alter) // 2] if alter else 0.0

        if gesamt < MIN_HISTORIE:
            ergebnis[ast] = {
                "gesamt": gesamt,
                "widerrufe": treffer,
                "rate": None,
                "halbwertszeit_tage": None,
                "naechste_pruefung_spaetestens_tage": OBERGRENZE_TAGE,
                "quelle": "unbekannt -- weniger als MIN_HISTORIE=%d Eintraege, Rate waere Rauschen" % MIN_HISTORIE,
            }
            continue

        rate = treffer / gesamt
        hwz = halbwertszeit_tage(rate, median_alter)
        naechste_pruefung = min(hwz, OBERGRENZE_TAGE) if hwz is not None else OBERGRENZE_TAGE
        quelle = (
            "widerrufsquote -- keine Widerrufe im Bestand, Untergrenze greift"
            if rate == 0.0
            else "widerrufsquote"
        )
        ergebnis[ast] = {
            "gesamt": gesamt,
            "widerrufe": treffer,
            "rate": round(rate, 4),
            "halbwertszeit_tage": round(hwz, 1) if hwz is not None else None,
            "naechste_pruefung_spaetestens_tage": round(naechste_pruefung, 1),
            "quelle": quelle,
        }
    return ergebnis


def main() -> None:
    with speicher.lesen() as conn:
        ergebnis = berechne(conn)

    ausgabe = {
        "erzeugt_am": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "min_historie": MIN_HISTORIE,
        "obergrenze_tage": OBERGRENZE_TAGE,
        "gegenmittel_gegen_die_falle": "untergrenze (a) -- naechste_pruefung_spaetestens_tage "
                                        "ueberschreitet nie OBERGRENZE_TAGE, auch bei Rate 0",
        "befund_beim_lesen": (
            "Die Quelle misst Bearbeitungsintensitaet, nicht zwingend fachlichen Verfall: "
            "knowledge_fassungen (Korrektur) feuert bei JEDER inhaltlichen Aenderung, auch "
            "reiner Anreicherung waehrend einer aktiven Sitzung -- ein Ast mit Rate 1.0 "
            "(z.B. arch, tools, backend) heisst 'wurde gerade viel bearbeitet', nicht "
            "zwingend 'war oft falsch'. Umgekehrt liefern germanquad und nasa-llis (zusammen "
            "4351 von 5240 Knoten, 83% des Bestands) beide Rate 0 -- Grossimporte, seit der "
            "Anlage nie wieder angefasst. Diese Quelle kann NICHT unterscheiden, ob das "
            "Themengebiet echt stabil ist oder ob es nur nie geprueft wurde -- genau die "
            "Falle aus dem Auftrag. Ohne eine vorwaertsgerichtete Quelle (E2/E3, hier "
            "ausdruecklich nicht gebaut) bleibt diese Unterscheidung offen."
        ),
        "aeste": dict(sorted(ergebnis.items(), key=lambda kv: -kv[1]["gesamt"])),
    }
    ziel = WURZEL / "runs" / "verfallsrate_2026-08-21.json"
    ziel.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {ziel}")
    fuenf_groesste = list(ausgabe["aeste"].items())[:5]
    for ast, werte in fuenf_groesste:
        print(f"  {ast}: gesamt={werte['gesamt']} widerrufe={werte['widerrufe']} rate={werte['rate']}")


def demo() -> None:
    """Selbsttest gegen eine synthetische In-Memory-DB (kein Ollama, kein
    echter Bestand noetig) -- reine Stdlib, keine Fixture-Datei.

    Deckt ab: Grenzwerte um MIN_HISTORIE (2/3/4 Eintraege je eigener Ast),
    den Negativfall (Ast ohne jede Historie -> 'unbekannt', keine erfundene
    Rate), alle drei gemessenen Widerrufsquellen einzeln, und die Untergrenze
    (Rate 0 -> naechste Pruefung bei OBERGRENZE_TAGE, nicht 'nie')."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE knowledge_nodes (path TEXT, created_at TEXT, zurueckgezogen INTEGER DEFAULT 0);
        CREATE TABLE knowledge_fassungen (node_id TEXT, path TEXT);
        CREATE TABLE knowledge_relations (source_path TEXT, target_path TEXT, relation_type TEXT);
        """
    )
    jetzt = datetime(2026, 8, 21, tzinfo=timezone.utc)
    alt = "2025-08-21T00:00:00Z"  # 365 Tage alt

    # /unter_schwelle: 2 Knoten (< MIN_HISTORIE=3) -> unbekannt, trotz 1 Widerruf
    # (erste Quelle: zurueckgezogen=1 direkt an einem der beiden Knoten).
    conn.executemany(
        "INSERT INTO knowledge_nodes VALUES (?,?,?)",
        [("/unter_schwelle/a", alt, 1), ("/unter_schwelle/b", alt, 0)],
    )

    # /an_schwelle: genau 3 Knoten, 1 widerrufen (per Fassung) -> Rate 1/3, gemessen.
    conn.executemany(
        "INSERT INTO knowledge_nodes VALUES (?,?,0)",
        [("/an_schwelle/a", alt), ("/an_schwelle/b", alt), ("/an_schwelle/c", alt)],
    )
    conn.execute("INSERT INTO knowledge_fassungen VALUES ('n1', '/an_schwelle/a')")

    # /ueber_schwelle: 4 Knoten, 0 Widerrufe -> Rate 0, Untergrenze greift.
    conn.executemany(
        "INSERT INTO knowledge_nodes VALUES (?,?,0)",
        [("/ueber_schwelle/a", alt), ("/ueber_schwelle/b", alt),
         ("/ueber_schwelle/c", alt), ("/ueber_schwelle/d", alt)],
    )

    # /supersede_ast: 3 Knoten, einer per Relation ueberholt (dritte Quelle).
    conn.executemany(
        "INSERT INTO knowledge_nodes VALUES (?,?,0)",
        [("/supersede_ast/alt", alt), ("/supersede_ast/neu", alt), ("/supersede_ast/x", alt)],
    )
    conn.execute(
        "INSERT INTO knowledge_relations VALUES ('/supersede_ast/neu', '/supersede_ast/alt', 'supersedes')"
    )

    ergebnis = berechne(conn, jetzt=jetzt)

    u = ergebnis["unter_schwelle"]
    assert u["gesamt"] == 2 and u["rate"] is None, u
    assert "unbekannt" in u["quelle"], u
    assert u["naechste_pruefung_spaetestens_tage"] == OBERGRENZE_TAGE, u

    a = ergebnis["an_schwelle"]
    assert a["gesamt"] == 3 and a["widerrufe"] == 1, a
    assert abs(a["rate"] - (1 / 3)) < 1e-3, a  # rate ist auf 4 Stellen gerundet
    assert a["halbwertszeit_tage"] is not None and a["halbwertszeit_tage"] > 0, a

    o = ergebnis["ueber_schwelle"]
    assert o["gesamt"] == 4 and o["widerrufe"] == 0 and o["rate"] == 0.0, o
    assert o["halbwertszeit_tage"] is None, "Rate 0 darf keine erfundene Halbwertszeit tragen"
    assert o["naechste_pruefung_spaetestens_tage"] == OBERGRENZE_TAGE, (
        "Untergrenze (Gegenmittel a) muss bei Rate 0 greifen, sonst prueft sich der Ast nie wieder")

    s = ergebnis["supersede_ast"]
    assert s["widerrufe"] == 1, "die per Relation ueberholte Seite muss zaehlen: " + str(s)

    # Halbwertszeit-Formel direkt gegen die Handrechnung: rate=0.5, alter=100
    # -> lambda = -ln(0.5)/100 = ln(2)/100 -> Halbwertszeit = 100 Tage.
    hwz = halbwertszeit_tage(0.5, 100.0)
    assert hwz is not None and abs(hwz - 100.0) < 1e-6, hwz

    conn.close()
    print("demo: ok", file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
