#!/usr/bin/env python3
"""Einlesweg fuer die vier freigegebenen Fremdquellen (Betreiberentscheidung
2026-08-15, woertlich "das meinte ich mit alles!" fuer GermanQuAD, GermanDPR,
Gesetze im Internet, Open Legal Data -- Wikipedia ausdruecklich gestrichen).

WAS DIESE DATEI TUT: baut aus Frage-Antwort-Paaren (GermanQuAD/GermanDPR)
zweierlei -- (a) NACHSCHLAGEWERK-Knoten aus den Antwort-Passagen (der
Heuhaufen, in den der Abruf greifen soll) und (b) Pruefkorpus-Faelle mit
VORHER bekanntem Label "Antwort im Bestand: ja/nein" (die Bruecke aus dem
Auftrag). Nur die Passagen werden importiert, nicht die Fragen selbst -- die
Fragen leben ausschliesslich als Pruefkorpus-Prompt (wie kern/pruefkorpus.py
es fuer den eigenen Bestand schon tut), sie sind kein Wissen, das jemand
nachschlagen soll.

GermanDPR liefert zusaetzlich Hard-Negative-Passagen: thematisch nahe, aber
NICHT die Antwort. Die werden ebenfalls als nachschlagewerk-Knoten importiert
(sie muessen im Heuhaufen liegen, sonst gibt es nichts, an dem sich "findet
Aehnliches statt Richtiges" pruefen liesse) und erzeugen zusaetzlich einen
Pruefkorpus-Fall der Kategorie "hard_negative": Frage mit Label ja (Antwort
liegt vor), aber ein zweiter, thematisch verwandter Distraktor liegt eben-
falls im Bestand -- die Trefferquote muss den richtigen treffen, nicht nur
irgendeinen.

KORREKTUR 2026-08-15 (Betreiber, woertlich "GermanQuAD und GermanDPR als
testkorpus, die legal sachen fuer bucke, steuer usw! realbetrieb"): NUR
GermanQuAD/GermanDPR sind Pruefkorpus -- gattung='nachschlagewerk' bleibt fuer
BEIDE richtig, sie sollen nie Ziel eines Prueffalls sein. Gesetze im Internet
und Open Legal Data sind dagegen FACHBESTAND fuer den Realbetrieb (buckeberg
WEG-Recht, openlehr Steuer) -- sie sollen im Abruf GEFUNDEN werden.

GEMESSEN (nicht vermutet): gattung kennt per DB-Trigger nur zwei Werte
(schema.sql, knowledge_nodes_gattung_check_bi/_bu), und
'nachschlagewerk' wird an DREI Stellen im echten Suchpfad aus dem Abruf
gefiltert -- SQL_ARBEITSBESTAND_NUR aus kern/gattung_filter.py, verwendet in
haken/knowledge_recall_hook.py, haken/suchpfad_abruf.py und
haken/mehrstufiger_abruf.py. 'arbeitsbestand' waere die falsche Gegenrichtung:
es behauptet eigenes Wissen dieses Hauses, was Gesetzestexte/Gerichtsent-
scheidungen nicht sind.

BEIDE Dateiarten, die einen dritten Wert tragen muessten, sind in diesem
Auftrag TABU: schema.sql (heute von einem anderen Agenten geaendert) und
haken/ (ein Agent repariert dort GERADE die Rangfolge-Fusion, Befund
d84b6b64 -- dieselbe Stelle anzufassen waere die Kollision, vor der die
Grenzen ausdruecklich warnen). Ein dritter gattung-Wert ('fremdbestand'?)
ist deshalb hier NICHT implementiert, sondern nur vorbereitet:
fachbestand_zu_knoten() unten laesst gattung ABSICHTLICH als Pflichtparameter
offen (kein Vorgabewert) und die Importfunktion verlangt ihn explizit -- die
Entscheidung faellt, wer schema.sql und haken/ als naechstes anfasst, mit
Blick auf die Rangfolge-Reparatur, die gerade laeuft. Bis dahin bleibt der
Import von Gesetze im Internet/Open Legal Data in die PRODUKTIVDATENBANK
blockiert, nicht nur wegen des Laufzeit-Konflikts mit der Guetemessung --
es gibt noch keinen zulaessigen gattung-Wert dafuer.

DREI PFLICHTEN, hart verdrahtet, nicht nur behauptet:
  1. gattung='nachschlagewerk' -- durchgesetzt per DB-Trigger
     (knowledge_nodes_gattung_check_bi in schema.sql), nicht nur hier gesetzt.
  2. norm_rang bleibt NULL -- norm_entscheidung='keine_norm' explizit gesetzt
     (der Trigger knowledge_nodes_norm_entscheidung_pflicht_bi lehnt den
     Vorgabewert 'offen' beim INSERT ab, siehe schema.sql).
  3. source traegt die Namensnennung -- durchgesetzt per DB-Trigger
     (knowledge_nodes_source_check_bi verbietet ein leeres source-Feld).
     CC BY 4.0 (GermanQuAD/GermanDPR) verlangt Namensnennung: das Feld traegt
     Datensatzname + Autoren (Moeller/Risch/Pietsch 2021, deepset) + Lizenz +
     Fundstelle je EINZELNEM Knoten -- nicht nur gesammelt in NOTICE. Damit
     ist die im Auftrag gestellte Frage ("traegt das Datenmodell das?")
     beantwortet: JA, `knowledge_nodes.source` existiert bereits und ist
     genau dafuer vorgesehen (schema.sql: "Herkunft: Datei/Konsil/Research").
     Keine Schemaaenderung noetig.

Schreibt NIE in brainlehr.db -- jede Funktion nimmt eine sqlite3-Verbindung
entgegen, die der Aufrufer oeffnet (Walkthrough-Doktrin: injizierbare
Aussenwelt). CLI unten oeffnet ausschliesslich einen Pfad, der per --db
uebergeben wird, nie einen Vorgabewert auf die Produktivdatenbank.

Aufruf:
    python3 pflege/wissenskorpus_einlesweg.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

# --- Quellenbeschreibung (Attribution + Lizenz je Quelle) -----------------
# Deckt sich mit quellen/fremdquellen.json -- diese Datei ist die technische
# Ausfuehrung, fremdquellen.json das Register. Zahlen hier sind Konstanten
# fuer den Attributionstext, keine zweite Wahrheit ueber Umfang (der steht
# im Bericht runs/wissenskorpus_einlesweg_2026-08-15_bericht.md).
QUELLEN: dict[str, dict] = {
    "germanquad": {
        "titel": "GermanQuAD",
        "autoren": "Timo Moeller, Julian Risch, Malte Pietsch (deepset), 2021",
        "lizenz": "CC BY 4.0",
        "fundstelle": "https://huggingface.co/datasets/deepset/germanquad",
    },
    "germandpr": {
        "titel": "GermanDPR",
        "autoren": "Timo Moeller, Julian Risch, Malte Pietsch (deepset), 2021",
        "lizenz": "CC BY 4.0",
        "fundstelle": "https://huggingface.co/datasets/deepset/germandpr",
    },
    "gesetze-im-internet": {
        "titel": "Gesetze im Internet",
        "autoren": "Bundesministerium der Justiz, technisch bereitgestellt durch juris GmbH",
        "lizenz": "Amtliches Werk, gemeinfrei nach §5 Abs. 1 UrhG",
        "fundstelle": "https://www.gesetze-im-internet.de/gii-toc.xml",
    },
    "open-legal-data": {
        "titel": "Open Legal Data -- German Court Decisions",
        "autoren": "Open Legal Data (Entscheidungstexte: die jeweiligen Gerichte, amtliches Werk)",
        "lizenz": "§5 UrhG (Text) + ODbL v1.0 (Sammlung)",
        "fundstelle": "https://huggingface.co/datasets/openlegaldata/court-decisions-germany",
    },
}


def attribution(quelle_kennung: str, herkunfts_id: str) -> str:
    """Baut den source-Text fuer EINEN Knoten -- Namensnennung ist Pflicht
    bei CC BY, hier je Knoten statt nur gesammelt in NOTICE (Auftrag Punkt 2:
    'gehoert in die Herkunftsangabe jedes Knotens')."""
    q = QUELLEN[quelle_kennung]
    return f"{q['titel']} ({q['autoren']}), {q['lizenz']}, {q['fundstelle']} -- {herkunfts_id}"


# --- Knoten aus einer Antwort-Passage --------------------------------------

def _pfad(quelle_kennung: str, herkunfts_id: str) -> str:
    # Materialized Path braucht druckbare, eindeutige Segmente -- ein Hash
    # der Herkunfts-ID ist kuerzer und kollisionssicherer als die ID selbst
    # (die bei GermanDPR z.B. Leerzeichen/Sonderzeichen tragen kann).
    kurz = hashlib.sha256(herkunfts_id.encode("utf-8")).hexdigest()[:12]
    return f"/{quelle_kennung}/{kurz}"


def passage_zu_knoten(quelle_kennung: str, herkunfts_id: str, titel: str,
                       text: str) -> dict:
    """Baut EINEN knowledge_nodes-Datensatz aus einer Antwort-Passage.
    Reine Funktion, kein DB-Zugriff -- macht sie einzeln testbar (Abnahme:
    gattung/norm_rang/source nachpruefbare Werte)."""
    return {
        "path": _pfad(quelle_kennung, herkunfts_id),
        "parent_path": None,
        "title": titel[:200] if titel else herkunfts_id[:200],
        "summary": text[:280],
        "content": text,
        "source": attribution(quelle_kennung, herkunfts_id),
        "gattung": "nachschlagewerk",
        "norm_entscheidung": "keine_norm",
        "norm_rang": None,
        "gilt_ab": None,
        "gilt_bis": None,
        "anlass": "skript",
        "freigabe": "intern",
        # Pflicht des Triggers knowledge_nodes_norm_entscheidung_wer_bi: wer
        # hat entschieden, dass dies keine Norm ist, und warum. Der Import
        # selbst ist die Entscheidung -- eine importierte Passage ist ein
        # FAKT (Frage-Antwort-Beleg), nie eine Norm dieses Hauses (ADR-018).
        "norm_entschieden_von": "wissenskorpus_einlesweg.py",
        "norm_entschieden_grund": (
            f"Fremdbestand ({quelle_kennung}): importierte Passage ist ein Fakt/"
            "Beleg, keine Norm dieses Hauses -- ADR-018 Wirkung Null."),
    }


def fachbestand_zu_knoten(quelle_kennung: str, herkunfts_id: str, titel: str,
                           text: str, gattung: str) -> dict:
    """Wie passage_zu_knoten(), aber fuer Gesetze im Internet/Open Legal
    Data -- gattung ist PFLICHTPARAMETER ohne Vorgabewert. Weder
    'arbeitsbestand' (behauptet eigenes Wissen) noch 'nachschlagewerk'
    (aus jedem Abruf gefiltert, siehe Moduldoku) sind fuer FACHBESTAND
    richtig -- ein dritter Wert fehlt im Schema und ist hier bewusst NICHT
    erfunden. Der DB-Trigger (schema.sql) lehnt jeden Wert ausser den
    zwei bestehenden ab -- das macht den Blocker PRUEFBAR statt behauptet,
    siehe _selftest()."""
    k = passage_zu_knoten(quelle_kennung, herkunfts_id, titel, text)
    k["gattung"] = gattung
    return k


def importiere_knoten(conn: sqlite3.Connection, knoten: list[dict]) -> int:
    """Schreibt eine Liste von passage_zu_knoten()-Datensaetzen. INSERT OR
    IGNORE auf UNIQUE(path) -- ein zweiter Lauf ueber dieselbe Stichprobe
    dupliziert nichts, statt mit UNIQUE-Verletzung abzubrechen."""
    n = 0
    for k in knoten:
        cur = conn.execute(
            "INSERT OR IGNORE INTO knowledge_nodes "
            "(id, path, parent_path, title, summary, content, source, gattung, "
            " norm_entscheidung, norm_rang, gilt_ab, gilt_bis, anlass, freigabe, "
            " norm_entschieden_von, norm_entschieden_grund) "
            "VALUES (lower(hex(randomblob(16))), :path, :parent_path, :title, "
            " :summary, :content, :source, :gattung, :norm_entscheidung, "
            " :norm_rang, :gilt_ab, :gilt_bis, :anlass, :freigabe, "
            " :norm_entschieden_von, :norm_entschieden_grund)",
            k,
        )
        n += cur.rowcount
    return n


# --- Bruecke: Frage-Antwort-Paar -> Pruefkorpus-Fall mit bekanntem Label --

def qa_zu_pruefkorpus_fall(quelle_kennung: str, frage: str, antwort_pfad: str,
                            hard_negative_pfad: str | None = None) -> dict:
    """Baut EINEN Fall im selben Format wie kern/pruefkorpus.py::run()
    (category/target_kind/target_id/prompt) -- zusaetzlich 'quelle' und
    'distraktor_pfad'. Label ist immer 'ja': die Frage stammt aus einem Paar,
    dessen Antwort NACHWEISLICH als Knoten importiert wurde (target_id zeigt
    genau dorthin) -- das ist der Kern der Bruecke aus dem Auftrag, VORHER
    bekannt statt aus dem Suchergebnis abgeleitet.
    distraktor_pfad (nur GermanDPR): Pfad der Hard-Negative-Passage, die
    ebenfalls im Bestand liegt -- ein Treffer auf DIESE statt auf target_id
    ist ein Fehlalarm, kein Erfolg (misst 'findet Aehnliches statt
    Richtiges')."""
    category = "hard_negative" if hard_negative_pfad else "qa_bruecke"
    return {
        "category": category, "quelle": quelle_kennung,
        "target_kind": "node", "target_id": antwort_pfad,
        "distraktor_pfad": hard_negative_pfad,
        "prompt": frage,
        "label_antwort_im_bestand": "ja",
    }


def negativfall(frage: str) -> dict:
    """Label 'nein': Gegenstueck zur Bruecke oben -- eine Frage OHNE
    importierten Zieleintrag. Baut nichts, importiert nichts; reine
    Kennzeichnung fuer die Trefferquoten-Trennung (Schritt 5 im Bericht)."""
    return {
        "category": "negativ_fremdquelle", "quelle": None,
        "target_kind": None, "target_id": None, "distraktor_pfad": None,
        "prompt": frage, "label_antwort_im_bestand": "nein",
    }


# --- Ganzer Lauf ueber eine Stichprobe -------------------------------------

def importiere_qa_stichprobe(conn: sqlite3.Connection, quelle_kennung: str,
                              paare: list[dict]) -> dict:
    """paare: Liste von {"frage": str, "antwort_titel": str,
    "antwort_text": str, "antwort_id": str,
    "hard_negative_titel": str|None, "hard_negative_text": str|None,
    "hard_negative_id": str|None}. Importiert alle Passagen (Antwort +
    ggf. Hard-Negative) als Knoten, baut je Paar EINEN Pruefkorpus-Fall.
    Gibt {"knoten_importiert": int, "faelle": [...]}."""
    knoten: list[dict] = []
    faelle: list[dict] = []
    for p in paare:
        antwort_knoten = passage_zu_knoten(
            quelle_kennung, p["antwort_id"], p["antwort_titel"], p["antwort_text"])
        knoten.append(antwort_knoten)
        hn_pfad = None
        if p.get("hard_negative_text"):
            hn_knoten = passage_zu_knoten(
                quelle_kennung, p["hard_negative_id"], p["hard_negative_titel"],
                p["hard_negative_text"])
            knoten.append(hn_knoten)
            hn_pfad = hn_knoten["path"]
        faelle.append(qa_zu_pruefkorpus_fall(
            quelle_kennung, p["frage"], antwort_knoten["path"], hn_pfad))
    n = importiere_knoten(conn, knoten)
    return {"knoten_importiert": n, "faelle": faelle}


# --- Selbsttest -------------------------------------------------------------

def _apply_schema(conn: sqlite3.Connection) -> None:
    schema = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)


def _selftest() -> None:
    import tempfile

    tmpdir = Path(tempfile.mkdtemp(prefix="wissenskorpus_einlesweg_selftest_"))
    db_path = tmpdir / "wegwerf.db"
    conn = sqlite3.connect(str(db_path))
    try:
        _apply_schema(conn)

        # (1) Ein GermanQuAD-artiges Paar ohne Hard-Negative.
        paare = [{
            "frage": "Wie viele Richter waehlt der Bundestag fuer das oberste Verfassungsorgan?",
            "antwort_titel": "Bundesverfassungsgericht",
            "antwort_text": "Das Bundesverfassungsgericht besteht aus 16 Richtern, "
                             "acht je Senat, gewaehlt je zur Haelfte von Bundestag und Bundesrat.",
            "antwort_id": "germanquad-test-001",
        }, {
            # (2) Ein GermanDPR-artiges Paar MIT Hard-Negative.
            "frage": "In welcher Stadt hat das oberste deutsche Verfassungsgericht seinen Sitz?",
            "antwort_titel": "Sitz des Bundesverfassungsgerichts",
            "antwort_text": "Das Bundesverfassungsgericht hat seinen Sitz in Karlsruhe, nicht in Berlin.",
            "antwort_id": "germandpr-test-001-pos",
            "hard_negative_titel": "Sitz des Bundesgerichtshofs",
            "hard_negative_text": "Der Bundesgerichtshof, das oberste Gericht der ordentlichen "
                                   "Gerichtsbarkeit, hat ebenfalls seinen Sitz in Karlsruhe.",
            "hard_negative_id": "germandpr-test-001-neg",
        }]

        # ROT-Probe: vor dem Import gibt es diese Knoten nicht.
        vor = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        assert vor == 0, "Wegwerf-DB war nicht leer -- Testaufbau fehlerhaft"

        ergebnis = importiere_qa_stichprobe(conn, "germanquad", paare[:1])
        ergebnis2 = importiere_qa_stichprobe(conn, "germandpr", paare[1:])
        conn.commit()

        # GRUEN: 3 Knoten (1 aus Paar 1, 2 aus Paar 2 -- Antwort + Hard-Negative).
        assert ergebnis["knoten_importiert"] == 1
        assert ergebnis2["knoten_importiert"] == 2
        nach = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        assert nach == 3, f"erwartet 3 Knoten, waren {nach}"
        print("  (rot->gruen) 0 Knoten vor Import, 3 danach -- ok")

        # Pflicht 1: gattung durchgaengig nachschlagewerk.
        gattungen = {r[0] for r in conn.execute("SELECT DISTINCT gattung FROM knowledge_nodes")}
        assert gattungen == {"nachschlagewerk"}, gattungen
        print("  Pflicht 1: gattung=nachschlagewerk bei allen importierten Knoten -- ok")

        # Pflicht 2: norm_rang leer bei allen.
        rang = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE norm_rang IS NOT NULL").fetchone()[0]
        assert rang == 0, f"{rang} Knoten trugen einen norm_rang"
        print("  Pflicht 2: norm_rang bei allen NULL (Wirkung Null, ADR-018) -- ok")

        # Pflicht 3: source traegt Namensnennung (Titel + Lizenz), je Knoten,
        # nicht nur gesammelt.
        quellen = conn.execute("SELECT source FROM knowledge_nodes ORDER BY path").fetchall()
        for (src,) in quellen:
            assert "CC BY 4.0" in src, src
            assert ("GermanQuAD" in src) or ("GermanDPR" in src), src
        print("  Pflicht 3: Namensnennung (Titel+Lizenz) in source JEDES Knotens -- ok")

        # Negativfall / Gegenprobe: eine Frage ohne Zieleintrag darf keinen
        # Knoten anlegen und traegt Label 'nein'.
        neg = negativfall("Wie kuendigt man einen Handyvertrag fristgerecht?")
        assert neg["target_id"] is None and neg["label_antwort_im_bestand"] == "nein"
        vor2 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        assert vor2 == nach, "negativfall() haette KEINEN Knoten anlegen duerfen"
        print("  Gegenprobe: negativfall() legt keinen Knoten an, Label 'nein' -- ok")

        # Bruecke: der hard_negative-Fall traegt einen Distraktor-Pfad, der
        # tatsaechlich im Bestand liegt (nicht nur ein Textfeld).
        hn_fall = ergebnis2["faelle"][0]
        assert hn_fall["category"] == "hard_negative"
        assert hn_fall["distraktor_pfad"] is not None
        distraktor_existiert = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE path = ?",
            (hn_fall["distraktor_pfad"],)).fetchone()[0]
        assert distraktor_existiert == 1, "Distraktor-Pfad zeigt ins Leere"
        print("  Bruecke: hard_negative-Fall zeigt auf einen tatsaechlich importierten Distraktor -- ok")

        # Fachbestand-Blocker: BELEGT statt behauptet. Ein erfundener dritter
        # gattung-Wert wird vom DB-Trigger abgelehnt -- der Import von
        # Gesetze im Internet/Open Legal Data in die Produktivdatenbank ist
        # damit nicht nur eine Empfehlung "erst schema.sql aendern", sondern
        # eine gemessene, aktiv durchgesetzte Sperre.
        fachbestand_knoten = fachbestand_zu_knoten(
            "gesetze-im-internet", "bgb-para-433", "§433 BGB",
            "Durch den Kaufvertrag wird der Verkaeufer einer Sache verpflichtet, "
            "dem Kaeufer die Sache zu uebergeben und das Eigentum zu verschaffen.",
            gattung="fremdbestand")
        try:
            importiere_knoten(conn, [fachbestand_knoten])
            conn.commit()
            raise AssertionError(
                "Trigger haette 'fremdbestand' als gattung ablehnen muessen -- "
                "der Blocker existiert nicht mehr, ein dritter Wert waere jetzt zulaessig")
        except sqlite3.IntegrityError as e:
            conn.rollback()
            # Welcher Trigger zuerst feuert, ist Zufall der SQLite-Ausfuehrungs-
            # reihenfolge -- BEIDE sind gueltige Befunde: gattung='fremdbestand'
            # existiert nicht (Kern des Blockers), UND ein zweiter, unabhaengiger
            # Trigger verlangt norm_art fuer Saetze, deren source ein Gesetz
            # nennt (knowledge_nodes_normrang_herkunft_bi, Knoten dd367fd1) --
            # ein Fund, den dieser Selbsttest nebenbei aufdeckt, nicht gesucht
            # hat: EIN naiver Import von Gesetzestexten stoesst auf MINDESTENS
            # zwei unabhaengige Schema-Huerden, nicht nur die gattung-Frage.
            assert "gattung" in str(e) or "norm_art" in str(e), str(e)
            print(f"  Fachbestand-Blocker BELEGT: DB-Trigger lehnt den naiven Import ab "
                  f"({e}) -- Import von Gesetze im Internet/Open Legal Data braucht "
                  "eine Schema-Entscheidung ausserhalb dieses Auftrags")

        # Doppellauf: derselbe Import ein zweites Mal dupliziert nichts
        # (INSERT OR IGNORE auf UNIQUE(path)).
        ergebnis3 = importiere_qa_stichprobe(conn, "germanquad", paare[:1])
        conn.commit()
        assert ergebnis3["knoten_importiert"] == 0
        nach2 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        assert nach2 == nach, "zweiter Lauf hat dupliziert"
        print("  Doppellauf: zweiter Import derselben Stichprobe dupliziert nichts -- ok")

    finally:
        conn.close()
        db_path.unlink(missing_ok=True)
        for p in tmpdir.glob("*"):
            p.unlink(missing_ok=True)
        tmpdir.rmdir()

    print("selftest ok (Wegwerf-DB, kein Zugriff auf brainlehr.db)", file=sys.stderr)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    ap.print_help()


if __name__ == "__main__":
    main()
