"""Titelverteidiger-Mechanik fuer die Abrufkette (Betreiber-Entwurf 2026-08-08).

Ausgangslage, die den Entwurf noetig macht (gemessen, s. Auftrag): volle Kette
gegen rohen Kosinusvergleich 34/36 zu 35/36 (Gleichstand trotz sechs Stufen
Mechanik), zwei identische Laeufe derselben Einstellung 22/36 und 15/36
(sieben Faelle Streuung), ADR-035 stundenlang ausser Kraft ohne dass es
auffiel. Jede Aenderung der Abrufkette soll ab jetzt gegen den zuletzt
GEWONNENEN Stand gemessen werden, nicht gegen einen fest eingebrannten Wert.

Dieses Modul AENDERT NICHTS an der Abrufkette. Es haelt den Titelverteidiger
fest (titelverteidiger_festhalten) und faellt ein Urteil ueber einen
Herausforderer (herausforderer_bewerten) -- reine Rechnung aus Messwerten,
kein Modell entscheidet mit. Der Wechsel des Titelverteidigers ist eine
Freigabe des Betreibers, kein Ergebnis dieses Laufs.

Speicherort: Tabelle knowledge_config (key/value, existiert bereits fuer das
Einbettungsmodell) -- ein Schluessel je Bereich, Wert ist ein JSON-Blob mit
Einstellung, Rohmessungen und Datum.

Eine "Messung" ist eine Liste von LAEUFEN. Jeder Lauf ist ein dict mit den
Rohgroessen dieses einen Durchlaufs, z.B.
    {"trefferquote": 0.639, "schweigequote": 0.7, "kosten": 12.3}
Mehrere Laeufe derselben Einstellung = Wiederholung zur Streuungsmessung.
Fehlt eine Groesse in ALLEN Laeufen einer Seite, gilt sie als "unmessbar" --
nie stillschweigend als 0 oder 1 gewertet (Auflage).

Vier Siegbedingungs-Groessen, Gewichte per Nutzer einstellbar (Vorgabe: alle
gleich, ausdruecklich GERATEN):
    trefferquote   -- hoeher besser
    schweigequote  -- hoeher besser
    kosten         -- niedriger besser
    streuung       -- niedriger besser, aus der Spannweite (max-min) des
                      gewichteten Komposit-Scores ueber die Laeufe einer
                      Seite. Wird zugleich als Schwelle fuer die
                      Signifikanzpruefung verwendet (VERBINDLICH): ein
                      Herausforderer gewinnt nur, wenn sein Vorsprung groesser
                      ist als die Streuung BEIDER Seiten zusammen (Summe,
                      konservativ -- beide Seiten koennten sich zufaellig in
                      Richtung des jeweils anderen Extrems verschieben). Bei
                      weniger als zwei Laeufen auf einer Seite ist die
                      Streuung nicht bestimmbar -- das Urteil faellt dann nie
                      "gewonnen", sondern "unentschieden" mit Begruendung.

Trennung von Anpassungsmenge und Pruefmenge: dieses Modul kann strukturell
nicht pruefen, woran ein Herausforderer eingestellt wurde. Der Aufrufer muss
das ausdruecklich bestaetigen (an_pruefmenge_nicht_angepasst=True), sonst
bricht die Bewertung ab.

Aufruf:
    from meisterschaft import titelverteidiger_festhalten, herausforderer_bewerten
"""
from __future__ import annotations

import json
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
DEFAULT_DB = SHARED_KNOWLEDGE / "knowledge.db"

# Richtung je Rohgroesse fuer den Komposit-Score: +1 hoeher besser, -1 niedriger
# besser. "streuung" ist absichtlich NICHT hier drin -- sie wird aus der
# Spannweite des Komposits berechnet, nicht aus einer eigenen Rohgroesse.
RICHTUNG = {"trefferquote": 1.0, "schweigequote": 1.0, "kosten": -1.0}
SIEGGROESSEN = ("trefferquote", "schweigequote", "streuung", "kosten")

_DDL = """
CREATE TABLE IF NOT EXISTS knowledge_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(bereich: str) -> str:
    return f"meisterschaft_titelverteidiger:{bereich}"


def _conn(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.execute(_DDL)
    return con


def _median(xs: list) -> float | None:
    return statistics.median(xs) if xs else None


def _spread(xs: list) -> float | None:
    """Spannweite max-min. None (nicht 0) wenn weniger als 2 Laeufe --
    Streuung ist mit einem Lauf nicht bestimmbar, s. Lehre L-effd52
    (Streuungsmasse brauchen genug Punkte, sonst taeuschen sie Praezision vor)."""
    return (max(xs) - min(xs)) if len(xs) >= 2 else None


def _komposit(laeufe: list[dict], gewichte: dict) -> list[float]:
    """Ein gewichteter Score je Lauf, nur ueber Groessen, die in DIESEM Lauf
    vorhanden sind. Laeufe ohne jede bekannte Groesse fallen weg."""
    out = []
    for lauf in laeufe:
        terme = [gewichte.get(k, 1.0) * RICHTUNG[k] * v
                 for k, v in lauf.items() if k in RICHTUNG]
        if terme:
            out.append(sum(terme))
    return out


def _rohgroessen_unmessbar(laeufe: list[dict]) -> list[str]:
    """Rohgroessen, die in KEINEM Lauf dieser Seite vorkommen."""
    vorhanden = {k for lauf in laeufe for k in lauf}
    return [k for k in RICHTUNG if k not in vorhanden]


def _score(laeufe: list[dict], gewichte: dict) -> dict | None:
    komp = _komposit(laeufe, gewichte)
    if not komp:
        return None
    spread = _spread(komp)
    median = _median(komp)
    streuung_gewicht = gewichte.get("streuung", 1.0)
    final = median if spread is None else median - streuung_gewicht * spread
    return {
        "n_laeufe": len(komp),
        "median_komposit": median,
        "streuung_komposit": spread if spread is not None else "unmessbar",
        "final_score": final,
        "unmessbare_groessen": _rohgroessen_unmessbar(laeufe),
    }


def titelverteidiger_festhalten(einstellung: dict, laeufe: list[dict], pruefmenge: str,
                                 bereich: str = "abruf", db_path: Path = DEFAULT_DB,
                                 datum: str | None = None) -> dict:
    """Haelt die aktuell geltende Einstellung als Titelverteidiger fest --
    samt den Zahlen, gegen die sie gewonnen hat, dem Datum und der
    Pruefmenge, auf der gemessen wurde. Ueberschreibt den bisherigen
    Titelverteidiger desselben Bereichs (Freigabe liegt beim Aufrufer)."""
    if not laeufe:
        raise ValueError("kein Titelverteidiger ohne mindestens einen Messlauf")
    record = {
        "einstellung": einstellung,
        "laeufe": laeufe,
        "pruefmenge": pruefmenge,
        "datum": datum or _now(),
    }
    con = _conn(db_path)
    try:
        con.execute(
            "INSERT INTO knowledge_config (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (_key(bereich), json.dumps(record, ensure_ascii=False), _now()))
        con.commit()
    finally:
        con.close()
    return record


def titelverteidiger_lesen(bereich: str = "abruf", db_path: Path = DEFAULT_DB) -> dict | None:
    con = _conn(db_path)
    try:
        row = con.execute("SELECT value FROM knowledge_config WHERE key = ?",
                           (_key(bereich),)).fetchone()
    finally:
        con.close()
    return json.loads(row[0]) if row else None


def herausforderer_bewerten(einstellung: dict, laeufe: list[dict],
                             an_pruefmenge_nicht_angepasst: bool,
                             gewichte: dict | None = None, bereich: str = "abruf",
                             db_path: Path = DEFAULT_DB) -> dict:
    """Urteil ueber einen Herausforderer gegen den gespeicherten
    Titelverteidiger: 'gewonnen', 'verloren' oder 'unentschieden'. AENDERT
    NICHTS -- reine Rechnung, kein Modell im Urteil."""
    if not an_pruefmenge_nicht_angepasst:
        raise ValueError(
            "an_pruefmenge_nicht_angepasst muss ausdruecklich bestaetigt werden -- "
            "gemessen wird auf einer Pruefmenge, an der der Herausforderer NICHT "
            "eingestellt wurde, sonst ist das Ergebnis kein Nachweis")
    if not laeufe:
        raise ValueError("kein Urteil ohne mindestens einen Messlauf des Herausforderers")

    champion = titelverteidiger_lesen(bereich, db_path)
    if champion is None:
        raise ValueError(f"kein Titelverteidiger fuer Bereich '{bereich}' hinterlegt -- "
                          "erst titelverteidiger_festhalten() aufrufen")

    gewichte_geraten = gewichte is None
    g = {k: 1.0 for k in SIEGGROESSEN}
    if gewichte:
        g.update(gewichte)

    champ_score = _score(champion["laeufe"], g)
    herf_score = _score(laeufe, g)

    ergebnis = {
        "bereich": bereich,
        "titelverteidiger_datum": champion["datum"],
        "titelverteidiger_pruefmenge": champion["pruefmenge"],
        "gewichte": g,
        "gewichte_geraten": gewichte_geraten,
        "titelverteidiger": champ_score,
        "herausforderer": herf_score,
    }

    if champ_score is None or herf_score is None:
        ergebnis["urteil"] = "unentschieden"
        ergebnis["begruendung"] = "mindestens eine Seite liefert keine bewertbare Groesse"
        return ergebnis

    spread_c = champ_score["streuung_komposit"]
    spread_h = herf_score["streuung_komposit"]
    if spread_c == "unmessbar" or spread_h == "unmessbar":
        ergebnis["urteil"] = "unentschieden"
        ergebnis["begruendung"] = (
            "Streuung mindestens einer Seite unmessbar (weniger als 2 Laeufe) -- "
            "kein Sieg ohne Streuungsnachweis, s. Auflage")
        return ergebnis

    vorsprung = herf_score["final_score"] - champ_score["final_score"]
    erforderlich = spread_c + spread_h
    ergebnis["vorsprung"] = vorsprung
    ergebnis["erforderlicher_vorsprung"] = erforderlich
    if vorsprung > erforderlich:
        ergebnis["urteil"] = "gewonnen"
    elif -vorsprung > erforderlich:
        ergebnis["urteil"] = "verloren"
    else:
        ergebnis["urteil"] = "unentschieden"
        ergebnis["begruendung"] = "Vorsprung liegt innerhalb der Streuung beider Seiten"
    return ergebnis


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"

        # 1) Titelverteidiger aus heutigem Stand mit bekannten Zahlen (34/36
        #    gegen 35/36 aus dem Auftrag), zwei Wiederholungslaeufe fuer die
        #    Streuung (22/36, 15/36 -- die gemessene Ausgangslage).
        rec = titelverteidiger_festhalten(
            einstellung={"ensemble_pflicht": True, "min_hits": 3},
            laeufe=[{"trefferquote": 22 / 36, "schweigequote": 0.7, "kosten": 10.0},
                    {"trefferquote": 15 / 36, "schweigequote": 0.6, "kosten": 10.5}],
            pruefmenge="pruefkorpus_v3", db_path=db)
        assert rec["pruefmenge"] == "pruefkorpus_v3"
        gelesen = titelverteidiger_lesen(db_path=db)
        assert gelesen == rec

        # 2) Herausforderer nachweislich schlechter -> "verloren".
        u_schlecht = herausforderer_bewerten(
            einstellung={"min_hits": 1},
            laeufe=[{"trefferquote": 2 / 36, "schweigequote": 0.1, "kosten": 40.0},
                    {"trefferquote": 3 / 36, "schweigequote": 0.15, "kosten": 41.0}],
            an_pruefmenge_nicht_angepasst=True, db_path=db)
        assert u_schlecht["urteil"] == "verloren", u_schlecht

        # 3) Herausforderer nur im Rauschen anders -> "unentschieden", NICHT
        #    "gewonnen" (wichtigste Abnahme).
        u_rauschen = herausforderer_bewerten(
            einstellung={"min_hits": 3},
            laeufe=[{"trefferquote": 20 / 36, "schweigequote": 0.65, "kosten": 10.1},
                    {"trefferquote": 14 / 36, "schweigequote": 0.6, "kosten": 10.4}],
            an_pruefmenge_nicht_angepasst=True, db_path=db)
        assert u_rauschen["urteil"] == "unentschieden", u_rauschen

        # 4) Gewichtung aendern -> Urteil kann kippen. Herausforderer ist bei
        #    Kosten klar besser, bei Trefferquote leicht schlechter, aber
        #    beide Seiten reproduzierbar (Streuung 0 dank identischer
        #    Wiederholungen) -- mit Kostengewicht 0 verliert er, mit hohem
        #    Kostengewicht gewinnt er.
        laeufe_kosten_gut = [{"trefferquote": 20 / 36, "kosten": 2.0},
                              {"trefferquote": 20 / 36, "kosten": 2.0}]
        titelverteidiger_festhalten(
            einstellung={"min_hits": 3},
            laeufe=[{"trefferquote": 22 / 36, "kosten": 20.0},
                    {"trefferquote": 22 / 36, "kosten": 20.0}],
            pruefmenge="pruefkorpus_v3", bereich="kostenfall", db_path=db)
        u_ohne_kosten = herausforderer_bewerten(
            einstellung={}, laeufe=laeufe_kosten_gut, an_pruefmenge_nicht_angepasst=True,
            gewichte={"trefferquote": 1.0, "schweigequote": 0.0, "streuung": 1.0, "kosten": 0.0},
            bereich="kostenfall", db_path=db)
        u_mit_kosten = herausforderer_bewerten(
            einstellung={}, laeufe=laeufe_kosten_gut, an_pruefmenge_nicht_angepasst=True,
            gewichte={"trefferquote": 1.0, "schweigequote": 0.0, "streuung": 1.0, "kosten": 5.0},
            bereich="kostenfall", db_path=db)
        assert u_ohne_kosten["urteil"] == "verloren", u_ohne_kosten
        assert u_mit_kosten["urteil"] == "gewonnen", u_mit_kosten

        # Ohne Bestaetigung der Pruefmengen-Trennung: Abbruch.
        try:
            herausforderer_bewerten(einstellung={}, laeufe=[{"trefferquote": 1.0}],
                                     an_pruefmenge_nicht_angepasst=False, db_path=db)
            raise AssertionError("haette ValueError werfen muessen")
        except ValueError:
            pass

        print("demo ok:")
        print("  verloren:      ", u_schlecht["urteil"], u_schlecht.get("vorsprung"))
        print("  unentschieden: ", u_rauschen["urteil"])
        print("  gewicht kippt: ", u_ohne_kosten["urteil"], "->", u_mit_kosten["urteil"])


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    print(__doc__)
