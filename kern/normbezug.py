#!/usr/bin/env python3
"""normbezug.py -- erkennt Normzitate in einer Antwort und prueft ihren Beleg.

ANLASS (Betreiber, 2026-08-10): "wir brauchen etwas das in deinen antworten
erkennt ob du zb gesetzt, din norm usw benutzt, wenn ja dann muss brainlehr
nachschauen gibt es eine valide quelle in brainlehr, wenn nicht dann muss dies
nachgeholt werden! dein lmm wissen ist ja eingefrohren, muss nicht mehr stimmen!"

DIE FEHLKLASSE, gemessen am selben Tag (L-62b600): Ich nannte im Gespraech
"§ 87 Abs. 1 Nr. 6 BetrVG -- geeignet, nicht gedacht". Norm, Nummer und
Gegenstand stimmten; der Wortlaut lautet aber "die dazu BESTIMMT sind". Die
Verschaerfung auf die objektive Eignung war ungeprueftes Modellwissen -- und
genau der Teil, auf den jemand handelt. Im Wissensknoten stand zwei Nachrichten
vorher ein sauberer Herkunftsvorbehalt; im Chat fiel er weg, weil dort kein
Pflichtfeld ihn erzwingt. Dieses Werkzeug ist das fehlende Pflichtfeld.

ZWEI GRUENDE, WARUM EIN BELEG NOETIG IST -- der zweite wird meist vergessen:
1. Das Modellwissen kann falsch sein (Halluzination, Verwechslung, erfundene
   Verschaerfung).
2. Das Modellwissen ist EINGEFROREN. Selbst eine damals richtige Angabe kann
   heute ueberholt sein -- Gesetze werden geaendert, Normen zurueckgezogen,
   Fassungen abgeloest. Darum reicht "steht im Bestand" NICHT: ein Beleg hat
   ein Datum, und ab einem Alter ist er nachzupruefen (PRUEFALTER_TAGE).

DIE MUSTERLISTE IST NICHT NEU ERFUNDEN. Sie stammt aus dem bereits vorhandenen
Trigger knowledge_nodes_normrang_herkunft_bi in schema.sql, der Normen fremder
Herkunft an genau diesen Woertern erkennt (gesetz, verordnung, urteil, az.,
BGBl, Richtlinie, DIN, EN, ISO, IEC, BSI, WCAG, RFC). Derselbe Katalog, der
Fremdnormen von Hausnormen trennt, erkennt Normzitate im Fliesstext.

WAS DIESES WERKZEUG NICHT TUT: Es prueft NICHT, ob eine Aussage ueber eine Norm
richtig ist -- das kann kein Programm. Es prueft, ob zu einer zitierten
Fundstelle ueberhaupt ein Beleg im Bestand liegt und wie alt er ist. Der Schluss
bleibt beim Menschen (dieselbe Haltung wie kanonymitaet.py, das die Zahl k nennt
und nie das Wort "anonym" verwendet).

FEHLKLASSE: unbelegtes Normzitat aus Modellwissen.
PREIS EINES FEHLALARMS: gering -- eine Wiedervorlage zu viel. Der umgekehrte
Fehler (ein unbelegtes Zitat bleibt unbemerkt) ist der teure, siehe L-62b600.

Aufruf:
    python3 normbezug.py --text "... § 87 Abs. 1 Nr. 6 BetrVG ..."
    python3 normbezug.py --stop        # Stop-Hook: liest die letzte Antwort
    python3 normbezug.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402 -- liefert DB, siehe haken/ort.py (L-6c6661)

# ERWAEHNUNG vs. GELTUNG (Auftrag 2026-08-12, Befund 7a6b27e1): ein LIKE-Treffer
# auf Reihe+Nummer beweist nur, dass ein Knoten die Norm NENNT -- nicht, dass
# sie noch gilt. Der Knoten 7a6b27e1 nennt "GEG" und "§ 71" nur, um ihre
# Streichung zu dokumentieren; belegt() nannte das bislang "belegt", das
# Gegenteil des Befunds. Zwei Signale trennen die Faelle, keines davon aus
# einer zweiten, selbst erfundenen Geltungspruefung -- die kanonische Formel
# fuer gilt_ab/gilt_bis steht bereits in normkraft.py::in_kraft
# (gilt_ab <= stichtag AND (gilt_bis IS NULL OR gilt_bis >= stichtag)), hier
# nur als Stringvergleich wiederholt, nicht neu erfunden:
#   1. STRUKTURELL: gilt_bis des juengsten Treffers liegt vor dem Stichtag.
#      Verlaesslich, aber am Bestand fast wirkungslos -- siehe Befund unten.
#   2. TEXTLICH: der Treffer nennt Streichung/Aufhebung/Ersetzung im Wortlaut.
#      SCHWAECHE, ausdruecklich: das ist eine Wortliste. Wer "§ 71 GEG faellt
#      weg" statt "gestrichen" schreibt, faellt durch. Besser als der Status
#      quo (gar keine Pruefung), aber kein Ersatz fuer eine echte Geltungs-
#      Annotation -- deshalb bleibt gilt_bis die vorrangige Pruefung, die
#      Wortliste nur der Fallback fuer den (heute haeufigeren) Fall, dass
#      gilt_bis nie gepflegt wurde.
# BEFUND ZUM BESTAND (2134 Knoten, gemessen): gilt_bis ist bei 2 Knoten
# gesetzt, zurueckgezogen bei 4 -- beide Male Test-/Probeknoten, keiner davon
# eine echte Rechtsnorm. Eine allein auf diese Felder gebaute Pruefung waere
# am heutigen Bestand wirkungslos gewesen; das ist der eigentliche Befund,
# nicht nur eine Randnotiz. zurueckgezogen bleibt darum aus dieser Pruefung
# aussen vor (WHERE zurueckgezogen = 0 unveraendert): die vier vorhandenen
# Faelle sind Aufraeum-Ruecknahmen ohne Bezug zur Norm-Geltung, ein Knoten
# als "ausser_kraft" zu werten, NUR weil er zurueckgezogen ist, waere die
# gleiche Verwechslung wie oben -- Rueckzug des KNOTENS ist nicht dasselbe
# wie Aufhebung der NORM.
_AUFHEBUNG = re.compile(
    r"(?i)\b(ersatzlos gestrichen|gestrichen|aufgehoben|außer kraft|"
    r"ausser kraft|abgelöst|abgeloest|ersetzt durch|nicht mehr in kraft|"
    r"nicht mehr gültig|nicht mehr gueltig)\b")


def _aufhebung_im_treffer(row: sqlite3.Row) -> bool:
    text = " ".join(str(row[f] or "") for f in ("title", "summary", "content"))
    return bool(_AUFHEBUNG.search(text))


# Ab diesem Alter gilt ein Beleg als nachpruefbeduerftig. 365 Tage, weil
# Gesetzesaenderungen in Deutschland ueblicherweise zum Jahreswechsel oder
# quartalsweise in Kraft treten -- ein Jahr faengt jede davon einmal ein.
# Bewusst KEINE Vorgabe von 0 (dann waere jeder Beleg sofort faellig und die
# Meldung nutzlos) und keine von 5 Jahren (dann faengt sie nichts).
PRUEFALTER_TAGE = 365


@dataclass(frozen=True)
class Fundstelle:
    """Ein erkanntes Normzitat, auf eine vergleichbare Kennung gebracht."""
    kennung: str      # z.B. "BetrVG §87", "DSGVO Art.6", "ISO 9241-110"
    roh: str          # wie es im Text stand
    art: str          # gesetz | eu | technisch


# --- Erkennung -------------------------------------------------------------
# Drei Bauformen, weil deutsche, europaeische und technische Normen verschieden
# zitiert werden. Jede liefert dieselbe normalisierte Kennung, damit der
# Bestandsabgleich EINE Form vergleichen kann und nicht zwanzig Schreibweisen.

# "§ 87 Abs. 1 Nr. 6 BetrVG" / "§§ 305 ff. BGB" / "§ 24 Abs. 7 WEG"
_PARAGRAF = re.compile(
    r"§§?\s*(\d+[a-z]?)"                      # Paragraf
    r"(?:\s*(?:Abs\.|Absatz)\s*\d+)?"          # Absatz (verworfen, s.u.)
    r"(?:\s*(?:Nr\.|Nummer)\s*\d+)?"
    r"(?:\s*(?:S\.|Satz)\s*\d+)?"
    r"(?:\s*(?:lit\.|Buchst\.)\s*[a-z])?"
    r"(?:\s*(?:ff?\.))?"
    r"\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{1,12}(?:G|VG|GB|O|VO|StGB|BGB)?)\b"
)

# "Art. 6 Abs. 1 lit. f DSGVO" / "Artikel 15 DSGVO"
_ARTIKEL = re.compile(
    r"\bArt(?:ikel|\.)\s*(\d+[a-z]?)"
    r"(?:\s*(?:Abs\.|Absatz)\s*\d+)?"
    r"(?:\s*(?:lit\.|Buchst\.)\s*[a-z])?"
    r"(?:\s*(?:Nr\.|Nummer)\s*\d+)?"
    r"\s*([A-ZÄÖÜ]{2,12})\b"
)

# "DIN EN ISO 9241-110", "ISO 27001", "BSI TR-02102-1", "RFC 7914", "WCAG 2.2"
_TECHNISCH = re.compile(
    r"\b(DIN(?:\s+EN)?(?:\s+ISO)?|EN(?:\s+ISO)?|ISO(?:/IEC)?|IEC|BSI|WCAG|RFC)"
    r"\s+([A-Z]{0,3}-?[\d][\d.\-]*)"
)

# HAUSNORMEN -- der haeufigere und gefaehrlichere Fall (Betreiber, 2026-08-10:
# "muessen wir hausnormen nicht auch gegenpruefen falls kontextfenster schon
# uebergelaufen ist usw?").
#
# Nach einer Kontextverdichtung bleibt die KENNUNG im Gedaechtnis, der Inhalt
# nicht: "laut ADR-027", "L-adfb33 sagt". Das ist dann Erinnerung, nicht Wissen
# -- dieselbe Fehlklasse wie beim eingefrorenen Modellwissen, nur mit kuerzerer
# Halbwertszeit. Und eine erfundene ADR-Nummer ist SCHLIMMER als eine erfundene
# Gesetzesnummer, weil sie vertraut klingt und niemand sie nachschlaegt.
#
# Bei Hausnormen ist die Frage darum eine andere: nicht "gibt es eine Quelle",
# sondern "existiert diese Kennung ueberhaupt". Ein Treffer im eigenen Bestand
# ist hier der Beleg selbst, kein Ersatz fuer eine externe Quelle.
_HAUSNORM = re.compile(
    r"\b(ADR-(?:[A-Z]{1,3}-)?\d{1,3}"      # ADR-001, ADR-F-026, ADR-OH-020
    r"|OD\d{1,2}"                           # OD13 (AKA2026-Direktiven)
    r"|L-[0-9a-f]{6}"                       # Lehren-Kennung
    r")\b")

# Blosse Erwaehnungen ohne Fundstelle ("laut Gesetz", "eine EU-Verordnung").
# Sie sind KEIN Zitat und werden nicht gemeldet -- sonst ertrinkt die Meldung
# in Rauschen und wird abgeschaltet. Nur benannt, damit klar ist, dass die
# Entscheidung getroffen wurde und nicht vergessen.
_VAGE = re.compile(r"(?i)\b(laut Gesetz|gesetzlich vorgeschrieben|eine? (EU-)?Verordnung)\b")


def erkenne(text: str) -> list[Fundstelle]:
    """Alle Normzitate im Text, dublettenfrei, in Reihenfolge des Auftretens.

    Der ABSATZ geht bewusst NICHT in die Kennung ein: ein Beleg zu § 87 BetrVG
    belegt auch Absatz 1 Nummer 6, und eine Kennung je Absatz wuerde denselben
    Beleg zwanzigmal als fehlend melden. Der Rohtext bleibt daneben erhalten,
    damit die Meldung zeigt, was tatsaechlich zitiert wurde."""
    treffer: list[Fundstelle] = []
    gesehen: set[str] = set()

    def add(kennung: str, roh: str, art: str) -> None:
        if kennung not in gesehen:
            gesehen.add(kennung)
            treffer.append(Fundstelle(kennung, roh.strip(), art))

    for m in _PARAGRAF.finditer(text):
        add(f"{m.group(2)} §{m.group(1)}", m.group(0), "gesetz")
    for m in _ARTIKEL.finditer(text):
        add(f"{m.group(2)} Art.{m.group(1)}", m.group(0), "eu")
    for m in _TECHNISCH.finditer(text):
        reihe = re.sub(r"\s+", " ", m.group(1))
        # Satzzeichen abschneiden: "WCAG 2.2." am Satzende darf nicht zu einer
        # anderen Kennung werden als "WCAG 2.2" mittendrin.
        add(f"{reihe} {m.group(2).rstrip('.-')}", m.group(0), "technisch")
    for m in _HAUSNORM.finditer(text):
        add(m.group(1), m.group(0), "hausnorm")
    return treffer


# --- Bestandsabgleich ------------------------------------------------------

def _db_pfad() -> Path:
    return ort.DB


def _suchbegriffe(f: Fundstelle) -> list[str]:
    """Wonach im Bestand gesucht wird. Mehrere Schreibweisen, weil ein Beleg
    "§ 87 BetrVG" oder "BetrVG § 87" oder "BetrVG §87" heissen kann."""
    if f.art == "hausnorm":
        return [f.kennung]          # die Kennung IST die Fundstelle
    if f.art == "technisch":
        return [f.kennung, f.kennung.replace(" ", "")]
    reihe, nummer = f.kennung.split(" ", 1)
    zeichen = nummer[0]           # § oder A(rt.)
    zahl = nummer.lstrip("§").replace("Art.", "")
    return [f"{reihe} {nummer}", f"{nummer} {reihe}",
            f"{zeichen} {zahl} {reihe}", f"{zeichen}{zahl} {reihe}"]


def belegt(f: Fundstelle, pfad: Path | None = None,
           jetzt: datetime | None = None) -> dict:
    """Liegt zu dieser Fundstelle ein Beleg im Bestand, und wie alt ist er?

    Rueckgabe: {status, treffer, alter_tage}. status ist einer von
      'belegt'        -- Beleg vorhanden und juenger als PRUEFALTER_TAGE
      'veraltet'      -- Beleg vorhanden, aber aelter (nachpruefen)
      'ausser_kraft'  -- Beleg vorhanden, belegt aber die NICHTGELTUNG: die
                         zitierte Norm ist laut juengstem Treffer gestrichen,
                         aufgehoben, ersetzt, oder ihr gilt_bis liegt vor dem
                         Stichtag. Ergaenzend im Rueckgabewert: 'grund'
                         ('gilt_bis_abgelaufen' | 'aufhebung_dokumentiert').
                         Zaehlt NICHT als Beleg fuer Geltung -- eigener Status,
                         damit ein Aufrufer, der nur auf 'belegt' prueft, ihn
                         nicht versehentlich als Erfolg liest.
      'unbelegt'      -- Bestand da, aber kein Beleg zu dieser Fundstelle
      'ungeprueft'    -- kein Bestand vorhanden, gar nicht geprueft
    'veraltet' ist der Fall, den ein blosses "steht im Bestand" verschweigt --
    und der eigentliche Grund fuer dieses Werkzeug: eingefrorenes Wissen wird
    nicht dadurch richtig, dass es einmal aufgeschrieben wurde.

    'unbelegt' und 'ungeprueft' sind ABSICHTLICH verschiedene Befunde. Ohne
    diese Trennung behauptete eine fehlende Datenbank stillschweigend "kein
    Beleg" fuer JEDES Zitat -- ein Aussagegehalt, den der Pruefer gar nicht
    hat, denn er hat nicht nachgesehen. Genau das geschah nach der Umbenennung
    knowledge.db -> brainlehr.db: der alte, selbst gebaute Pfad existierte
    nicht mehr, und jedes Zitat wurde als 'unbelegt' gemeldet, ohne dass die
    DB je geoeffnet wurde (Befund 3bd128cc)."""
    jetzt = jetzt or datetime.now(timezone.utc)
    pfad = pfad or _db_pfad()
    if not pfad.exists():
        return {"status": "ungeprueft", "treffer": [], "alter_tage": None}

    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Lehren-Kennungen leben in einer eigenen Tabelle. Und fuer Hausnormen
        # gilt KEIN Veralten: eine ADR wird nicht dadurch falsch, dass sie ein
        # Jahr alt ist -- sie wird durch eine spaetere ADR abgeloest, und das
        # steht dann dort. Hier zaehlt nur: existiert die Kennung ueberhaupt.
        # Ein 'unbelegt' heisst bei einer Hausnorm darum nicht "unbelegt",
        # sondern "erfunden" -- der schaerfere Befund.
        if f.kennung.startswith("L-"):
            try:
                r = conn.execute(
                    "SELECT id FROM lessons_learned WHERE id = ?",
                    (f.kennung,)).fetchone()
            except sqlite3.OperationalError:
                r = None
            if r:
                return {"status": "belegt", "alter_tage": 0,
                        "treffer": [{"id": r["id"], "path": "lessons_learned"}]}
            return {"status": "unbelegt", "treffer": [], "alter_tage": None}
        bedingungen, werte = [], []
        if f.art in ("gesetz", "eu"):
            # Gesetz und Paragraf GETRENNT suchen, nicht als zusammenhaengende
            # Zeichenkette: ein Beleg schreibt "§ 87 Abs. 1 BetrVG", und darin
            # kommt "§ 87 BetrVG" nicht vor. Vom Werkzeug an echten Daten
            # selbst gefunden -- der erste Lauf meldete den Knoten, der den
            # Wortlaut TRAEGT, als unbelegt.
            reihe, nummer = f.kennung.split(" ", 1)
            zahl = nummer.lstrip("§").replace("Art.", "")
            for feld in ("title", "summary", "COALESCE(content,'')", "source"):
                bedingungen.append(f"({feld} LIKE ? AND ({feld} LIKE ? OR {feld} LIKE ?))")
                werte += [f"%{reihe}%", f"%§ {zahl}%", f"%§{zahl}%"] if f.art == "gesetz" \
                    else [f"%{reihe}%", f"%Art. {zahl}%", f"%Art.{zahl}%"]
        else:
            for b in _suchbegriffe(f):
                bedingungen.append(
                    "(title LIKE ? OR summary LIKE ? OR COALESCE(content,'') LIKE ?"
                    " OR source LIKE ?)")
                werte += [f"%{b}%"] * 4
        rows = conn.execute(
            "SELECT id, path, title, summary, COALESCE(content,'') AS content, "
            "source, updated_at, gilt_bis FROM knowledge_nodes "
            f"WHERE zurueckgezogen = 0 AND ({' OR '.join(bedingungen)}) "
            "ORDER BY updated_at DESC LIMIT 5", werte).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"status": "unbelegt", "treffer": [], "alter_tage": None}

    if f.art != "hausnorm":
        # STRUKTURELL zuerst (verlaesslich, siehe Kommentar oben), dann
        # TEXTLICH -- am juengsten Treffer, nicht an irgendeinem: die neueste
        # Fassung im Bestand entscheidet, aeltere widersprechende Knoten sind
        # der Grund, warum es ueberhaupt Versionsstaende gibt.
        stichtag_tag = jetzt.strftime("%Y-%m-%d")
        if rows[0]["gilt_bis"] is not None and rows[0]["gilt_bis"] < stichtag_tag:
            return {"status": "ausser_kraft", "grund": "gilt_bis_abgelaufen",
                    "treffer": [{"id": rows[0]["id"], "path": rows[0]["path"]}],
                    "alter_tage": None}
        for r in rows:
            if _aufhebung_im_treffer(r):
                return {"status": "ausser_kraft", "grund": "aufhebung_dokumentiert",
                        "treffer": [{"id": r["id"], "path": r["path"]}],
                        "alter_tage": None}

    juengster = rows[0]["updated_at"]
    alter = None
    try:
        d = datetime.fromisoformat(juengster)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        alter = (jetzt - d).days
    except (TypeError, ValueError):
        # Unlesbares Datum gilt als alt, nicht als frisch -- ein kaputter
        # Zeitstempel darf keinen Beleg jung machen.
        alter = PRUEFALTER_TAGE + 1
    if f.art == "hausnorm":
        # siehe oben: Hausnormen veralten nicht nach Kalender, sie werden
        # abgeloest. Existenz genuegt.
        status = "belegt"
    else:
        status = "belegt" if alter is not None and alter <= PRUEFALTER_TAGE else "veraltet"
    return {"status": status,
            "treffer": [{"id": r["id"], "path": r["path"]} for r in rows],
            "alter_tage": alter}


def pruefe(text: str, pfad: Path | None = None,
           jetzt: datetime | None = None) -> list[dict]:
    """Alle Fundstellen im Text mit ihrem Belegstatus."""
    ergebnis = []
    for f in erkenne(text):
        b = belegt(f, pfad=pfad, jetzt=jetzt)
        ergebnis.append({"kennung": f.kennung, "roh": f.roh, "art": f.art, **b})
    return ergebnis


def melde(ergebnis: list[dict]) -> str:
    """Text fuer den Stop-Hook. Leer, wenn alles belegt und frisch ist --
    ein Melder, der auch bei Ordnung spricht, wird abgeschaltet."""
    offen = [e for e in ergebnis if e["status"] != "belegt"]
    if not offen:
        return ""
    zeilen = ["NORMBEZUG OHNE BELEG — Modellwissen ist eingefroren und kann "
              "ueberholt sein:"]
    for e in offen:
        if e["status"] == "ungeprueft":
            zeilen.append(f"  {e['roh']}  ->  kein Bestand gefunden, NICHT "
                          f"geprueft (nicht mit 'unbelegt' verwechseln).")
        elif e["status"] == "ausser_kraft":
            grund = ("gilt_bis liegt vor dem Stichtag" if e.get("grund") ==
                      "gilt_bis_abgelaufen" else
                      "Beleg dokumentiert Streichung/Aufhebung/Ersetzung")
            zeilen.append(f"  {e['roh']}  ->  Beleg zeigt: diese Fassung gilt "
                          f"NICHT (mehr) — {grund} ({e['treffer'][0]['path']}). "
                          f"Nicht als Beleg fuer Geltung verwenden.")
        elif e["art"] == "hausnorm":
            zeilen.append(f"  {e['roh']}  ->  Kennung existiert im Bestand "
                          f"NICHT. Aus dem Sitzungsgedaechtnis zitiert oder "
                          f"erfunden — nachsehen, bevor sie weitergetragen wird.")
        elif e["status"] == "unbelegt":
            zeilen.append(f"  {e['roh']}  ->  kein Beleg im Bestand. "
                          f"Wortlaut nachschlagen und als Knoten anlegen.")
        else:
            zeilen.append(f"  {e['roh']}  ->  Beleg ist {e['alter_tage']} Tage "
                          f"alt ({e['treffer'][0]['path']}). Fassung pruefen.")
    return "\n".join(zeilen)


# --- Selbsttest ------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    # --- Erkennung: die vier Bauformen, die heute wirklich vorkamen --------
    t = ("Nach § 87 Abs. 1 Nr. 6 BetrVG ist das mitbestimmungspflichtig, und "
         "Art. 6 Abs. 1 lit. f DSGVO traegt die Verarbeitung. Geprueft gegen "
         "DIN EN ISO 9241-110 und BSI TR-02102-1, dazu RFC 7914 und WCAG 2.2.")
    k = [f.kennung for f in erkenne(t)]
    for erwartet in ("BetrVG §87", "DSGVO Art.6", "DIN EN ISO 9241-110",
                     "BSI TR-02102-1", "RFC 7914", "WCAG 2.2"):
        assert erwartet in k, f"nicht erkannt: {erwartet} (gefunden: {k})"

    # --- Absatz aendert die Kennung nicht (sonst meldet ein Beleg 20x) -----
    a = erkenne("§ 87 Abs. 1 Nr. 6 BetrVG")[0].kennung
    b = erkenne("§ 87 Abs. 2 BetrVG")[0].kennung
    assert a == b == "BetrVG §87", (a, b)

    # --- Dubletten: dieselbe Norm zweimal genannt -> ein Treffer -----------
    assert len(erkenne("§ 87 BetrVG und nochmal § 87 Abs. 3 BetrVG")) == 1

    # --- NEGATIVFALL: vage Erwaehnungen sind kein Zitat --------------------
    for harmlos in ("laut Gesetz ist das erlaubt",
                    "eine EU-Verordnung regelt das",
                    "das ist gesetzlich vorgeschrieben",
                    "wir haben 87 Tests und 6 Fehler",
                    "Version 2.2 der Oberflaeche"):
        assert erkenne(harmlos) == [], f"Fehlalarm: {harmlos!r}"

    # --- Hausnormen: Kennungen aus dem Sitzungsgedaechtnis -----------------
    hk = [f.kennung for f in erkenne(
        "Laut ADR-001 und ADR-F-026, dazu OD13 und L-adfb33.")]
    for erwartet in ("ADR-001", "ADR-F-026", "OD13", "L-adfb33"):
        assert erwartet in hk, f"Hausnorm nicht erkannt: {erwartet} ({hk})"
    assert erkenne("ADR-001")[0].art == "hausnorm"
    # Negativfall: aehnlich aussehende Zeichenketten sind keine Kennung
    for harmlos in ("ADRESSE", "L-x", "OD", "ADR ohne Nummer"):
        assert not [f for f in erkenne(harmlos) if f.art == "hausnorm"], harmlos

    # --- Bestandsabgleich gegen eine gebaute Mini-DB -----------------------
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "k.db"
        conn = sqlite3.connect(str(pfad))
        conn.execute("""CREATE TABLE knowledge_nodes (
            id TEXT, path TEXT, title TEXT, summary TEXT, content TEXT,
            source TEXT, updated_at TEXT, zurueckgezogen INTEGER DEFAULT 0,
            gilt_bis TEXT)""")
        jetzt = datetime(2026, 8, 10, tzinfo=timezone.utc)
        conn.execute(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,0,NULL)",
            ("n1", "/recht/betrvg", "Mitbestimmung", "…", "Wortlaut § 87 BetrVG",
             "gesetze-im-internet.de", (jetzt - timedelta(days=10)).isoformat()))
        conn.execute(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,0,NULL)",
            ("n2", "/recht/alt", "Alte Norm", "…", "ISO 27001 Anforderungen",
             "irgendwo", (jetzt - timedelta(days=400)).isoformat()))
        conn.commit(); conn.close()

        r = {e["kennung"]: e for e in pruefe(
            "§ 87 Abs. 1 Nr. 6 BetrVG, ISO 27001 und Art. 15 DSGVO",
            pfad=pfad, jetzt=jetzt)}
        assert r["BetrVG §87"]["status"] == "belegt", r["BetrVG §87"]
        assert r["ISO 27001"]["status"] == "veraltet", r["ISO 27001"]
        assert r["ISO 27001"]["alter_tage"] == 400
        assert r["DSGVO Art.15"]["status"] == "unbelegt"

        # Grenzwerte am Pruefalter: davor, genau darauf, danach
        conn = sqlite3.connect(str(pfad))
        for tage, erwartet in ((PRUEFALTER_TAGE - 1, "belegt"),
                               (PRUEFALTER_TAGE, "belegt"),
                               (PRUEFALTER_TAGE + 1, "veraltet")):
            conn.execute("UPDATE knowledge_nodes SET updated_at=? WHERE id='n1'",
                         ((jetzt - timedelta(days=tage)).isoformat(),))
            conn.commit()
            got = pruefe("§ 87 BetrVG", pfad=pfad, jetzt=jetzt)[0]["status"]
            assert got == erwartet, f"{tage} Tage -> {got}, erwartet {erwartet}"
        # kaputter Zeitstempel gilt als alt, nie als frisch
        conn.execute("UPDATE knowledge_nodes SET updated_at='neulich' WHERE id='n1'")
        conn.commit(); conn.close()
        assert pruefe("§ 87 BetrVG", pfad=pfad, jetzt=jetzt)[0]["status"] == "veraltet"

        # --- Meldung schweigt bei Ordnung ---------------------------------
        assert melde([{"kennung": "x", "roh": "x", "art": "gesetz",
                       "status": "belegt", "treffer": [], "alter_tage": 1}]) == ""
        text = melde(pruefe("Art. 15 DSGVO", pfad=pfad, jetzt=jetzt))
        assert "kein Beleg" in text and "Art. 15 DSGVO" in text

        # --- Hausnorm gegen den Bestand: existiert die Kennung? -----------
        conn = sqlite3.connect(str(pfad))
        conn.execute("""CREATE TABLE lessons_learned (id TEXT)""")
        conn.execute("INSERT INTO lessons_learned VALUES ('L-abc123')")
        conn.execute(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,0,NULL)",
            ("n3", "/adr/001", "ADR-001 Transport", "…", "…", "adr",
             (jetzt - timedelta(days=800)).isoformat()))
        conn.commit(); conn.close()

        # --- ERWAEHNUNG vs. GELTUNG: der eigentliche Auftrag ---------------
        # Rot vor Gruen: gegen den Code VOR diesem Auftrag waere "GEG §71"
        # 'belegt' gewesen (LIKE traf n_geg, keine Geltungspruefung existierte).
        conn = sqlite3.connect(str(pfad))
        conn.execute(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,0,NULL)",
            ("n_geg", "/shared/geg-71-gestrichen",
             "GEG heisst seit 29.07.2026 GModG — §§ 71 bis 73 gestrichen",
             "Artikel 1 Nr. 32 streicht die §§ 71 bis 73 ersatzlos.",
             "Die 65-Prozent-Pflicht nach § 71 GEG entfaellt.",
             "BGBl. I 2026 Nr. 226", jetzt.isoformat()))
        # Grenzfall: eine Norm, die zum Stichtag der Aussage galt (gilt_ab
        # liegt davor) und HEUTE (jetzt) nicht mehr -- strukturell, ohne dass
        # ein Wort wie "gestrichen" ueberhaupt vorkommt.
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary,content,"
            "source,updated_at,zurueckgezogen,gilt_bis) VALUES (?,?,?,?,?,?,?,0,?)",
            ("n_abgelaufen", "/simulation/erlass-2026",
             "Erlass 2026", "Sommergebuehrenerlass", "§ 12 WEG regelt das befristet.",
             "verordnung", jetzt.isoformat(), (jetzt - timedelta(days=1)).date().isoformat()))
        conn.commit(); conn.close()

        r_geg = pruefe("§ 71 GEG", pfad=pfad, jetzt=jetzt)[0]
        assert r_geg["status"] == "ausser_kraft", r_geg
        assert r_geg["grund"] == "aufhebung_dokumentiert", r_geg
        meldung_geg = melde([r_geg])
        assert "gilt NICHT (mehr)" in meldung_geg and "§ 71 GEG" in meldung_geg

        r_abgelaufen = pruefe("§ 12 WEG", pfad=pfad, jetzt=jetzt)[0]
        assert r_abgelaufen["status"] == "ausser_kraft", r_abgelaufen
        assert r_abgelaufen["grund"] == "gilt_bis_abgelaufen", r_abgelaufen

        # Positivfall: eine geltende Norm bleibt 'belegt' -- ohne ihn waere
        # ein Melder gruen, der alles pauschal als ausser_kraft ablehnt. Bewusst
        # dieselbe Reihe (GEG) wie der Streichungsfall, andere Nummer: beweist,
        # dass die Kennung trennt und nicht die blosse Erwaehnung von "GEG".
        conn = sqlite3.connect(str(pfad))
        conn.execute(
            "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?,0,NULL)",
            ("n_geg_gueltig", "/shared/geg-20-heizungslabel",
             "§ 20 GEG regelt Heizungslabel weiter",
             "§ 20 GEG bleibt von der Novelle unberuehrt und in Kraft.",
             "unveraendert anwendbar", "BGBl. I 2026 Nr. 226", jetzt.isoformat()))
        conn.commit(); conn.close()
        assert pruefe("§ 20 GEG", pfad=pfad, jetzt=jetzt)[0]["status"] == "belegt", \
            pruefe("§ 20 GEG", pfad=pfad, jetzt=jetzt)

        h = {e["kennung"]: e for e in pruefe(
            "Laut ADR-001, ADR-999 und L-abc123 sowie L-ffffff.",
            pfad=pfad, jetzt=jetzt)}
        # 800 Tage alt und trotzdem 'belegt': eine ADR veraltet nicht nach
        # Kalender, sie wird abgeloest.
        assert h["ADR-001"]["status"] == "belegt", h["ADR-001"]
        assert h["ADR-999"]["status"] == "unbelegt", "erfundene ADR nicht erkannt"
        assert h["L-abc123"]["status"] == "belegt"
        assert h["L-ffffff"]["status"] == "unbelegt", "erfundene Lehre nicht erkannt"
        meldung = melde(list(h.values()))
        assert "existiert im Bestand" in meldung and "ADR-999" in meldung

        # --- fehlende DB ist kein Absturz UND kein 'unbelegt' --------------
        # 'unbelegt' hiesse "nachgesehen, nichts gefunden" -- das waere hier
        # falsch, denn nachgesehen wurde gar nicht. Der eigene Befund dieses
        # Auftrags (3bd128cc): nach der Umbenennung knowledge.db->brainlehr.db
        # meldete genau diese Verwechslung JEDES Zitat als grundlos unbelegt.
        r_fehlend = pruefe("§ 87 BetrVG", pfad=Path(tmp) / "gibtsnicht.db")[0]
        assert r_fehlend["status"] == "ungeprueft", r_fehlend
        m_fehlend = melde([r_fehlend])
        assert "kein Bestand gefunden" in m_fehlend and "NICHT" in m_fehlend, m_fehlend

    print("normbezug.py: Selbsttest gruen")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--text")
    p.add_argument("--stop", action="store_true",
                   help="Stop-Hook: liest die letzte Antwort aus stdin (JSON)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return 0

    text = args.text
    if args.stop and not text:
        try:
            text = json.load(sys.stdin).get("text", "")
        except (json.JSONDecodeError, ValueError):
            return 0
    if not text:
        p.error("--text oder --stop mit JSON auf stdin")

    ergebnis = pruefe(text)
    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 0
    meldung = melde(ergebnis)
    if meldung:
        print(meldung)
        return 1
    print(f"normbezug: {len(ergebnis)} Fundstelle(n), alle belegt und frisch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
