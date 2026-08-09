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
MAX_RESULTS_STOP = 5    # knowledge_search max_results am Stop-Haltepunkt
CAP_EINTRAEGE = 3       # Deckel Auftrag
CAP_ZEICHEN = 1200      # Deckel Auftrag

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

    # Vergleichsstand fuer die Bestaetigung: die ALTE "aktuelle" Ablage
    # wird zur neuen "vorherigen" -- nur wenn sie zur selben Sitzung
    # gehoert, sonst gibt es (wie beim allerersten Zug) keinen Vergleich.
    vorherige = None
    try:
        with open(TREFFER_DATEI, encoding="utf-8") as f:
            alt = json.load(f)
        if alt.get("session") == session8:
            vorherige = alt.get("aktuelle")
    except (OSError, json.JSONDecodeError):
        pass

    daten = {
        "session": session8,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verbraucht": False,
        "vorherige": vorherige,
        "aktuelle": {"treffer": treffer, "begriffe": begriffe},
    }
    with open(TREFFER_DATEI, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False)


# --- Betriebsart --prompt ---------------------------------------------------

def _bereits_geliefert(session: str) -> tuple[set, set, int]:
    """Pfade/Kennungen, die recall_log.jsonl fuer diese Sitzung schon
    ausgeliefert hat -- ueber ALLE Zeilen dieser Sitzung, nicht nur die
    letzte -- plus wieviele davon ueber DIESEN Weg kamen (quelle=="antwort",
    fuer die Sitzungsobergrenze). Zeilen des normalen Prompt-Wegs (kein
    "quelle"-Feld) zaehlen fuer den Dedup mit, aber NICHT auf die
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
                if d.get("quelle") == "antwort":
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
    naechsten Zug greift, plus "quelle": "antwort" zur Kennzeichnung des
    Wegs. Beiwerk, darf die Ausgabe nie zum Scheitern bringen."""
    zeile = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nodes": [s for k, s, _ in eintraege if k == "node"],
        "lessons": [s for k, s, _ in eintraege if k == "lesson"],
        "session": session,
        "quelle": "antwort",
    }
    try:
        with open(RECALL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ausgabefaehig(aktuelle: dict, vorherige: dict | None) -> list[tuple[str, str, str]]:
    """Wendet die Bestaetigung-ueber-zwei-Zuege-Regel an (siehe Moduldoc).
    vorherige=None (erster Zug der Sitzung) -> keine Bestaetigungsbasis UND
    eine leere Differenzmenge, sonst wuerde jeder Begriff beim ersten Zug
    als 'neu' gelten und die Bestaetigungspflicht wirkungslos machen."""
    vorherige_treffer = (vorherige or {}).get("treffer") or []
    vorherige_schluessel = {_schluessel_und_zeile(e)[:2] for e in vorherige_treffer}
    if vorherige is not None:
        neue_begriffe = set(aktuelle.get("begriffe") or []) - set(vorherige.get("begriffe") or [])
    else:
        neue_begriffe = set()

    ausgefiltert = []
    for e in aktuelle.get("treffer") or []:
        kind, schluessel, zeile = _schluessel_und_zeile(e)
        bestaetigt = (kind, schluessel) in vorherige_schluessel
        text = f"{e.get('title') or e.get('type') or ''} {e.get('summary') or ''} {schluessel}"
        hat_neuen_begriff = bool(pruefkorpus.tokenize(text) & neue_begriffe)
        if bestaetigt or hat_neuen_begriff:
            ausgefiltert.append((kind, schluessel, zeile))
    return ausgefiltert


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

    kandidaten = _ausgabefaehig(daten.get("aktuelle") or {}, daten.get("vorherige"))
    if not kandidaten:
        return

    geliefert_nodes, geliefert_lessons, antwort_bisher = _bereits_geliefert(session)
    verfuegbar = MAX_ANTWORT_EINTRAEGE_JE_SITZUNG - antwort_bisher
    if verfuegbar <= 0:
        return

    kandidaten = [
        (kind, schluessel, zeile) for kind, schluessel, zeile in kandidaten
        if schluessel not in (geliefert_lessons if kind == "lesson" else geliefert_nodes)
    ]
    if not kandidaten:
        return

    kandidaten = kandidaten[:min(CAP_EINTRAEGE, verfuegbar)]
    while kandidaten:
        block = "\n".join([KOPF, HINWEIS, *[z for _, _, z in kandidaten], FUSS])
        if len(block) <= CAP_ZEICHEN:
            break
        kandidaten.pop()  # Ueberzaehliges wird verworfen, nicht gekuerzt
    if not kandidaten:
        return

    print(block)
    daten["verbraucht"] = True
    try:
        with open(TREFFER_DATEI, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False)
    except OSError:
        pass
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
        return {"results": [
            {"kind": "node", "path": f"/fake/{i}", "title": f"T{i}", "summary": f"S{i}"}
            for i in range(5)
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
            assert len(abgelegt["aktuelle"]["treffer"]) == 5
            print(f"  Fall {faelle}: (f) lange Antwort -> Ablage mit Attrappen-Treffern, erster Zug ok")

            # Zweiter Zug, dieselben Treffer -> die alte "aktuelle" (fake/0..4) wird zur
            # neuen "vorherigen", die neue "aktuelle" ist wieder fake/0..4: alle 5
            # Treffer sind damit ueber ZWEI Zuege bestaetigt (Kriterium 1).
            faelle += 1
            modus_stop({"transcript_path": str(transcript2), "session_id": "sess0001x"})
            abgelegt2 = json.loads(TREFFER_DATEI.read_text(encoding="utf-8"))
            assert abgelegt2["vorherige"] is not None
            assert len(abgelegt2["vorherige"]["treffer"]) == 5
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

            # (c) Deckel: von den verbleibenden 3 (fake/2,3,4) stehen hoechstens 3 im Block.
            faelle += 1
            zeilen_im_block = [z for z in ausgabe.splitlines() if z.startswith("- [")]
            assert len(zeilen_im_block) <= CAP_EINTRAEGE, zeilen_im_block
            assert len(zeilen_im_block) == 3, zeilen_im_block  # genau die 3 uebrigen
            print(f"  Fall {faelle}: (c) Deckel haelt (<= {CAP_EINTRAEGE} Eintraege) ok")

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
                "lessons": [], "quelle": "antwort",
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
            # "quelle": "antwort") zaehlen NICHT auf die Obergrenze.
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

    finally:
        TREFFER_DATEI, RECALL_LOG = orig_treffer, orig_log
        kms.knowledge_search = orig_search

    print(f"Selbsttest: {faelle} Faelle, alle ok")


if __name__ == "__main__":
    main()
