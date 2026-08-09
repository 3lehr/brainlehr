#!/usr/bin/env python3
"""antwort_abruf.py -- Wissensabruf aus der eigenen ANTWORT, nicht nur aus
der Frage des Betreibers (Betreiber-Auftrag 2026-08-09).

DIE LUECKE: Der bestehende Abruf haengt allein am UserPromptSubmit-Text des
Betreibers. Gemessen: 28 von 94 Nachrichten erreichen diesen Haltepunkt nie
(Klient liefert sie als Attachment waehrend laufender Arbeit), weitere 22
reissen die Mindesttrefferzahl nicht. Auf der Eingabeseite gibt es fuer
beide Klassen nichts zu durchsuchen -- die ANTWORT des Assistenten liegt
dagegen immer vor und traegt das volle Fachvokabular. Gemessen an sechs
echten Antworten: die 30 Begriffe mit hoechstem IDF-Gewicht (1719 Zeichen)
fanden 17 Eintraege, die der Prompt-Weg nie lieferte.

ZWEI BETRIEBSARTEN:
  --stop   (Stop-Haltepunkt): letzte Assistant-Antwort aus dem Transcript
           ziehen, ab 400 Zeichen auf die 30 IDF-staerksten Begriffe
           verdichten, damit knowledge_search() fragen, Treffer nach
           antwort_treffer.json ablegen. Die vorherige Ablage (falls
           dieselbe Sitzung) wird dabei nicht verworfen, sondern als
           Vergleichsstand mitgefuehrt (siehe BESTAETIGUNG unten).
  --prompt (UserPromptSubmit-Haltepunkt): von den abgelegten Treffern nur
           die AUSGABEFAEHIGEN nehmen (siehe BESTAETIGUNG), davon was laut
           recall_log.jsonl in DIESER Sitzung schon ausgeliefert wurde
           herausfiltern, Rest (Deckel 3 Eintraege / 1200 Zeichen) auf
           stdout ausgeben und die Ablage als verbraucht markieren.

BESTAETIGUNG UEBER ZWEI ZUEGE (Nachtrag 2026-08-09, Lehre L-f0d97d):
knowledge_search liefert KEINE vergleichbaren Scores (RRF-Rangfusion, siehe
Docstring dort) -- ein Score-Schwellwert ist also nicht baubar, gebraucht
wird ein SKALENFREIES Kriterium. Zwei unabhaengig erzeugte Antworten, die
auf denselben Eintrag zeigen, SIND ein Relevanzsignal, das keine Zahl
braucht: ein Treffer gilt erst als ausgabefaehig, wenn er in ZWEI
aufeinanderfolgenden Ablagen (vorige + aktuelle) steckt. Preis: ein nur
einmalig auftauchendes Thema wird nie ausgespielt, und jeder Treffer kommt
grundsaetzlich einen Zug spaeter an.
Ausnahme (schlaegt die Bestaetigung): ein Treffer, der an einem Begriff
haengt, der in der VORIGEN Antwort nicht vorkam (Differenzmenge aktuelle
minus vorige Begriffe), gilt SOFORT als ausgabefaehig -- ein Themenwechsel
darf nicht erst nach zwei Zuegen ankommen, sonst kommt das Wissen genau
dann zu spaet, wenn es am meisten hilft. Beim ERSTEN Zug einer Sitzung gibt
es keine vorige Antwort; die Differenzmenge ist dann ABSICHTLICH leer statt
"alles ist neu" -- sonst waere die Ausnahme beim ersten Zug immer wahr und
haette die Bestaetigungspflicht komplett ausgehebelt, noch bevor sie greifen
konnte.

DRITTES KRITERIUM -- VERBINDENDE TREFFER (Nachtrag 2026-08-09, zweiter
Nachtrag): Messung ueber acht echte Antworten (max_results=15): die Spitze
(Rang 1-3) zeigte ueber 24 Plaetze 24 VERSCHIEDENE Eintraege -- Kriterium 1
kam im Fenster nie zum Zug, weil die acht Antworten acht verschiedene Themen
waren (kein Beleg GEGEN Kriterium 1, nur ein Fenster ohne den Fall, in dem es
greift -- L-b4b6fc). Im Schwanz (Rang 4-15) dagegen: EIN Eintrag kam
dreimal vor, nie in der Spitze -- er passte zu keinem der acht Themen genau,
zu dreien halb. Ein solcher Treffer liegt QUER ueber den Themen und wird
darum eigens erfasst statt am Bestaetigungs-/Neu-Kriterium zu scheitern
(die vergleichen nur zwei aufeinanderfolgende Zuege, ein quer liegender
Treffer wiederholt sich ueber viele Zuege in wechselnder Umgebung).
Schwelle SCHWANZ_SCHWELLE=3 ist GERATEN -- die einzige Zahl, die dahinter
steht, ist der EINE Fund bei acht Anfragen in der Messung oben. Ein Treffer,
der die Schwelle erreicht und NIE in der Spitze stand, wird als
"verbindender Treffer" (eigene Kennzeichnung im Ausgabetext, siehe
_kriterium_3) statt als Thementreffer ausgegeben -- sonst haelt ihn, wer die
Kennzeichnung nicht kennt, fuer einen schlechten Treffer, der zufaellig oft
auftaucht. Die Schwanz-Zaehlung UND die Feuerzaehler je Kriterium (1/2/3)
laufen bei jedem --stop bzw. --prompt mit, auch wenn nichts ausgegeben wird
-- sonst laesst sich die geratene Drei nie an echten Daten korrigieren.

VERWENDUNG STATT NUR LIEFERUNG (Nachtrag 2026-08-09, Lehre L-ff8fff): der
Feuerzaehler oben misst nur, dass ein Treffer AUSGESPIELT wurde -- nicht, ob
er in der naechsten Antwort auch VORKAM. Gemessener Anlass: ein eingespielter
Treffer loeste den offenen Denkfehler der laufenden Antwort, wurde aber nur
als Beleg fuer "der Mechanismus feuert" erwaehnt, nicht inhaltlich benutzt --
erst die Nachfrage des Betreibers oeffnete ihn. Darum merkt --prompt sich in
"ausgespielt_offen", welche Eintraege es ausgeliefert hat (Kennung +
kennzeichnende Begriffe aus der Ausgabezeile), und der naechste --stop prueft
die NEUE Antwort darauf: WOERTLICH wenn die Kennung selbst vorkommt (harter
Nachweis), BEGRIFFLICH wenn mindestens BEGRIFFLICH_MIN der kennzeichnenden
Begriffe vorkommen, sonst NICHT_VERWENDET. Geprueft wird genau EINMAL (beim
naechsten Zug), danach verlaesst der Eintrag "ausgespielt_offen" -- der
Auftrag verlangt keine Mehrfachpruefung ueber viele Zuege. Auch WOERTLICH
beweist nur, dass der Eintrag VORKAM, nicht dass er die Antwort besser
gemacht hat -- dieselbe Verwechslung wie zwischen Lieferung und Wirkung, nur
eine Ebene hoeher, siehe Kommentar an der Zaehlung selbst.

Beide Pfade fangen jede Ausnahme ab und enden still -- ein Haken darf die
Sitzung nie stoeren (gleiche Regel wie in knowledge_recall_hook.py und
existenzpruefung.py, hier eigenstaendig nachgebaut statt importiert, siehe
Grenzen unten).

Wiederverwendet (Ponytail-Leiter, Stufe 2): knowledge_mcp_server.knowledge_search
fuer die Suche, pruefkorpus.load_bestand/build_idf/tokenize fuer die
IDF-Gewichtung -- beide bereits im Repo, kein Neubau. NICHT verwendet:
pruefkorpus.rare_terms() -- filtert auf im Bestand seltene Begriffe und
lieferte in der Auftragsmessung 0 Treffer.

GRENZEN: keine andere Datei angefasst. haken/ort.py absichtlich NICHT
importiert (Auftrag erlaubt nur Standardbibliothek + die zwei genannten
Repo-Module) -- der Wurzelpfad wird hier eigenstaendig aus __file__
abgeleitet, exakt wie in ort.py (WURZEL = ... .parent.parent).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

import knowledge_mcp_server as kms  # noqa: E402
import pruefkorpus  # noqa: E402

RECALL_LOG = WURZEL / "recall_log.jsonl"
TREFFER_DATEI = WURZEL / "antwort_treffer.json"

MIN_LEN = 400          # kuerzere Antworten sind selten inhaltsreich genug
MAX_BEGRIFFE = 30       # Auftragsvorgabe
MIN_BEGRIFF_LAENGE = 4  # ">3 Zeichen" -- pruefkorpus.tokenize() filtert das schon mit
MAX_RESULTS_STOP = 15   # war 5, jetzt Spitze(3) + Schwanz(12) fuer Kriterium 3
SPITZE_GROESSE = 3      # Rang 1-3, speist Kriterium 1+2 (Auftrag Nachtrag 4)
# GERATEN: die einzige Grundlage ist EIN Fund (L-6a44e5) bei acht Anfragen in
# der Auftragsmessung -- keine statistisch tragfaehige Zahl, nur der erste
# Anschlusspunkt zum Nachjustieren, sobald die Feuerzaehler mehr Daten haben.
SCHWANZ_SCHWELLE = 3
CAP_EINTRAEGE = 3       # Deckel Auftrag
CAP_ZEICHEN = 1200      # Deckel Auftrag

# Wieviele kennzeichnende Begriffe (aus Titel+Zusammenfassung eines
# ausgespielten Eintrags) muessen in der naechsten Antwort vorkommen, damit
# er als "begrifflich verwendet" zaehlt, wenn die Kennung selbst NICHT
# vorkommt. GEWAEHLT: 2 -- bei 1 reicht ein einzelnes, haeufiges Wort
# (z.B. "Deckel", "Sitzung") zum Falsch-Positiv, weil es zufaellig auch im
# naechsten, thematisch anderen Absatz auftaucht. Preis eines Fehlalarms:
# die Verwendungs-Statistik meldet Wirkung, die es nicht gab, und genau DAS
# soll dieser Auftrag verhindern (siehe BEFUND). 2 verlangt zwei voneinander
# unabhaengige Zufallstreffer, was bei Woertern >=4 Zeichen (tokenize())
# deutlich unwahrscheinlicher ist. Keine hoehere Zahl gewaehlt, weil kurze
# Zusammenfassungen sonst nie genug Begriffe liefern, um ueberhaupt zu
# feuern -- 2 ist der kleinste Wert, der einen Einzelwort-Zufallstreffer
# ausschliesst.
BEGRIFFLICH_MIN = 2

# Zweite Sicherung gegen die Rueckkopplung (Nachtrag 2026-08-09): ohne diesen
# Deckel wuerde jede Antwort, die ein zuvor eingespieltes Thema wieder
# aufgreift, denselben Treffer erneut in den Bestand ziehen -- Punkt 1
# (Protokollierung in recall_log.jsonl) verhindert die Wiederholung DESSELBEN
# Treffers, aber nicht die Verengung auf ein enges Themenfeld ueber viele
# VERSCHIEDENE Treffer hinweg. Deckel ist je Sitzung, nicht je Aufruf. Preis:
# spaete Treffer in einer langen Sitzung, die inhaltlich besser waeren als
# fruehe, fallen nach Erreichen der Grenze weg -- bewusst in Kauf genommen,
# weil eine falsch verengte Sitzung teurer ist als ein einzelner ausbleibender
# Treffer.
MAX_ANTWORT_EINTRAEGE_JE_SITZUNG = 10

KOPF = "<antwort-recall>"
FUSS = "</antwort-recall>"
HINWEIS = ("Wissen zu Begriffen aus der eigenen letzten Antwort "
           "(automatisch abgeleitet, ungeprüft):")


# --- Transcript lesen ------------------------------------------------------

def letzte_antwort(transcript_path: str) -> str:
    """Text der letzten Assistant-Nachricht im Sitzungsprotokoll. Robust
    gegen kaputte/Teilzeilen -- eine einzelne unlesbare Zeile darf den Rest
    nicht kippen."""
    letzte = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for zeile in f:
                try:
                    d = json.loads(zeile)
                except Exception:
                    continue
                if d.get("type") != "assistant":
                    continue
                inhalt = (d.get("message") or {}).get("content") or []
                stuecke = [t.get("text", "") for t in inhalt
                           if isinstance(t, dict) and t.get("type") == "text"]
                if stuecke:
                    letzte = "\n".join(stuecke)
    except OSError:
        return ""
    return letzte


def top_begriffe(text: str, n: int = MAX_BEGRIFFE) -> list[str]:
    """Die n Begriffe aus text mit dem hoechsten IDF-Gewicht ueber den
    ganzen Bestand (Nodes + aktive Lehren). tokenize() liefert bereits nur
    Woerter ab 4 Zeichen, gefaltet, ohne Stopwoerter -- kein zweiter Filter
    noetig."""
    nodes, lessons = pruefkorpus.load_bestand()
    idf, _n_docs, _df = pruefkorpus.build_idf(nodes, lessons)
    begriffe = pruefkorpus.tokenize(text)
    geordnet = sorted(begriffe, key=lambda w: idf.get(w, 0.0), reverse=True)
    return geordnet[:n]


# --- Schwanz-Statistik (Kriterium 3) ----------------------------------------

def _leere_statistik() -> dict:
    return {
        "schwanz": {}, "spitze_gesehen": [], "kriterium_feuer": {"1": 0, "2": 0, "3": 0},
        # Verwendungs-Statistik (Auftrag L-ff8fff): "geliefert" zaehlt jede
        # Ausspielung sofort (in modus_prompt), die drei anderen erst wenn
        # der naechste --stop tatsaechlich geprueft hat -- darum koennen sie
        # in Summe unter "geliefert" liegen, wenn eine Sitzung vor der
        # Pruefung endet. Das ist gewollt, kein Zaehlfehler.
        "verwendung": {"geliefert": 0, "woertlich": 0, "begrifflich": 0, "nicht_verwendet": 0},
        "ausgespielt_offen": [],
    }


def _schwanz_zaehlen(statistik: dict, spitze: list[dict], schwanz: list[dict]) -> None:
    """Laeuft bei JEDEM --stop mit, unabhaengig davon, ob je etwas ausgegeben
    wird (Auftrag Punkt 5) -- sonst laesst sich SCHWANZ_SCHWELLE nie an echten
    Daten korrigieren. 'nie in der Spitze' ist eine LEBENSZEIT-Aussage ueber
    die ganze Sitzung, darum ein eigenes 'spitze_gesehen'-Register statt nur
    ein Flag am Schwanz-Eintrag -- ein Treffer kann in Zug 1 Spitze und in
    Zug 5 Schwanz sein, die Reihenfolge darf das Ergebnis nicht aendern."""
    spitze_keys = {f"{k}|{s}" for k, s, _ in (_schluessel_und_zeile(e) for e in spitze)}
    gesehen = set(statistik.get("spitze_gesehen") or []) | spitze_keys
    statistik["spitze_gesehen"] = sorted(gesehen)

    schwanz_dict = statistik.setdefault("schwanz", {})
    for e in schwanz:
        kind, schluessel, _ = _schluessel_und_zeile(e)
        key = f"{kind}|{schluessel}"
        eintrag = schwanz_dict.setdefault(
            key, {"kind": kind, "schluessel": schluessel, "anzahl": 0, "titel": "", "zusammenfassung": ""})
        eintrag["anzahl"] = eintrag.get("anzahl", 0) + 1
        eintrag["titel"] = e.get("title") or e.get("type") or ""
        eintrag["zusammenfassung"] = e.get("summary") or ""


# --- Verwendungs-Statistik (Auftrag L-ff8fff) -------------------------------

def _verwendung_pruefen(statistik: dict, antwort: str) -> None:
    """Prueft die beim VORIGEN --prompt ausgespielten Eintraege gegen die
    NEUE Antwort (voller Text, nicht die 30 IDF-Begriffe). WOERTLICH wenn
    die Kennung selbst im Text steht, sonst BEGRIFFLICH wenn mindestens
    BEGRIFFLICH_MIN der kennzeichnenden Begriffe vorkommen, sonst
    NICHT_VERWENDET. Genau EINE Pruefung je Eintrag -- "ausgespielt_offen"
    wird danach geleert, der Auftrag verlangt keine Mehrfachpruefung ueber
    mehrere Zuege. Auch WOERTLICH beweist nur, dass der Eintrag VORKAM --
    nicht, dass er die Antwort besser gemacht hat (dieselbe Verwechslung wie
    Lieferung vs. Wirkung, nur eine Ebene hoeher)."""
    offen = statistik.get("ausgespielt_offen") or []
    if not offen:
        return
    verwendung = statistik.setdefault(
        "verwendung", {"geliefert": 0, "woertlich": 0, "begrifflich": 0, "nicht_verwendet": 0})
    antwort_begriffe = pruefkorpus.tokenize(antwort)
    for eintrag in offen:
        schluessel = eintrag.get("schluessel") or ""
        if schluessel and schluessel in antwort:
            verwendung["woertlich"] = verwendung.get("woertlich", 0) + 1
            continue
        begriffe = set(eintrag.get("begriffe") or [])
        if len(begriffe & antwort_begriffe) >= BEGRIFFLICH_MIN:
            verwendung["begrifflich"] = verwendung.get("begrifflich", 0) + 1
        else:
            verwendung["nicht_verwendet"] = verwendung.get("nicht_verwendet", 0) + 1
    statistik["ausgespielt_offen"] = []


# --- Betriebsart --stop -----------------------------------------------------

def modus_stop(payload: dict) -> None:
    pfad = payload.get("transcript_path")
    if not pfad:
        return
    antwort = letzte_antwort(pfad)
    if len(antwort) < MIN_LEN:
        return
    begriffe = top_begriffe(antwort)
    if not begriffe:
        return
    ergebnis = kms.knowledge_search(" ".join(begriffe), max_results=MAX_RESULTS_STOP)
    treffer = ergebnis.get("results") or []
    if not treffer:
        return
    session = payload.get("session_id")
    session8 = session[:8] if session else None
    spitze = treffer[:SPITZE_GROESSE]
    schwanz = treffer[SPITZE_GROESSE:]

    # Vergleichsstand fuer die Bestaetigung: die ALTE "aktuelle" Ablage
    # (nur die Spitze) wird zur neuen "vorherigen" -- nur wenn sie zur
    # selben Sitzung gehoert, sonst gibt es (wie beim allerersten Zug)
    # keinen Vergleich. Die Schwanz-Statistik ist SITZUNGSWEIT und wird
    # ebenso uebernommen, nicht neu angelegt.
    vorherige = None
    statistik = _leere_statistik()
    try:
        with open(TREFFER_DATEI, encoding="utf-8") as f:
            alt = json.load(f)
        if alt.get("session") == session8:
            vorherige = alt.get("aktuelle")
            statistik = alt.get("statistik") or statistik
    except (OSError, json.JSONDecodeError):
        pass

    _verwendung_pruefen(statistik, antwort)
    _schwanz_zaehlen(statistik, spitze, schwanz)

    daten = {
        "session": session8,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verbraucht": False,
        "vorherige": vorherige,
        "aktuelle": {"treffer": spitze, "begriffe": begriffe},
        "statistik": statistik,
    }
    with open(TREFFER_DATEI, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False)


# --- Betriebsart --prompt ---------------------------------------------------

def _bereits_geliefert(session: str) -> tuple[set, set, int]:
    """Pfade/Kennungen, die recall_log.jsonl fuer diese Sitzung schon
    ausgeliefert hat -- ueber ALLE Zeilen dieser Sitzung, nicht nur die
    letzte -- plus wieviele davon ueber DIESEN Weg kamen (ausloeser=="antwort",
    fuer die Sitzungsobergrenze). Zeilen des normalen Prompt-Wegs (kein
    "ausloeser"-Feld) zaehlen fuer den Dedup mit, aber NICHT auf die
    Obergrenze."""
    nodes, lessons = set(), set()
    antwort_eintraege = 0
    try:
        with open(RECALL_LOG, encoding="utf-8") as f:
            for zeile in f:
                try:
                    d = json.loads(zeile)
                except Exception:
                    continue
                if d.get("session") != session:
                    continue
                zeilen_nodes = d.get("nodes") or []
                zeilen_lessons = d.get("lessons") or []
                nodes.update(zeilen_nodes)
                lessons.update(zeilen_lessons)
                if d.get("ausloeser") == "antwort":
                    antwort_eintraege += len(zeilen_nodes) + len(zeilen_lessons)
    except OSError:
        pass
    return nodes, lessons, antwort_eintraege


def _schluessel_und_zeile(e: dict) -> tuple[str, str, str]:
    if e.get("kind") == "lesson":
        kind = "lesson"
        schluessel = e.get("id", "")
        titel = e.get("type") or "Lehre"
    else:
        kind = "node"
        schluessel = e.get("path", "")
        titel = e.get("title") or ""
    zeile = f"- [{schluessel}] {titel}: {e.get('summary') or ''}"
    return kind, schluessel, zeile


def _protokolliere(session: str, eintraege: list[tuple[str, str, str]]) -> None:
    """Schreibt, was tatsaechlich ausgegeben wurde (NACH Dedup und Deckel,
    keine Rohtreffer) als eigene Zeile nach recall_log.jsonl -- gleiches
    Format wie die bestehenden Zeilen, damit der vorhandene Dedup ab dem
    naechsten Zug greift, plus "ausloeser": "antwort" zur Kennzeichnung des
    Wegs. Beiwerk, darf die Ausgabe nie zum Scheitern bringen."""
    zeile = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nodes": [s for k, s, _ in eintraege if k == "node"],
        "lessons": [s for k, s, _ in eintraege if k == "lesson"],
        "session": session,
        "ausloeser": "antwort",
    }
    try:
        with open(RECALL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ausgabefaehig(aktuelle: dict, vorherige: dict | None) -> tuple[list[tuple[str, str, str]], dict]:
    """Kriterium 1+2, wendet die Bestaetigung-ueber-zwei-Zuege-Regel an
    (siehe Moduldoc) auf die SPITZE (aktuelle["treffer"] enthaelt seit
    Nachtrag 4 nur noch Rang 1-3). vorherige=None (erster Zug der Sitzung)
    -> keine Bestaetigungsbasis UND eine leere Differenzmenge, sonst wuerde
    jeder Begriff beim ersten Zug als 'neu' gelten und die
    Bestaetigungspflicht wirkungslos machen. Gibt zusaetzlich zurueck, wie
    oft jedes Kriterium gefeuert hat (Auftrag Punkt 5)."""
    vorherige_treffer = (vorherige or {}).get("treffer") or []
    vorherige_schluessel = {_schluessel_und_zeile(e)[:2] for e in vorherige_treffer}
    if vorherige is not None:
        neue_begriffe = set(aktuelle.get("begriffe") or []) - set(vorherige.get("begriffe") or [])
    else:
        neue_begriffe = set()

    ausgefiltert = []
    fired = {"1": 0, "2": 0}
    for e in aktuelle.get("treffer") or []:
        kind, schluessel, zeile = _schluessel_und_zeile(e)
        bestaetigt = (kind, schluessel) in vorherige_schluessel
        text = f"{e.get('title') or e.get('type') or ''} {e.get('summary') or ''} {schluessel}"
        hat_neuen_begriff = bool(pruefkorpus.tokenize(text) & neue_begriffe)
        if bestaetigt:
            fired["1"] += 1
        if hat_neuen_begriff:
            fired["2"] += 1
        if bestaetigt or hat_neuen_begriff:
            ausgefiltert.append((kind, schluessel, zeile))
    return ausgefiltert, fired


def _kriterium_3(statistik: dict, ausgeschlossen: set) -> tuple[list[tuple[str, str, str]], int]:
    """Verbindende Treffer: mindestens SCHWANZ_SCHWELLE mal im Schwanz
    aufgetaucht und NIE in der Spitze gestanden (siehe Moduldoc). Eigene
    Kennzeichnung im Ausgabetext -- sonst haelt sie, wer sie nicht kennt,
    fuer schwache Thementreffer, die zufaellig oft auftauchen. `ausgeschlossen`
    sind (kind, schluessel)-Paare, die schon ueber Kriterium 1/2 im Ergebnis
    stehen -- kein Doppeleintrag."""
    spitze_gesehen = set(statistik.get("spitze_gesehen") or [])
    kandidaten = []
    gefeuert = 0
    for key, eintrag in (statistik.get("schwanz") or {}).items():
        kind, schluessel = eintrag.get("kind"), eintrag.get("schluessel")
        if (kind, schluessel) in ausgeschlossen:
            continue
        if eintrag.get("anzahl", 0) >= SCHWANZ_SCHWELLE and key not in spitze_gesehen:
            zeile = (f"- [{schluessel}] (verbindender Treffer, kein Thementreffer) "
                     f"{eintrag.get('titel') or ''}: {eintrag.get('zusammenfassung') or ''}")
            kandidaten.append((kind, schluessel, zeile))
            gefeuert += 1
    return kandidaten, gefeuert


def modus_prompt(payload: dict) -> None:
    session = payload.get("session_id")
    if not session:
        return
    session = session[:8]
    try:
        with open(TREFFER_DATEI, encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if daten.get("verbraucht") or daten.get("session") != session:
        return

    # Kriterium 1+2 (Spitze) zuerst, Kriterium 3 (Schwanz) ergaenzt nur, was
    # dort noch nicht steht -- kein Doppeleintrag. Die Feuerzaehler laufen
    # IMMER mit (Auftrag Punkt 5), auch wenn am Ende nichts ausgegeben wird --
    # darum wird "statistik" unten in JEDEM Fall zurueckgeschrieben, nicht nur
    # bei erfolgreicher Ausgabe.
    statistik = daten.get("statistik") or _leere_statistik()
    kandidaten, fired = _ausgabefaehig(daten.get("aktuelle") or {}, daten.get("vorherige"))
    ausgeschlossen = {(k, s) for k, s, _ in kandidaten}
    kandidaten_3, fired3 = _kriterium_3(statistik, ausgeschlossen)
    kandidaten += kandidaten_3
    fired["3"] = fired3
    for k in ("1", "2", "3"):
        statistik.setdefault("kriterium_feuer", {})[k] = statistik["kriterium_feuer"].get(k, 0) + fired[k]
    daten["statistik"] = statistik

    if kandidaten:
        geliefert_nodes, geliefert_lessons, antwort_bisher = _bereits_geliefert(session)
        verfuegbar = MAX_ANTWORT_EINTRAEGE_JE_SITZUNG - antwort_bisher
        if verfuegbar <= 0:
            kandidaten = []
        else:
            kandidaten = [
                (kind, schluessel, zeile) for kind, schluessel, zeile in kandidaten
                if schluessel not in (geliefert_lessons if kind == "lesson" else geliefert_nodes)
            ]
            kandidaten = kandidaten[:min(CAP_EINTRAEGE, verfuegbar)]
            while kandidaten:
                block = "\n".join([KOPF, HINWEIS, *[z for _, _, z in kandidaten], FUSS])
                if len(block) <= CAP_ZEICHEN:
                    break
                kandidaten.pop()  # Ueberzaehliges wird verworfen, nicht gekuerzt

    if kandidaten:
        print(block)
        daten["verbraucht"] = True
        # Verwendungs-Statistik (Auftrag L-ff8fff): "geliefert" zaehlt sofort,
        # unabhaengig davon, ob der naechste --stop je dazu kommt zu pruefen.
        # kennzeichnende Begriffe werden aus der fertigen Ausgabezeile
        # gezogen (enthaelt Kennung, Titel und Zusammenfassung bereits) --
        # kein zweiter Zugriff auf den Rohtreffer noetig.
        verwendung = statistik.setdefault(
            "verwendung", {"geliefert": 0, "woertlich": 0, "begrifflich": 0, "nicht_verwendet": 0})
        ausgespielt_offen = statistik.setdefault("ausgespielt_offen", [])
        for kind, schluessel, zeile in kandidaten:
            verwendung["geliefert"] = verwendung.get("geliefert", 0) + 1
            ausgespielt_offen.append({
                "kind": kind, "schluessel": schluessel,
                "begriffe": sorted(pruefkorpus.tokenize(zeile)),
            })

    try:
        with open(TREFFER_DATEI, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False)
    except OSError:
        pass

    if kandidaten:
        _protokolliere(session, kandidaten)


# --- Einstieg ---------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    try:
        if args.stop:
            modus_stop(payload)
        elif args.prompt:
            modus_prompt(payload)
    except Exception:
        return


# --- Selbsttest (rot vor gruen, kein Modellaufruf/Netz) ---------------------

def _selftest() -> None:
    import tempfile

    global TREFFER_DATEI, RECALL_LOG
    orig_treffer, orig_log = TREFFER_DATEI, RECALL_LOG
    orig_search = kms.knowledge_search
    faelle = 0

    def fake_search(query, scope="all", max_results=10, **kw):
        # Genau SPITZE_GROESSE Treffer -- kein Schwanz, damit diese Faelle
        # (Kriterium 1+2, Dedup, Sitzungsobergrenze) nicht ungewollt mit
        # Kriterium 3 interferieren (eigener Testblock weiter unten).
        return {"results": [
            {"kind": "node", "path": f"/fake/{i}", "title": f"T{i}", "summary": f"S{i}"}
            for i in range(SPITZE_GROESSE)
        ]}

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            TREFFER_DATEI = tmp / "antwort_treffer.json"
            RECALL_LOG = tmp / "recall_log.jsonl"

            # (a) Antwort unter 400 Zeichen -> keine Ablage.
            faelle += 1
            transcript = tmp / "t_kurz.jsonl"
            transcript.write_text(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "kurz"}]},
            }) + "\n", encoding="utf-8")
            modus_stop({"transcript_path": str(transcript), "session_id": "sess0001x"})
            assert not TREFFER_DATEI.exists(), "(a) Ablage haette nicht entstehen duerfen"
            print(f"  Fall {faelle}: (a) Antwort < 400 Zeichen -> keine Ablage ok")

            # (e) Negativfall: fehlendes Transcript-Feld -> still, keine Ausnahme.
            faelle += 1
            modus_stop({"session_id": "sess0001x"})  # kein transcript_path
            assert not TREFFER_DATEI.exists()
            print(f"  Fall {faelle}: (e) fehlendes transcript_path -> still, keine Ausnahme ok")

            # (f) Antwort >= 400 Zeichen -> Ablage mit 5 Treffern (Attrappe statt Modell/Netz).
            # Erster Zug der Sitzung -> "vorherige" ist None (noch kein Vergleichsstand).
            faelle += 1
            kms.knowledge_search = fake_search
            lang = "wort " * 200  # weit ueber 400 Zeichen, genug fuer 30 Begriffe
            transcript2 = tmp / "t_lang.jsonl"
            transcript2.write_text(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": lang}]},
            }) + "\n", encoding="utf-8")
            modus_stop({"transcript_path": str(transcript2), "session_id": "sess0001x"})
            assert TREFFER_DATEI.exists(), "(f) Ablage haette entstehen sollen"
            abgelegt = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))
            assert abgelegt["session"] == "sess0001"
            assert abgelegt["vorherige"] is None
            assert len(abgelegt["aktuelle"]["treffer"]) == SPITZE_GROESSE  # nur noch Rang 1-3 (fake/0,1,2)
            print(f"  Fall {faelle}: (f) lange Antwort -> Ablage mit Attrappen-Treffern, erster Zug ok")

            # Zweiter Zug, dieselben Treffer -> die alte "aktuelle" (fake/0,1,2) wird zur
            # neuen "vorherigen", die neue "aktuelle" ist wieder fake/0,1,2: alle 3
            # Treffer sind damit ueber ZWEI Zuege bestaetigt (Kriterium 1).
            faelle += 1
            modus_stop({"transcript_path": str(transcript2), "session_id": "sess0001x"})
            abgelegt2 = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))
            assert abgelegt2["vorherige"] is not None
            assert len(abgelegt2["vorherige"]["treffer"]) == SPITZE_GROESSE
            print(f"  Fall {faelle}: zweiter Zug schiebt 'aktuelle' zu 'vorherige' ok")

            # (b) Dedup: Treffer, der laut recall_log.jsonl dieser Sitzung schon
            # ausgeliefert wurde, erscheint NICHT im Block -- die restlichen 3
            # sind bestaetigt (Kriterium 1) und damit ausgabefaehig.
            faelle += 1
            RECALL_LOG.write_text(json.dumps({
                "session": "sess0001", "nodes": ["/fake/0", "/fake/1"], "lessons": [],
            }) + "\n", encoding="utf-8")
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                modus_prompt({"session_id": "sess0001x"})
            ausgabe = buf.getvalue()
            assert "/fake/0" not in ausgabe and "/fake/1" not in ausgabe
            assert "/fake/2" in ausgabe
            print(f"  Fall {faelle}: (b) bereits gelieferte Treffer bleiben aussen vor ok")

            # (d) verbrauchte Ablage liefert beim zweiten Aufruf nichts mehr.
            faelle += 1
            buf2 = io.StringIO()
            with contextlib.redirect_stdout(buf2):
                modus_prompt({"session_id": "sess0001x"})
            assert buf2.getvalue() == ""
            print(f"  Fall {faelle}: (d) verbrauchte Ablage liefert kein zweites Mal ok")

            # Negativfall --prompt: kein session_id -> still.
            faelle += 1
            buf3 = io.StringIO()
            with contextlib.redirect_stdout(buf3):
                modus_prompt({})
            assert buf3.getvalue() == ""
            print(f"  Fall {faelle}: --prompt ohne session_id -> still ok")

            # (g) Nachtrag: ein ueber diesen Weg (--prompt) ausgeliefertes Fundstueck
            # steht danach selbst in recall_log.jsonl und bleibt beim naechsten
            # Zug aussen vor -- auch wenn dieselbe Suche es erneut liefert.
            faelle += 1
            kms.knowledge_search = fake_search  # liefert wieder fake/0..4
            modus_stop({"transcript_path": str(transcript2), "session_id": "sess0001x"})
            buf4 = io.StringIO()
            with contextlib.redirect_stdout(buf4):
                modus_prompt({"session_id": "sess0001x"})
            assert buf4.getvalue() == "", buf4.getvalue()
            print(f"  Fall {faelle}: (g) ueber --prompt ausgelieferter Treffer kehrt nicht zurueck ok")

            # (c) Deckel gilt fuer ALLE drei Kriterien gemeinsam: 3 bestaetigte
            # Spitzen-Treffer (Kriterium 1) + 2 verbindende Schwanz-Treffer
            # (Kriterium 3) sind 5 Kandidaten, hoechstens 3 duerfen im Block stehen.
            # Eigene Sitzung, direkt konstruierte Ablage -- unabhaengig von der
            # sess0001-Kette oben.
            faelle += 1
            _kappe_spitze = {
                "treffer": [{"kind": "node", "path": f"/kappe/{i}", "title": f"K{i}", "summary": "s"}
                            for i in range(SPITZE_GROESSE)],
                "begriffe": ["kappx"],
            }
            TREFFER_DATEI.write_text(json.dumps({
                "session": "seskappe", "verbraucht": False,
                "vorherige": _kappe_spitze, "aktuelle": _kappe_spitze,
                "statistik": {
                    "schwanz": {
                        "node|/kappe/schwanz1": {"kind": "node", "schluessel": "/kappe/schwanz1",
                                                  "anzahl": SCHWANZ_SCHWELLE, "titel": "V1", "zusammenfassung": "s"},
                        "node|/kappe/schwanz2": {"kind": "node", "schluessel": "/kappe/schwanz2",
                                                  "anzahl": SCHWANZ_SCHWELLE, "titel": "V2", "zusammenfassung": "s"},
                    },
                    "spitze_gesehen": [], "kriterium_feuer": {"1": 0, "2": 0, "3": 0},
                },
            }), encoding="utf-8")
            buf_kappe = io.StringIO()
            with contextlib.redirect_stdout(buf_kappe):
                modus_prompt({"session_id": "seskappex"})
            zeilen_im_block = [z for z in buf_kappe.getvalue().splitlines() if z.startswith("- [")]
            assert len(zeilen_im_block) <= CAP_EINTRAEGE, zeilen_im_block
            assert len(zeilen_im_block) == CAP_EINTRAEGE, zeilen_im_block  # 5 Kandidaten, Deckel bei 3
            print(f"  Fall {faelle}: (c) Deckel haelt ueber alle drei Kriterien gemeinsam ok")

            # (h) Sitzungsobergrenze haelt: 10 bereits ueber diesen Weg protokollierte
            # Eintraege -> modus_prompt bleibt still, auch bei einem bestaetigten
            # (also sonst ausgabefaehigen) Treffer. "vorherige" == "aktuelle" macht
            # den Kandidaten bewusst bestaetigt, damit die Obergrenze isoliert
            # geprueft wird -- nicht vermischt mit der Bestaetigungsfrage.
            faelle += 1
            _cap_treffer = {"treffer": [{"kind": "node", "path": "/cap/neu", "title": "N", "summary": "S"}],
                             "begriffe": ["x"]}
            RECALL_LOG.write_text(json.dumps({
                "session": "sesscap1",
                "nodes": [f"/cap/{i}" for i in range(10)],
                "lessons": [], "ausloeser": "antwort",
            }) + "\n", encoding="utf-8")
            TREFFER_DATEI.write_text(json.dumps({
                "session": "sesscap1", "verbraucht": False,
                "vorherige": _cap_treffer, "aktuelle": _cap_treffer,
            }), encoding="utf-8")
            buf5 = io.StringIO()
            with contextlib.redirect_stdout(buf5):
                modus_prompt({"session_id": "sesscap1xx"})
            assert buf5.getvalue() == "", buf5.getvalue()
            print(f"  Fall {faelle}: (h) Sitzungsobergrenze ({MAX_ANTWORT_EINTRAEGE_JE_SITZUNG}) haelt ok")

            # Negativfall zu (h): Eintraege ueber den NORMALEN Prompt-Weg (kein
            # "ausloeser": "antwort") zaehlen NICHT auf die Obergrenze.
            faelle += 1
            _cap2_treffer = {"treffer": [{"kind": "node", "path": "/cap2/neu", "title": "N", "summary": "S"}],
                              "begriffe": ["x"]}
            RECALL_LOG.write_text(json.dumps({
                "session": "sesscap2", "nodes": [f"/cap2/{i}" for i in range(10)], "lessons": [],
            }) + "\n", encoding="utf-8")
            TREFFER_DATEI.write_text(json.dumps({
                "session": "sesscap2", "verbraucht": False,
                "vorherige": _cap2_treffer, "aktuelle": _cap2_treffer,
            }), encoding="utf-8")
            buf6 = io.StringIO()
            with contextlib.redirect_stdout(buf6):
                modus_prompt({"session_id": "sesscap2xx"})
            assert "/cap2/neu" in buf6.getvalue(), buf6.getvalue()
            print(f"  Fall {faelle}: normaler Prompt-Weg zaehlt nicht auf die Obergrenze ok")

            # --- Nachtrag 3: Bestaetigung ueber zwei Zuege + Differenzmenge ---------

            # NEU-1: Treffer nur in EINER Antwort (nicht in "vorherige"), kein neuer
            # Begriff (gleiche Begriffsmenge wie vorige) -> NICHT ausgegeben.
            faelle += 1
            TREFFER_DATEI.write_text(json.dumps({
                "session": "seskonf1", "verbraucht": False,
                "vorherige": {"treffer": [{"kind": "node", "path": "/other", "title": "X", "summary": "unrelated"}],
                              "begriffe": ["alpha", "beta"]},
                "aktuelle": {"treffer": [{"kind": "node", "path": "/konf/a", "title": "A", "summary": "ganz normaler text"}],
                             "begriffe": ["alpha", "beta"]},
            }), encoding="utf-8")
            buf7 = io.StringIO()
            with contextlib.redirect_stdout(buf7):
                modus_prompt({"session_id": "seskonf1x"})
            assert buf7.getvalue() == "", buf7.getvalue()
            print(f"  Fall {faelle}: nur einmal gesehen, kein neuer Begriff -> nicht ausgegeben ok")

            # NEU-2: derselbe Treffer erneut gefunden (steht in "vorherige" UND
            # "aktuelle") -> bestaetigt, WIRD ausgegeben.
            faelle += 1
            TREFFER_DATEI.write_text(json.dumps({
                "session": "seskonf2", "verbraucht": False,
                "vorherige": {"treffer": [{"kind": "node", "path": "/konf/b", "title": "B", "summary": "text"}],
                              "begriffe": ["alpha"]},
                "aktuelle": {"treffer": [{"kind": "node", "path": "/konf/b", "title": "B", "summary": "text"}],
                             "begriffe": ["alpha"]},
            }), encoding="utf-8")
            buf8 = io.StringIO()
            with contextlib.redirect_stdout(buf8):
                modus_prompt({"session_id": "seskonf2x"})
            assert "/konf/b" in buf8.getvalue(), buf8.getvalue()
            print(f"  Fall {faelle}: in Folgeantwort bestaetigt -> ausgegeben ok")

            # NEU-3: Treffer haengt an einem Begriff, der in "vorherige" fehlte
            # (Differenzmenge) -> SOFORT ausgegeben, ohne zweite Bestaetigung.
            faelle += 1
            TREFFER_DATEI.write_text(json.dumps({
                "session": "seskonf3", "verbraucht": False,
                "vorherige": {"treffer": [{"kind": "node", "path": "/other2", "title": "X", "summary": "alt"}],
                              "begriffe": ["alpha"]},
                "aktuelle": {"treffer": [{"kind": "node", "path": "/konf/c", "title": "C", "summary": "enthaelt zeppelin"}],
                             "begriffe": ["alpha", "zeppelin"]},
            }), encoding="utf-8")
            buf9 = io.StringIO()
            with contextlib.redirect_stdout(buf9):
                modus_prompt({"session_id": "seskonf3x"})
            assert "/konf/c" in buf9.getvalue(), buf9.getvalue()
            print(f"  Fall {faelle}: neuer Begriff schlaegt Bestaetigung -> sofort ausgegeben ok")

            # NEU-4 (Negativfall, Auftragspflicht): erster Zug der Sitzung, keine
            # "vorherige" Antwort -> die Differenzmenge ist LEER, nicht "alles neu".
            # Ohne diese Festlegung wuerde Kriterium 2 beim ersten Zug JEDEN Treffer
            # durchwinken und die Bestaetigungspflicht waere wirkungslos.
            faelle += 1
            TREFFER_DATEI.write_text(json.dumps({
                "session": "seskonf4", "verbraucht": False,
                "vorherige": None,
                "aktuelle": {"treffer": [{"kind": "node", "path": "/konf/d", "title": "D", "summary": "enthaelt zeppelin"}],
                             "begriffe": ["alpha", "zeppelin"]},
            }), encoding="utf-8")
            buf10 = io.StringIO()
            with contextlib.redirect_stdout(buf10):
                modus_prompt({"session_id": "seskonf4x"})
            assert buf10.getvalue() == "", buf10.getvalue()
            print(f"  Fall {faelle}: erster Zug der Sitzung -> Differenzmenge leer, nichts ausgegeben ok")

            # --- Nachtrag 4: drittes Kriterium (verbindende Treffer) ----------------
            # Eine Sitzung, vier Stop-Zuege: /connector liegt in Zug 0-2 immer im
            # Schwanz (nie in der Spitze), in Zug 3 rutscht er in die Spitze. Die
            # Spitze wechselt jeden Zug komplett (andere Pfade) und die Begriffsmenge
            # bleibt gleich (derselbe lange Antworttext) -- damit feuern Kriterium 1
            # und 2 in dieser Sitzung nie, und der Schwanz-Effekt ist isoliert
            # nachweisbar.
            faelle += 1
            zaehler = [0]

            def fake_search_schwanz(query, scope="all", max_results=10, **kw):
                n = zaehler[0]
                zaehler[0] += 1
                if n < 3:
                    spitze = [{"kind": "node", "path": f"/spitze/{n}/{i}", "title": f"S{n}{i}",
                               "summary": "eigenes thema"} for i in range(SPITZE_GROESSE)]
                    schwanz = [{"kind": "node", "path": "/connector", "title": "C",
                                "summary": "verbindet alles"}]
                else:
                    spitze = [{"kind": "node", "path": "/connector", "title": "C", "summary": "verbindet alles"}] + \
                              [{"kind": "node", "path": f"/spitze/{n}/{i}", "title": f"S{n}{i}",
                                "summary": "eigenes thema"} for i in range(SPITZE_GROESSE - 1)]
                    schwanz = []
                rest = [{"kind": "node", "path": f"/rest/{n}/{i}", "title": f"R{n}{i}", "summary": "fuellmaterial"}
                        for i in range(11)]
                return {"results": spitze + schwanz + rest}

            kms.knowledge_search = fake_search_schwanz
            transcript_schw = tmp / "t_schwanz.jsonl"
            transcript_schw.write_text(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": lang}]},  # gleicher Text, gleiche Begriffe
            }) + "\n", encoding="utf-8")

            modus_stop({"transcript_path": str(transcript_schw), "session_id": "sesschw1"})  # n=0
            modus_stop({"transcript_path": str(transcript_schw), "session_id": "sesschw1"})  # n=1, /connector anzahl=2

            # Grenzwert: 2x im Schwanz reicht NICHT.
            buf_schw1 = io.StringIO()
            with contextlib.redirect_stdout(buf_schw1):
                modus_prompt({"session_id": "sesschw1xx"})
            assert buf_schw1.getvalue() == "", buf_schw1.getvalue()
            print(f"  Fall {faelle}: zweimal im Schwanz reicht nicht (Grenzwert) ok")

            faelle += 1
            modus_stop({"transcript_path": str(transcript_schw), "session_id": "sesschw1"})  # n=2, /connector anzahl=3
            buf_schw2 = io.StringIO()
            with contextlib.redirect_stdout(buf_schw2):
                modus_prompt({"session_id": "sesschw1xx"})
            ausgabe_schw = buf_schw2.getvalue()
            assert "/connector" in ausgabe_schw, ausgabe_schw
            assert "verbindender Treffer" in ausgabe_schw, ausgabe_schw
            statistik_nach_3 = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))["statistik"]
            assert statistik_nach_3["kriterium_feuer"]["3"] == 1, statistik_nach_3
            print(f"  Fall {faelle}: dreimal im Schwanz, nie Spitze -> ausgegeben, "
                  f"als verbindend gekennzeichnet, Feuerzaehler lesbar ok")

            faelle += 1
            modus_stop({"transcript_path": str(transcript_schw), "session_id": "sesschw1"})  # n=3, /connector in Spitze
            buf_schw3 = io.StringIO()
            with contextlib.redirect_stdout(buf_schw3):
                modus_prompt({"session_id": "sesschw1xx"})
            assert "/connector" not in buf_schw3.getvalue(), buf_schw3.getvalue()
            statistik_nach_4 = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))["statistik"]
            # Feuerzaehler 3 bleibt bei 1 -- /connector zaehlt nicht nochmal, weil es
            # inzwischen (Zug 3) in der Spitze stand. Dedup-unabhaengiger Beleg:
            # der Feuerzaehler steigt nur, wenn ein Kriterium wirklich zugeschlagen hat.
            assert statistik_nach_4["kriterium_feuer"]["3"] == 1, statistik_nach_4
            print(f"  Fall {faelle}: einmal in der Spitze gewesen -> ueber Kriterium 3 nicht mehr ausgabefaehig ok")

            # --- Nachtrag 5: Verwendungs-Statistik (Auftrag L-ff8fff) ---------------
            # Direkt konstruierte Ablage mit "ausgespielt_offen" -- isoliert von
            # Kriterium 1/2/3, prueft nur ob die vorige Ausspielung in der neuen
            # Antwort VORKAM. Vier Eintraege decken (a) woertlich, (b) genau
            # BEGRIFFLICH_MIN Begriffe -> begrifflich (Grenzwert, "genau darauf
            # ja"), (c) BEGRIFFLICH_MIN-1 Begriffe -> nicht_verwendet (Grenzwert,
            # "eins darunter nein"), (d) keine Begriffe -> nicht_verwendet.
            faelle += 1
            kms.knowledge_search = fake_search  # muss nichtleer sein, sonst kehrt
            # modus_stop vor der Verwendungspruefung zurueck (siehe Reihenfolge
            # im Code: leere Treffer -> frueher return, VOR _verwendung_pruefen).
            TREFFER_DATEI.write_text(json.dumps({
                "session": "verw0001", "verbraucht": True,
                "vorherige": None, "aktuelle": None,
                "statistik": {
                    "schwanz": {}, "spitze_gesehen": [], "kriterium_feuer": {"1": 0, "2": 0, "3": 0},
                    "verwendung": {"geliefert": 3, "woertlich": 0, "begrifflich": 0, "nicht_verwendet": 0},
                    "ausgespielt_offen": [
                        {"kind": "node", "schluessel": "/verw/woertlich", "begriffe": ["alpha", "beta", "gamma"]},
                        {"kind": "node", "schluessel": "/verw/zwei", "begriffe": ["delta", "epsilon", "zeta"]},
                        {"kind": "node", "schluessel": "/verw/eins", "begriffe": ["theta", "iota", "kappa"]},
                        {"kind": "node", "schluessel": "/verw/null", "begriffe": ["lambda", "omikron", "sigma"]},
                    ],
                },
            }), encoding="utf-8")
            # WICHTIG: die drei "abwesenden" Begriffe (zeta, iota, kappa, lambda,
            # omikron, sigma) duerfen NICHT im Text stehen -- auch nicht in einem
            # Satz, der ihre Abwesenheit behauptet ("... zeta kommt nicht vor").
            # Der Abgleich ist reine Tokenmenge ohne Verneinungserkennung, ein
            # erwaehntes Wort zaehlt als vorhanden, egal in welchem Satzzusammenhang.
            antwort_verw = (
                "Die Antwort erwaehnt /verw/woertlich woertlich als Kennung. "
                "Ausserdem kommen delta und epsilon vor. Auch theta ist dabei. "
                + ("fuellstoff " * 60)
            )
            transcript_verw = tmp / "t_verw.jsonl"
            transcript_verw.write_text(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": antwort_verw}]},
            }) + "\n", encoding="utf-8")
            modus_stop({"transcript_path": str(transcript_verw), "session_id": "verw0001x"})
            statistik_verw = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))["statistik"]
            verwendung = statistik_verw["verwendung"]
            assert verwendung["woertlich"] == 1, verwendung           # (a) Kennung im Text
            assert verwendung["begrifflich"] == 1, verwendung         # (b) Grenzwert: genau 2 Begriffe -> ja
            assert verwendung["nicht_verwendet"] == 2, verwendung     # (c)+(d): 1 Begriff und 0 Begriffe -> nein
            assert verwendung["geliefert"] == 3, verwendung           # unveraendert -- nur modus_prompt erhoeht das
            assert statistik_verw["ausgespielt_offen"] == [], statistik_verw
            print(f"  Fall {faelle}: (i) woertlich/begrifflich(Grenzwert ja)/nicht_verwendet(Grenzwert nein) "
                  f"in einem Zug erkannt, ausgespielt_offen geleert ok")

            # (j) kumulativ: ein zweiter Zug mit neuer Ausspielung addiert sich zu
            # den Zaehlern von oben, statt sie zu ueberschreiben.
            faelle += 1
            statistik_verw["ausgespielt_offen"] = [
                {"kind": "node", "schluessel": "/verw/zweite/runde", "begriffe": ["omega", "psi", "chi"]},
            ]
            TREFFER_DATEI.write_text(json.dumps({
                "session": "verw0001", "verbraucht": True,
                "vorherige": None, "aktuelle": None, "statistik": statistik_verw,
            }), encoding="utf-8")
            antwort_verw2 = "Kein Bezug, andere Themen. " + ("fuellstoff " * 60)
            transcript_verw2 = tmp / "t_verw2.jsonl"
            transcript_verw2.write_text(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": antwort_verw2}]},
            }) + "\n", encoding="utf-8")
            modus_stop({"transcript_path": str(transcript_verw2), "session_id": "verw0001x"})
            statistik_verw2 = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))["statistik"]
            verwendung2 = statistik_verw2["verwendung"]
            assert verwendung2["woertlich"] == 1, verwendung2         # unveraendert vom ersten Zug
            assert verwendung2["begrifflich"] == 1, verwendung2       # unveraendert vom ersten Zug
            assert verwendung2["nicht_verwendet"] == 3, verwendung2   # 2 (erster Zug) + 1 (neuer, unbenutzter Eintrag)
            print(f"  Fall {faelle}: (j) Verwendungszaehler sind kumulativ ueber zwei Zuege ok")

            # (k) modus_prompt selbst schreibt "geliefert" und "ausgespielt_offen"
            # beim Ausspielen -- Ende-zu-Ende ohne direkt konstruierte Ablage.
            faelle += 1
            TREFFER_DATEI.write_text(json.dumps({
                "session": "verw0002", "verbraucht": False,
                "vorherige": {"treffer": [{"kind": "node", "path": "/e2e/a", "title": "EA", "summary": "text"}],
                              "begriffe": ["alpha"]},
                "aktuelle": {"treffer": [{"kind": "node", "path": "/e2e/a", "title": "EA", "summary": "text"}],
                             "begriffe": ["alpha"]},
            }), encoding="utf-8")
            buf_e2e = io.StringIO()
            with contextlib.redirect_stdout(buf_e2e):
                modus_prompt({"session_id": "verw0002x"})
            assert "/e2e/a" in buf_e2e.getvalue(), buf_e2e.getvalue()
            statistik_e2e = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))["statistik"]
            assert statistik_e2e["verwendung"]["geliefert"] == 1, statistik_e2e
            assert len(statistik_e2e["ausgespielt_offen"]) == 1, statistik_e2e
            assert statistik_e2e["ausgespielt_offen"][0]["schluessel"] == "/e2e/a", statistik_e2e
            print(f"  Fall {faelle}: (k) modus_prompt traegt Ausspielung selbst in "
                  f"'geliefert'/'ausgespielt_offen' ein ok")

    finally:
        TREFFER_DATEI, RECALL_LOG = orig_treffer, orig_log
        kms.knowledge_search = orig_search

    print(f"Selbsttest: {faelle} Faelle, alle ok")


if __name__ == "__main__":
    main()
