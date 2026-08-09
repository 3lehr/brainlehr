#!/usr/bin/env python3
"""Der erste Melder, der URTEILT statt zaehlt.

Anlass: Der Betreiber vermisste am 2026-08-09, dass sich Pruefer von selbst
melden -- frueher habe ein Skeptiker-Agent auf Dogmen hingewiesen. Die
Recherche ergab (L-479171): er hat NIE autonom gefeuert. Er war Schritt 3
einer von Hand gestarteten Pipeline, und die "ACTIVATION: proaktiv"-Zeilen
im Frontmatter waren Prosa fuer ein Modell, kein Mechanismus.

Die Lage ist trotzdem besser als damals: heute feuern 23 Haken autonom. Es
fehlt nicht an Autonomie, sondern daran, dass einer ein URTEIL faellt.

DER UNTERSCHIED, auf den es ankommt: Ein Melder vergleicht eine Schwelle
("18 Tage alt", "12 ohne Vermerk"). Ein Pruefer sagt, dass etwas SCHIEF
STEHT, obwohl keine Zahl ueberschritten ist. Das ist heikler, weil es
Fehlalarme gibt -- darum drei Auflagen fuer jede Pruefung hier:

  1. Sie muss sich aus dem Bestand MESSEN lassen, nicht aus Stimmung.
  2. Sie nennt, welcher Fehlklasse sie nachgeht -- ein Befund ohne
     Fehlklasse ist eine Meinung.
  3. Sie nennt den Preis eines Fehlalarms. Wer den nicht beziffern kann,
     hat die Pruefung nicht zu Ende gedacht.

Und sie schweigt, solange nichts anschlaegt. Ein Pruefer, der bei jedem
Start dasselbe sagt, wird ueberlesen -- dann faellt er genauso aus wie
einer, den es nicht gibt.

Aufruf:
    python3 pruefer.py             # alle Pruefungen, ausfuehrlich
    python3 pruefer.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 pruefer.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "haken"))
import ort  # noqa: E402

# Woran ein KI-Entscheider erkennbar ist. Gleiche Liste wie in der
# Herkunftsschranke (schema.sql) -- bewusst hier wiederholt und nicht
# importiert, weil dieses Modul ohne Server und ohne Schemazugriff laufen
# koennen muss (Regel aus S7: jeder Lesepfad ohne den Server).
KI_MARKER = ("claude", "gpt", "gemini", "anthropic", "opus", "sonnet", "haiku")

# Ab wann eine Quote ueberhaupt etwas bedeutet. Unter dieser Zahl ist jede
# Prozentangabe Rauschen -- 2 von 3 sind 67 Prozent und sagen nichts.
MINDESTZAHL = 20


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def selbstzuschreibung(conn: sqlite3.Connection) -> dict | None:
    """Wieviele Normentscheidungen hat sich die Maschine selbst gegeben?

    FEHLKLASSE: stille Selbstermaechtigung. Eine Maschine, die ihre eigenen
    Aussagen fuer verbindlich erklaert, erzeugt eine Geltung ohne
    Gegenueber -- und niemandem faellt es auf, weil jede einzelne
    Entscheidung fuer sich plausibel aussieht.

    PREIS EINES FEHLALARMS: gering. Der Befund fordert kein Handeln, er
    macht eine Verteilung sichtbar. Wer ihn ignoriert, verliert nichts;
    wer ihm folgt, sieht sich 33 Zeilen an.

    Gemessen 2026-08-09 vor dem Bau: 62 von 72. Heute haette kein Melder
    das gesagt -- der Betreiber hat es selbst gefunden."""
    zeilen = conn.execute(
        "SELECT norm_entschieden_von FROM knowledge_nodes "
        "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0"
    ).fetchall()
    n = len(zeilen)
    if n < MINDESTZAHL:
        return None
    ki = sum(1 for z in zeilen
             if any(m in (z["norm_entschieden_von"] or "").lower() for m in KI_MARKER))
    anteil = ki / n
    if anteil < 0.5:
        return None
    return {
        "pruefung": "selbstzuschreibung",
        "befund": f"{ki} von {n} Normentscheidungen ({anteil:.0%}) hat ein KI-Akteur sich selbst gegeben",
        "fehlklasse": "stille Selbstermaechtigung -- Geltung ohne Gegenueber",
        "fehlalarm_kostet": "gering: der Befund fordert kein Handeln, er macht eine Verteilung sichtbar",
    }


def stumme_spalte(conn: sqlite3.Connection, spalte: str, zweck: str,
                  nur_normen: bool = True) -> dict | None:
    """Eine Spalte mit definiertem Zweck, die zu 100 Prozent leer steht.

    FEHLKLASSE: gebaute Regel ohne Wirkung. Sie sieht im Quelltext aus wie
    Schutz und unterscheidet nichts -- dieselbe Signatur wie ein Schema
    ohne Schreiber (vier Tokenspalten ueber 2167 Zeilen NULL) und wie der
    Skeptiker, dessen Ausloeser Prosa war (L-479171).

    PREIS EINES FEHLALARMS: gering, aber nicht null -- eine Spalte kann
    absichtlich leer sein (Altbestand, der nie geraten werden soll). Darum
    nennt der Befund den ZWECK mit, damit sich das beurteilen laesst.

    Nur bei 100 Prozent, nicht bei 90: eine teilweise gefuellte Spalte
    wirkt wenigstens dort, wo sie gefuellt ist. Der Sprung von 'wirkt nie'
    auf 'wirkt manchmal' ist der Unterschied, um den es geht."""
    wo = "WHERE norm_rang IS NOT NULL AND zurueckgezogen = 0" if nur_normen else "WHERE zurueckgezogen = 0"
    r = conn.execute(
        f"SELECT COUNT(*) n, SUM({spalte} IS NULL OR TRIM({spalte})='') leer "
        f"FROM knowledge_nodes {wo}"
    ).fetchone()
    n, leer = r["n"] or 0, r["leer"] or 0
    if n < MINDESTZAHL or leer != n:
        return None
    return {
        "pruefung": f"stumme_spalte:{spalte}",
        "befund": f"{spalte} ist bei allen {n} betroffenen Zeilen leer",
        "fehlklasse": f"gebaute Regel ohne Wirkung -- Zweck laut Schema: {zweck}",
        "fehlalarm_kostet": "gering: eine Spalte darf absichtlich leer sein, der Zweck steht daneben",
    }


def faellige_auswertung(conn: sqlite3.Connection) -> dict | None:
    """Wartet eine Auswertung auf genug FAELLE -- nicht auf genug Tage.

    FEHLKLASSE: Zeit als Massstab. "Eine Woche laufen lassen" ist derselbe
    Fehler wie "der Bestand ist noch klein" -- beides setzt einen Betrieb
    voraus, dessen Umfang niemand kennt. Eine Woche kann drei Abrufe
    bedeuten oder dreitausend; die Aussagekraft haengt an der Zahl der
    Faelle, nie am Kalender. Am 2026-08-09 habe ich die Zeitform zweimal an
    einem Tag benutzt, und der Betreiber hat beide Male widersprochen.

    PREIS EINES FEHLALARMS: keiner. Der Befund sagt "jetzt lohnt sich ein
    Blick", er verlangt nichts.

    Die offenen Auswertungen stehen unten als Tabelle -- Datei, Schwelle,
    was dann zu tun ist. Wer eine neue vertagt, traegt sie hier ein statt
    ein Datum zu nennen."""
    # NULLLINIE, und sie wird GEMESSEN statt eingetragen. Zweimal in drei
    # Minuten falsch gewesen: erst zaehlte der Melder den Gesamtbestand
    # (866 von 200 "erreicht", ueberwiegend aus dem alten Weg), dann trug
    # ich sie von Hand ein -- aus dem Hauptverzeichnis (42 Zeilen), waehrend
    # der Melder die Datei an SEINEM Ort liest (866). Zwei verschiedene
    # Dateien, eine Zahl.
    #
    # Darum: der erste Lauf legt die Nulllinie selbst an, dort wo er laeuft.
    # Eine Zahl, die im Quelltext steht, gilt fuer einen Ort, den der Autor
    # im Kopf hatte -- nicht fuer den, an dem sie gelesen wird.
    offen = [
        # (Bezeichnung, Zaehldatei, zusaetzliche Faelle, was dann zu tun ist)
        ("Suchpfad im Abruf", ort.WURZEL / "recall_log.jsonl", 200,
         "frisch lesen, ob das Mehr an Zeichen Nutzen oder Rauschen ist -- "
         "und ob der Verlust des Schweigens (vorher 37,8 % leer) stoert"),
        ("Bereinigung", ort.WURZEL / "bereinigung_log.jsonl", 500,
         "python3 bereinigung.py --bericht -- Schwelle und Schwaerzung an "
         "gemessenen Daten entscheiden statt an geratenen"),
    ]
    faellig = []
    for name, datei, schwelle, dann in offen:
        try:
            n = sum(1 for _ in datei.open(encoding="utf-8")) if datei.exists() else 0
            marke = datei.with_suffix(datei.suffix + ".nulllinie")
            if not marke.exists():
                marke.write_text(str(n), encoding="utf-8")   # erster Lauf setzt sie
                continue                                      # und meldet nie sofort
            nulllinie = int(marke.read_text(encoding="utf-8").strip() or 0)
        except Exception:
            continue
        seit = n - nulllinie
        if seit >= schwelle:
            faellig.append(f"{name}: {seit} von {schwelle} Faellen seit der Umstellung -- {dann}")
    if not faellig:
        return None
    return {
        "pruefung": "faellige_auswertung",
        "befund": " | ".join(faellig),
        "fehlklasse": "Zeit als Massstab -- eine Woche kann drei Faelle bedeuten oder dreitausend",
        "fehlalarm_kostet": "keiner: der Befund sagt 'jetzt lohnt ein Blick', er verlangt nichts",
    }


def platzhalterfuellung(conn: sqlite3.Connection, spalte: str, zweck: str,
                        schwelle: float = 0.8) -> dict | None:
    """Eine Spalte, die formal gefuellt ist und nichts sagt.

    FEHLKLASSE: Tautologisch erfuelltes Pflichtfeld. Nicht dieselbe wie
    stumme_spalte -- die meldet nur bei 100 Prozent LEER, weil eine
    teilweise gefuellte Spalte wenigstens dort wirkt, wo sie gefuellt ist.
    Hier ist die Spalte GEFUELLT, aber mit 'unbekannt' bzw. leerem Text,
    und faellt damit durch beide Netze: kein NULL, also nicht stumm; kein
    Inhalt, also ohne Wirkung. Gemessen 2026-08-09 an actor/model:
    361 von 383 Knoten ausserhalb des NASA-Imports, darunter der Knoten,
    in dem ich zwei Minuten zuvor genau diese Felder als Alleinstellung
    gegen fremde Systeme aufgeschrieben hatte.

    Verwandt und schon belegt: L-7aad34 (source liess sich mit einer
    Tautologie erfuellen) und L-86e92d (ordnungsgemaess abgelegt, in einer
    Ablage, die der Empfaenger nicht kennt). Dieselbe Signatur, andere
    Spalte -- ein Feld sieht befuellt aus und traegt nichts.

    PREIS EINES FEHLALARMS: gering. 'unbekannt' kann ehrlich sein, wo die
    Herkunft wirklich nicht feststellbar war. Darum die Schwelle bei 80
    Prozent statt bei jedem Einzelfall, und darum nennt der Befund die
    Zahl mit, statt nur zu urteilen.

    Warum nicht bei 100 Prozent wie stumme_spalte: ein Identitaetsfeld,
    das bei vier von fuenf Zeilen 'unbekannt' sagt, ist als Nachweis schon
    tot -- man kann daraus keine Aussage ueber den Bestand mehr ziehen.
    Der Unterschied zwischen 80 und 100 Prozent aendert daran nichts.

    NUR ARBEITSBESTAND, und das ist keine Bequemlichkeit, sondern der
    Nenner. Beim ersten Entwurf zaehlte die Pruefung ueber ALLE Knoten und
    schwieg: 361 blinde von 2021 sind 18 Prozent, weil der NASA-Import mit
    1638 Zeilen einen echten Schreiber traegt ('nasa_llis_import.py') und
    die Quote verduennt. Gemessen, BEVOR die Pruefung eingebaut wurde --
    dieselbe Fehlerklasse wie 'ortsabhaengige Zahl' im Arbeitsmelder.
    Sachlich richtig ist der engere Nenner ohnehin: bei einem
    Nachschlagewerk IST der Schreiber der Importeur, das sagt nichts ueber
    die Herkunftskette. Beim Arbeitsbestand ist er der ganze Punkt."""
    leerwerte = ("unbekannt", "unknown", "", "n/a", "none", "null")
    platz = ",".join("?" * len(leerwerte))
    r = conn.execute(
        f"SELECT COUNT(*) n, SUM(LOWER(TRIM(COALESCE({spalte},''))) IN ({platz})) blind "
        f"FROM knowledge_nodes WHERE zurueckgezogen = 0 "
        f"AND COALESCE(gattung,'arbeitsbestand') = 'arbeitsbestand'", leerwerte
    ).fetchone()
    n, blind = r["n"] or 0, r["blind"] or 0
    if n < MINDESTZAHL or blind / n < schwelle:
        return None
    return {
        "pruefung": f"platzhalterfuellung:{spalte}",
        "befund": f"{spalte} sagt bei {blind} von {n} Zeilen ({blind / n:.0%}) nichts aus",
        "fehlklasse": f"tautologisch erfuelltes Pflichtfeld -- Zweck laut Schema: {zweck}",
        "fehlalarm_kostet": "gering: 'unbekannt' darf ehrlich sein, die Quote steht daneben",
    }


def alle(conn: sqlite3.Connection) -> list[dict]:
    funde = [
        selbstzuschreibung(conn),
        faellige_auswertung(conn),
        stumme_spalte(conn, "norm_art",
                      "Sein/Sollen/Duerfen -- zwei Normen verschiedener Art konkurrieren nicht"),
        platzhalterfuellung(conn, "actor",
                            "wer die Aussage geschrieben hat -- traegt die ganze Herkunftskette"),
        platzhalterfuellung(conn, "model",
                            "welches Modell die Aussage geschrieben hat"),
    ]
    return [f for f in funde if f]


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE knowledge_nodes (norm_rang INTEGER, norm_art TEXT,
                    norm_entschieden_von TEXT, zurueckgezogen INTEGER DEFAULT 0)""")

    def fuelle(n, wer, art=None, rang=1, zurueck=0):
        for _ in range(n):
            conn.execute("INSERT INTO knowledge_nodes VALUES (?,?,?,?)", (rang, art, wer, zurueck))

    # Negativfall zuerst und er ist der wichtigste: unter der Mindestzahl
    # schweigt die Pruefung, auch bei 100 Prozent. Sonst meldet sie bei
    # zwei Zeilen einen Missstand.
    fuelle(3, "claude-code/opus-5")
    assert selbstzuschreibung(conn) is None, "unter der Mindestzahl wird nicht geurteilt"

    fuelle(30, "claude-code/opus-5")
    f = selbstzuschreibung(conn)
    assert f and "33 von 33" in f["befund"], f
    assert f["fehlklasse"] and f["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"

    # Gegenprobe: kippt die Mehrheit auf Menschen, schweigt die Pruefung.
    fuelle(40, "markus")
    assert selbstzuschreibung(conn) is None, "bei menschlicher Mehrheit kein Befund"

    # Zurueckgezogene zaehlen nicht mit.
    fuelle(100, "claude-code/opus-5", zurueck=1)
    assert selbstzuschreibung(conn) is None, "zurueckgezogene Zeilen duerfen nicht kippen"

    # Stumme Spalte: 100 Prozent meldet, 99 Prozent nicht.
    conn2 = sqlite3.connect(":memory:"); conn2.row_factory = sqlite3.Row
    conn2.execute("""CREATE TABLE knowledge_nodes (norm_rang INTEGER, norm_art TEXT,
                     norm_entschieden_von TEXT, zurueckgezogen INTEGER DEFAULT 0)""")
    for _ in range(25):
        conn2.execute("INSERT INTO knowledge_nodes VALUES (1, NULL, 'x', 0)")
    assert stumme_spalte(conn2, "norm_art", "z") is not None
    conn2.execute("INSERT INTO knowledge_nodes VALUES (1, 'sollen', 'x', 0)")
    assert stumme_spalte(conn2, "norm_art", "z") is None, "teilweise gefuellt ist kein Befund"

    # Platzhalterfuellung. Eigene Tabelle, weil gattung dazukommt.
    c3 = sqlite3.connect(":memory:"); c3.row_factory = sqlite3.Row
    c3.execute("""CREATE TABLE knowledge_nodes (actor TEXT, gattung TEXT,
                  zurueckgezogen INTEGER DEFAULT 0)""")

    def p3(n, actor, gattung='arbeitsbestand', zur=0):
        for _ in range(n):
            c3.execute("INSERT INTO knowledge_nodes VALUES (?,?,?)", (actor, gattung, zur))

    # Negativfall: unter der Mindestzahl schweigt sie, auch bei 100 Prozent.
    p3(5, "unbekannt")
    assert platzhalterfuellung(c3, "actor", "z") is None, "unter der Mindestzahl kein Urteil"

    # Grenzwert um die Schwelle: 79 Prozent schweigt, 80 Prozent meldet.
    c3.execute("DELETE FROM knowledge_nodes")
    p3(79, "unbekannt"); p3(21, "markus")
    assert platzhalterfuellung(c3, "actor", "z") is None, "79 Prozent ist unter der Schwelle"
    c3.execute("DELETE FROM knowledge_nodes")
    p3(80, "unbekannt"); p3(20, "markus")
    f3 = platzhalterfuellung(c3, "actor", "z")
    assert f3 and "80 von 100" in f3["befund"], f3
    assert f3["fehlklasse"] and f3["fehlalarm_kostet"], "Fehlklasse und Preis sind Pflicht"

    # Der Fehler, der beim Bau fast durchging: ein Nachschlagewerk mit
    # echtem Schreiber darf die Quote NICHT verduennen.
    p3(1000, "nasa_llis_import.py", gattung="nachschlagewerk")
    f4 = platzhalterfuellung(c3, "actor", "z")
    assert f4 and "80 von 100" in f4["befund"], ("Nachschlagewerk darf den Nenner nicht aufblaehen", f4)

    # Gegenprobe in die andere Richtung: echte Schreiber im Arbeitsbestand
    # muessen den Melder wieder zum Schweigen bringen.
    p3(200, "claude-code/opus-5")
    assert platzhalterfuellung(c3, "actor", "z") is None, "echte Schreiber loeschen den Befund"

    # Leerer Text zaehlt wie 'unbekannt' -- sonst faellt er durch beide Netze.
    c3.execute("DELETE FROM knowledge_nodes")
    p3(30, ""); p3(2, "markus")
    assert platzhalterfuellung(c3, "actor", "z") is not None, "leerer Text ist auch blind"

    print("selftest ok (13 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    conn = _verbindung(a.db)
    funde = alle(conn)
    conn.close()

    if a.melder:
        if funde:
            zeilen = [f"{f['befund']} ({f['fehlklasse']})" for f in funde]
            print("⚠️ Pruefer: " + "\n   ".join(zeilen))
        return

    if not funde:
        print("Pruefer: nichts anzumerken.")
        return
    for f in funde:
        print(f"[{f['pruefung']}] {f['befund']}")
        print(f"   Fehlklasse:  {f['fehlklasse']}")
        print(f"   Fehlalarm:   {f['fehlalarm_kostet']}")


if __name__ == "__main__":
    main()
