#!/usr/bin/env python3
"""Warum steht BDW-P05 (Zielbild A) bei 8,6 %? -- Diagnose, kein Umbau.

`messungen/zielbild_a_vollstaendigkeit.py` liefert VIER Quoten und eine
Gesamtquote. Was es NICHT sagt: ob eine fehlende Angabe daran liegt, dass
der Abruf das Ziel nicht fand, dass das Feld in der Datenbank leer ist,
oder dass es gefuellt ist und der Abruf es nicht ausliefert. Genau diese
drei Faelle brauchen verschiedene Behebungen -- und zwei davon liegen
nicht im Abruf.

Je Fall und je Bestandteil wird deshalb ein Topf vergeben:
    a  Ziel nicht unter den ersten K des Abrufs
    b  Ziel gefunden, Feld in der Datenbank leer
    c  Ziel gefunden, Feld gefuellt, wird aber nicht ausgeliefert
    d  Ziel gefunden, Feld gefuellt, wird ausgeliefert

WEG: Der Abruf wird NICHT erneut gefahren (er braucht den Ollama-Daemon
und wuerde eine parallele Messung stoeren). Uebernommen wird die Spalte
`aussage` aus einem vorhandenen Lauf von
zielbild_a_vollstaendigkeit.py -- das ist dieselbe Zahl, die den Befund
erzeugt hat, den diese Diagnose erklaeren soll. Alles Uebrige kommt aus
der Datenbank plus den AUSLIEFERUNGSREGELN, die in
knowledge_mcp_server.knowledge_search() im Ergebnis-dict stehen (Zeile
~2870 fuer Knoten, ~2896 fuer Lehren) -- nicht aus einem Nachbau der
Suche, sondern aus dem, was der Produktivweg nachweislich in den Treffer
schreibt.

Zusaetzlich die Gegenrechnung, die das Messwerkzeug nicht stellt:
OBERGRENZE -- was waere die Gesamtquote bei PERFEKTEM Abruf (jedes Ziel
auf Rang 1)? Liegt sie unter 95 %, ist Zielbild A mit dem heutigen
Bestand unerreichbar, egal wie gut die Suche wird.

Aufruf:
    python3 messungen/zielbild_a_diagnose.py [--lauf DATEI] [--out DATEI]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "haken"), str(WURZEL / "kern")]

import ort  # noqa: E402  -- setzt den Datenbankort, nie fest verdrahten
from kern import speicher  # noqa: E402

KORPUS = WURZEL / "runs" / "pruefkorpus.jsonl"
SCHWELLE = 0.95
BESTANDTEILE = ("quelle", "status", "geltung")


def _letzter_lauf() -> Path:
    kandidaten = sorted((WURZEL / "runs").glob("zielbild_a_vollstaendigkeit_*.json"))
    if not kandidaten:
        raise SystemExit("kein Lauf von zielbild_a_vollstaendigkeit.py in runs/")
    return kandidaten[-1]


def _faelle() -> list[dict]:
    zeilen = [json.loads(z) for z in KORPUS.read_text(encoding="utf-8").splitlines() if z.strip()]
    return [f for f in zeilen if f.get("category") != "negative"]


def _ziel_zeile(conn, ziel: str) -> tuple[str | None, dict | None]:
    """(art, zeile) -- Lehre oder Knoten, ueber Kennung ODER Pfad."""
    z = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (ziel,)).fetchone()
    if z is not None:
        return "lesson", dict(z)
    z = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (ziel, ziel)).fetchone()
    if z is not None:
        return "node", dict(z)
    return None, None


def _gefuellt(wert) -> bool:
    return wert is not None and wert != ""


def _datenbank_hat(art: str, zeile: dict) -> dict:
    """Traegt die DATENBANKZEILE die Angabe -- unabhaengig von der Auslieferung.

    Fuer Lehren wird der Bestandteil auf die Felder gelesen, die
    lessons_learned ueberhaupt hat (schema.sql): eine Lehre kennt kein
    `source` und keinen `norm_rang`. Herkunft ist dort `bezug`/`node_path`/
    `session`, Status ist `status`/`pruefstelle`.
    """
    if art == "lesson":
        return {
            "quelle": any(_gefuellt(zeile.get(f)) for f in ("bezug", "node_path", "session")),
            "status": any(_gefuellt(zeile.get(f)) for f in ("status", "pruefstelle")),
            "geltung": any(_gefuellt(zeile.get(f)) for f in ("gilt_ab", "gilt_bis")),
        }
    return {
        "quelle": _gefuellt(zeile.get("source")),
        "status": zeile.get("norm_rang") is not None or _gefuellt(zeile.get("norm_entscheidung")),
        "geltung": any(_gefuellt(zeile.get(f)) for f in ("gilt_ab", "gilt_bis")),
    }


def _wird_ausgeliefert(art: str, zeile: dict) -> dict:
    """Was das Messwerkzeug im TREFFER vorfaende -- nach dessen eigener Regel.

    zielbild_a_vollstaendigkeit._bestandteile liest ausschliesslich
    `source`/`quelle`, `norm_rang`/`norm_entscheidung`, `gilt_ab`/`gilt_bis`.
    Ein Lehren-Treffer traegt keins der ersten vier Felder (der Serverkode
    sagt das woertlich: "source/norm_rang/norm_entscheidung gibt es in
    lessons_learned nicht ... also nicht erfunden") -- fuer Lehren sind
    quelle und status also strukturell falsch, egal was in der Zeile steht.
    """
    if art == "lesson":
        return {
            "quelle": False,
            "status": False,
            "geltung": any(_gefuellt(zeile.get(f)) for f in ("gilt_ab", "gilt_bis")),
        }
    return {
        "quelle": _gefuellt(zeile.get("source")),
        "status": zeile.get("norm_rang") is not None or _gefuellt(zeile.get("norm_entscheidung")),
        "geltung": any(_gefuellt(zeile.get(f)) for f in ("gilt_ab", "gilt_bis")),
    }


def _laufreihe() -> dict:
    """`aussage` je vorhandenem Lauf -- die Zahl, auf der Topf (a) ruht.

    Schwankt sie, schwankt auch (a). Das ist keine Nebenbemerkung: der
    Abrufteil dieses Befundes ist nur so belastbar wie diese Reihe."""
    reihe = {}
    for f in sorted((WURZEL / "runs").glob("zielbild_a_vollstaendigkeit_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        reihe[f.name] = {"aussage": d["je_bestandteil"]["aussage"]["treffer"],
                         "vollstaendig": d["vollstaendig"]["treffer"], "n": d["korpus"]["n"]}
    return {"je_lauf": reihe,
            "hinweis": ("gleicher Korpus, gleicher Weg -- eine Schwankung in `aussage` "
                        "ist eine Eigenschaft des Abrufs, nicht des Korpus")}


def _korrigierte_lesart(einzeln: list[dict], n: int) -> dict:
    """Was waere, wenn die Messung je Sorte die Felder laese, die es dort GIBT?

    Ein Lehren-Treffer traegt Herkunft als `bezug`/`node_path`/`session` und
    Status als `status`/`pruefstelle` -- alle diese Felder stehen wirklich im
    Ergebnis-dict (knowledge_mcp_server, kind=lesson). Nur ihre NAMEN sind
    andere als bei Knoten. Die Messung liest ausschliesslich die Knotennamen
    und sieht deshalb bei jeder Lehre eine Luecke, die es nicht gibt.

    Gerechnet wird die Obergrenze bei perfektem Abruf, damit der Vergleich zur
    ungekuerzten Lesart nur EINE Variable aendert."""
    voll = 0
    for e in einzeln:
        liefert = dict(e["ausgeliefert"])
        if e["art"] == "lesson":
            # was der Treffer wirklich mitfuehrt, statt der Knotennamen
            liefert["quelle"] = e["in_db"]["quelle"]
            liefert["status"] = e["in_db"]["status"]
        if all(liefert.values()):
            voll += 1
    return {
        "obergrenze_voll": voll, "n": n, "quote": round(voll / n, 4),
        "gewinn_gegenueber_heutiger_lesart": voll,
        "bedeutung": ("Obergrenze bei perfektem Abruf UND je Sorte richtig gelesenen "
                      "Feldnamen. Bleibt sie gleich, ist die Messkorrektur nicht das, "
                      "was das AC blockiert."),
    }


def _verfallsrate_deckung(einzeln: list[dict]) -> dict:
    """Punkt 4: koennte kern/verfallsrate.py die gilt_bis-Luecke schliessen?

    Gemessen wird die DECKUNG, nicht die Eignung: fuer wie viele der Ziele
    ohne Geltung koennte das Modul ueberhaupt eine Zahl liefern? Lehren sind
    dort ausdruecklich ausgeschlossen (Modul-Docstring: lessons_learned
    traegt keinen Widerrufswert), Knoten brauchen einen Ast mit
    MIN_HISTORIE Eintraegen."""
    from kern import verfallsrate

    fehler = None
    raten, schaetzungen = {}, {}
    with speicher.lesen() as conn:
        try:
            raten = verfallsrate.berechne(conn)
            schaetzungen = verfallsrate.lade_schaetzungen(conn)
        except Exception as exc:   # BEFUND, nicht umgangen: siehe "laeuft" unten
            fehler = f"{type(exc).__name__}: {exc}"
            # Der Fehlschlag ist gemeldet, ersetzt aber die Antwort auf Punkt 4
            # nicht. Zweiter Anlauf mit toleranter Zeitlesung -- NUR hier in der
            # Messung, kern/verfallsrate.py bleibt unangetastet.
            from datetime import datetime as _dt
            def _tolerant(created_at, jetzt, _o=verfallsrate._alter_tage):
                try:
                    return _o(created_at, jetzt)
                except ValueError:
                    d = _dt.fromisoformat(created_at.replace("Z", "+00:00"))
                    return max((jetzt - d).total_seconds() / 86400.0, 0.0)
            verfallsrate._alter_tage = _tolerant
            try:
                raten = verfallsrate.berechne(conn)
                schaetzungen = verfallsrate.lade_schaetzungen(conn)
            except Exception as exc2:
                fehler += f" | auch mit toleranter Zeitlesung: {type(exc2).__name__}: {exc2}"

    ohne_geltung = [e for e in einzeln if not e["in_db"]["geltung"]]
    lehren = [e for e in ohne_geltung if e["art"] == "lesson"]
    knoten = [e for e in ohne_geltung if e["art"] == "node"]
    mit_rate = [e for e in knoten
                if raten.get(verfallsrate.ast_von(e.get("pfad") or ""), {})
                   .get("halbwertszeit_tage") is not None]
    return {
        "laeuft_gegen_den_bestand": fehler is None,
        "fehler": fehler,
        "zahlen_unten_mit_toleranter_zeitlesung": fehler is not None and bool(raten),
        "ziele_ohne_geltung": len(ohne_geltung),
        "davon_lehren_ausserhalb_des_moduls": len(lehren),
        "davon_knoten": len(knoten),
        "knoten_mit_berechenbarer_halbwertszeit": len(mit_rate),
        "schaetzungen_von_hand_gesetzt": len(schaetzungen),
        "aeste_gesamt": len(raten),
        "aeste_mit_halbwertszeit": sum(1 for w in raten.values()
                                       if w.get("halbwertszeit_tage") is not None),
    }


def diagnose(lauf: Path, out: Path | None = None) -> dict:
    referenz = json.loads(lauf.read_text(encoding="utf-8"))
    gefunden = {e["ziel"]: bool(e["aussage"]) for e in referenz["einzeln"]}

    faelle = _faelle()
    einzeln, toepfe = [], {b: {"a": 0, "b": 0, "c": 0, "d": 0} for b in BESTANDTEILE}
    fall_topf = {"a": 0, "b": 0, "c": 0, "d": 0}
    obergrenze_voll = 0
    fehlend = []

    with speicher.lesen() as conn:
        for fall in faelle:
            ziel = fall.get("target_id") or fall.get("target_label")
            art, zeile = _ziel_zeile(conn, ziel)
            if zeile is None:
                fehlend.append(ziel)
                art, zeile = "node", {}
            da = _datenbank_hat(art, zeile)
            liefert = _wird_ausgeliefert(art, zeile)
            traf = gefunden.get(ziel, False)

            je = {}
            for b in BESTANDTEILE:
                if not traf:
                    t = "a"
                elif not da[b]:
                    t = "b"
                elif not liefert[b]:
                    t = "c"
                else:
                    t = "d"
                toepfe[b][t] += 1
                je[b] = t
            # Fall-Topf: der SCHLECHTESTE Bestandteil bestimmt den Fall,
            # weil das AC alle vier zugleich verlangt.
            fall_topf[min(je.values(), key="abcd".index)] += 1
            if all(liefert.values()):
                obergrenze_voll += 1
            einzeln.append({"ziel": ziel, "art": art, "gefunden": traf,
                            "in_db": da, "ausgeliefert": liefert, "topf": je,
                            "pfad": zeile.get("path"),
                            "zurueckgezogen": bool(zeile.get("zurueckgezogen")),
                            "gattung": zeile.get("gattung")})

    n = len(faelle)
    ergebnis = {
        "zeit": datetime.now(timezone.utc).isoformat(),
        "frage": ("BDW-P05/Zielbild A steht bei 8,6 %. Liegt das am Abruf, am leeren "
                  "Feld oder an der Auslieferung?"),
        "weg": {
            "aussage": f"uebernommen aus {lauf.relative_to(WURZEL)} (Produktivweg, "
                       "nicht neu gefahren -- Ollama-Kollision)",
            "feldstand": "Datenbank ueber kern/speicher.lesen(), Ort ueber haken/ort.py",
            "auslieferung": "Regeln aus knowledge_mcp_server.knowledge_search(), "
                            "Ergebnis-dict fuer kind=node bzw. kind=lesson",
        },
        "korpus": {"datei": str(KORPUS.relative_to(WURZEL)), "n": n,
                   "nicht_in_db": fehlend},
        "toepfe": {
            "legende": {
                "a": "Ziel nicht unter den ersten K -- Abrufproblem",
                "b": "Ziel gefunden, Feld in der Datenbank leer -- Bestandsproblem",
                "c": "Ziel gefunden, Feld gefuellt, nicht ausgeliefert -- Auslieferungsproblem",
                "d": "alles da",
            },
            "je_bestandteil": toepfe,
            "je_fall": fall_topf,
            "hinweis_je_fall": "schlechtester Bestandteil bestimmt den Fall (AC verlangt alle zugleich)",
        },
        "obergrenze_bei_perfektem_abruf": {
            "voll": obergrenze_voll, "n": n, "quote": round(obergrenze_voll / n, 4),
            "schwelle": SCHWELLE,
            "erreichbar": obergrenze_voll / n >= SCHWELLE,
            "bedeutung": ("Gesamtquote, wenn jeder Abruf sein Ziel auf Rang 1 legte. "
                          "Liegt sie unter der Schwelle, ist das AC mit dem heutigen "
                          "Bestand unerreichbar -- unabhaengig von der Abrufguete."),
        },
        "referenzlauf_stabilitaet": _laufreihe(),
        "korrigierte_lesart": _korrigierte_lesart(einzeln, n),
        "verfallsrate_als_astweg": _verfallsrate_deckung(einzeln),
        "einzeln": einzeln,
    }

    ziel_datei = out or (WURZEL / "runs" /
                         f"zielbild_a_diagnose_{datetime.now().strftime('%Y-%m-%d')}.json")
    ziel_datei.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    ergebnis["datei"] = str(ziel_datei)
    return ergebnis


def demo() -> None:
    """Kleinster Lauf, der fehlschlaegt, wenn die Topflogik bricht."""
    # Lehre mit bezug: in der DB vorhanden, aber vom Treffer nicht ausgeliefert -> c
    lehre = {"bezug": "x", "status": "active", "gilt_ab": None, "gilt_bis": None}
    assert _datenbank_hat("lesson", lehre)["quelle"] is True
    assert _wird_ausgeliefert("lesson", lehre)["quelle"] is False
    # Geltung fehlt in der Zeile selbst -> b, nicht c
    assert _datenbank_hat("lesson", lehre)["geltung"] is False
    # Knoten mit source, ohne Geltung
    knoten = {"source": "manual", "norm_rang": None, "norm_entscheidung": "offen",
              "gilt_ab": None, "gilt_bis": None}
    assert _wird_ausgeliefert("node", knoten) == {"quelle": True, "status": True, "geltung": False}
    print("demo ok")


def main() -> int:
    if "--demo" in sys.argv:
        demo()
        return 0
    lauf = Path(sys.argv[sys.argv.index("--lauf") + 1]) if "--lauf" in sys.argv else _letzter_lauf()
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    e = diagnose(lauf, out)
    n = e["korpus"]["n"]
    print(f"Diagnose ueber {n} Faelle, Referenzlauf {lauf.name}")
    for b, t in e["toepfe"]["je_bestandteil"].items():
        print(f"  {b:8} a={t['a']:2} b={t['b']:2} c={t['c']:2} d={t['d']:2}")
    t = e["toepfe"]["je_fall"]
    print(f"  JE FALL  a={t['a']:2} b={t['b']:2} c={t['c']:2} d={t['d']:2}")
    o = e["obergrenze_bei_perfektem_abruf"]
    print(f"  Obergrenze bei perfektem Abruf: {o['voll']}/{n} = {o['quote']:.1%} "
          f"(Schwelle {SCHWELLE:.0%}) -> {'erreichbar' if o['erreichbar'] else 'UNERREICHBAR'}")
    print(f"  {e['datei']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
