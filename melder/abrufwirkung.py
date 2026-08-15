#!/usr/bin/env python3
"""Abrufwirkung -- dauerhafter Verlauf statt einmaliger Messung.

ANLASS (Betreiber 2026-08-15, woertlich): "Bitte, ich hoffe du hast es
trotzdem direkt eingebaut, es jetzt schon zu haben ist kein Fehler!" -- die
Messung vom selben Tag (runs/abrufwirkung_2026-08-15T131451+0200.json: 334
eingespielte Kennungen, 37 nachgewiesen benutzt, 11,1%) war ein einmaliges
Skript, nicht Teil des Repos. Dieses Modul macht daraus ein wiederholbares
Werkzeug MIT GEDAECHTNIS: je Kennung ein VERLAUF, nicht nur eine Momentzahl.

DIE DREI EREIGNISSE je Kennung (Bauform uebernommen von kern/baustein.py::
herkunftsverlauf, Feld zurueckgenommen_am -- ERGAENZEN statt neu anlegen):

    eingespielt   <knowledge-recall> hat die Kennung in den Chat gebracht.
    benutzt       die Kennung taucht NACH ihrer fruehesten Einspielung in
                  einem Agentenauftrag (Werkzeug 'Agent') oder einem neuen
                  Wissenseintrag (mcp__knowledge__knowledge_add/lesson_record)
                  wieder auf -- ODER, git-zeitstempelgeprueft, in einem
                  spaeteren Commit dieses Repos.
    unbeachtet    bis zum Ende dieses Laufs kein Beleg fuer Benutzung.

SPAETWIRKUNG (der eigentliche Punkt des Auftrags): wird eine Kennung
zunaechst unbeachtet erneut eingespielt und ERST DANN benutzt, steht das in
DEMSELBEN Eintrag -- "zweimal weggelegt, beim dritten Mal gegriffen" statt
drei unverbundene Zeilen. Siehe verlauf_aktualisieren().

WARUM KEINE NEUE DATENBANKSPALTE (Auftrag verlangte die Pruefung):
knowledge_nodes.abgeleitet_von, knowledge_nodes/lessons_learned/access_log.
bedient_von sind alle drei mit demselben Kommentar belegt ("WER FUEHRT DIE
MASCHINE, die hier geschrieben hat" -- Ausweis-Herkunft, ausschliesslich aus
kern/ausweis.py). Das ist Schreiber-Identitaet, keine Nutzungsspur -- eine
andere Frage mit anderem Antwortraum (ein NAME vs. ein VERLAUF aus Ereig-
nissen). Eine dieser Spalten zu belegen waere falsch etikettiert, keine
Wiederverwendung. Der Verlauf liegt deshalb wie recall_log.jsonl/
wissensverlauf.jsonl NEBEN der Datenbank, nicht darin -- gleiche Begruendung
wie dort: keine Schreibsperre quer durchs Fleet fuer ein Signal, das nur
gelegentlich (nicht bei jedem Prompt) erhoben wird. Anders als die beiden
genannten ist die Datei aber kein Append-only-JSONL, sondern EIN JSON-Objekt
je Kennung (amendierbar, wie kern/baustein.py::herkunftsverlauf) -- ein
Ereignis MUSS an einen bestehenden Eintrag andocken koennen, das verbietet
Append-only.

DREI AUFLAGEN, siehe Auftrag (L-8b377b, L-f61f86, L-79ec88):

  1. ROH vs. NORMIERT (L-8b377b). Rohe Einspielungen sind SCHIEF verteilt
     (ein haeufig gezogener Eintrag draengt sich vor) -- der Wirkungsgrad
     wird deshalb NORMIERT ausgewiesen (je Kennung EINMAL gezaehlt,
     unabhaengig von der Einspielhaeufigkeit), zusaetzlich zur rohen,
     einspielgewichteten Zahl UND dem Anteil der drei haeufigsten Kennungen
     an allen Einspielungen (>50% heisst: die Zahl beschreibt die Suche).
  2. Kein Signal, das nur eine Richtung kennt (L-f61f86) -- siehe
     tests/test_abrufwirkung.py: Positivbeleg UND Negativbeleg am echten
     Bestand, nicht nur am Testfall.
  3. Keine Selbstauskunft (L-79ec88) -- ausschliesslich objektive Spuren:
     Transkript-Text (Werkzeugaufrufe, keine Chat-Prosa) und git log mit
     Zeitstempelvergleich.

ZWEI FALLEN, beide mit eigenem Test gegen echte Daten (siehe Tests):

  Zeitrichtung: ein Commit, der die Kennung nennt, zaehlt nur, wenn sein
  Zeitstempel NACH der fruehesten Einspielung liegt -- sonst hat der Commit
  den Eintrag selbst erst erzeugt und zitiert sich dabei selbst.
  Wortgrenzen: eine Pfad-Kennung wie '/brainlehr' darf nicht als Substring
  in '/brainlehr/irgendwas' oder '/brainlehr-ausweise' treffen -- das ist
  der Ablageort, kein Zitat.

Aufruf:
    python3 abrufwirkung.py --lauf <transkript.jsonl> [--seit-git ISO-DATUM]
                             [--verlauf <pfad>] [--bericht]
    python3 abrufwirkung.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterator

import zeitmarke  # noqa: E402

STANDARD_VERLAUF = _w / "abrufwirkung_verlauf.json"

# --- Kennungen erkennen ----------------------------------------------------

# Lehren: L- + 6 Hex-Ziffern, nicht als Teil eines laengeren Tokens.
_KENNUNG_LEHRE_RE = re.compile(r"(?<![0-9A-Za-z_])L-[0-9a-f]{6}(?![0-9A-Za-z_])")
# Knoten in <knowledge-recall>-Bloecken: '[/pfad/mit-bindestrichen]'.
_KENNUNG_KNOTEN_KLAMMER_RE = re.compile(r"\[(/[^\]\s]+)\]")


def kennungen_aus_block(text: str) -> dict[str, str]:
    """Kennung -> 'lehre'|'knoten', aus dem Text eines eingespielten Blocks."""
    out: dict[str, str] = {}
    for m in _KENNUNG_LEHRE_RE.finditer(text):
        out[m.group(0)] = "lehre"
    for m in _KENNUNG_KNOTEN_KLAMMER_RE.finditer(text):
        out[m.group(1)] = "knoten"
    return out


def wortgrenzen_treffer(text: str, kennung: str, ist_pfad: bool) -> bool:
    """FALLE 2: eine Pfad-Kennung darf nicht als Substring eines laengeren
    Pfads treffen ('/brainlehr' in '/brainlehr/irgendwas' oder
    '/brainlehr-ausweise' ist KEIN Treffer, siehe Modul-Docstring)."""
    if ist_pfad:
        muster = re.compile(r"(?<![\w/-])" + re.escape(kennung) + r"(?![\w/-])")
    else:
        muster = re.compile(r"(?<![0-9A-Za-z_])" + re.escape(kennung) + r"(?![0-9A-Za-z_])")
    return bool(muster.search(text))


# --- Transkript lesen (zeilenweise, nie am Stueck) --------------------------

def transkript_zeilen(pfad: Path | str) -> Iterator[tuple[int, dict]]:
    """(seq, geparste Zeile) je nicht-leerer Zeile -- seq ist eine reine
    Sitzungs-Sequenznummer, nur INNERHALB dieses Transkripts vergleichbar."""
    seq = 0
    with open(pfad, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            seq += 1
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            yield seq, d


def einspielungen_aus_transkript(pfad: Path | str) -> list[dict]:
    """[{seq, ts, kennung, art}] -- ein Eintrag je Kennung je Block, in
    Transkriptreihenfolge. ts kommt roh aus der Zeile (noch nicht
    normiert)."""
    out: list[dict] = []
    for seq, d in transkript_zeilen(pfad):
        att = d.get("attachment")
        if not (isinstance(att, dict) and att.get("type") == "hook_additional_context"):
            continue
        inhalt = att.get("content") or []
        text = "\n".join(c for c in inhalt if isinstance(c, str))
        if "<knowledge-recall>" not in text:
            continue
        ts = d.get("timestamp")
        for kennung, art in kennungen_aus_block(text).items():
            out.append({"seq": seq, "ts": ts, "kennung": kennung, "art": art})
    return out


_WERKZEUGE_AUFTRAG = {"Agent"}
_WERKZEUGE_SCHREIBEND = {"mcp__knowledge__knowledge_add", "mcp__knowledge__lesson_record"}


def _tool_use_texte(d: dict, namen: set[str]) -> list[str]:
    msg = d.get("message")
    if not isinstance(msg, dict):
        return []
    content = msg.get("content")
    if not isinstance(content, list):
        return []
    out = []
    for c in content:
        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in namen:
            out.append(json.dumps(c.get("input") or {}, ensure_ascii=False))
    return out


def verwendungen_aus_transkript(pfad: Path | str, gesuchte: dict[str, str],
                                 grenze_seq: dict[str, int]) -> dict[str, dict]:
    """Kennung -> {seq, ts, quelle='transkript'} -- der ERSTE Fund NACH der
    fruehesten Einspielung (grenze_seq) in einem Agentenauftrag oder einem
    knowledge_add/lesson_record-Aufruf. Reiner Assistenten-Fliesstext zaehlt
    NICHT (nur Werkzeugaufrufe, siehe _tool_use_texte)."""
    gefunden: dict[str, dict] = {}
    offen = set(gesuchte)
    for seq, d in transkript_zeilen(pfad):
        if not offen:
            break
        texte = None
        for kennung in list(offen):
            grenze = grenze_seq.get(kennung)
            if grenze is None or seq <= grenze:
                continue
            if texte is None:
                texte = _tool_use_texte(d, _WERKZEUGE_AUFTRAG | _WERKZEUGE_SCHREIBEND)
                if not texte:
                    texte = []
            ist_pfad = gesuchte[kennung] == "knoten"
            for text in texte:
                if wortgrenzen_treffer(text, kennung, ist_pfad):
                    gefunden[kennung] = {"seq": seq, "ts": d.get("timestamp"), "quelle": "transkript"}
                    offen.discard(kennung)
                    break
    return gefunden


# --- Git-Kanal (FALLE 1: Zeitrichtung) --------------------------------------

def _git_commits(wurzel: Path, seit: str) -> list[tuple[str, str, str]]:
    """[(hash, ts_utc, text)] in chronologischer Reihenfolge (aeltester
    zuerst), text = Nachricht + Diff. seit: Datum/Zeit fuer `git log
    --since`."""
    lauf = subprocess.run(
        ["git", "-C", str(wurzel), "log", "--since", seit, "--reverse", "--format=%H"],
        capture_output=True, text=True, check=False,
    )
    out = []
    for h in (l.strip() for l in lauf.stdout.splitlines() if l.strip()):
        meta = subprocess.run(
            ["git", "-C", str(wurzel), "show", "-s", "--format=%aI%x1f%B", h],
            capture_output=True, text=True, check=False,
        )
        if "\x1f" not in meta.stdout:
            continue
        ts_roh, nachricht = meta.stdout.split("\x1f", 1)
        diff = subprocess.run(
            ["git", "-C", str(wurzel), "show", "--format=", h],
            capture_output=True, text=True, check=False,
        )
        try:
            ts_utc = zeitmarke.nach_utc(ts_roh.strip())
        except ValueError:
            continue
        out.append((h, ts_utc, nachricht + "\n" + diff.stdout))
    return out


def git_verwendungen(wurzel: Path, gesuchte: dict[str, str], grenze_ts: dict[str, str],
                      seit: str) -> dict[str, dict]:
    """Kennung -> {ts, quelle='git:<kurzhash>'} -- FALLE 1: ein Commit
    zaehlt nur, wenn sein Zeitstempel (UTC-normiert) NACH grenze_ts[kennung]
    liegt (String-Vergleich ist gueltig, weil beide Seiten durch
    zeitmarke.nach_utc auf dieselbe Form gebracht sind)."""
    commits = _git_commits(wurzel, seit)
    gefunden: dict[str, dict] = {}
    for kennung, art in gesuchte.items():
        if kennung in gefunden:
            continue
        grenze = grenze_ts.get(kennung)
        if grenze is None:
            continue
        ist_pfad = art == "knoten"
        for h, ts_utc, text in commits:
            if ts_utc <= grenze:
                continue
            if wortgrenzen_treffer(text, kennung, ist_pfad):
                gefunden[kennung] = {"ts": ts_utc, "quelle": f"git:{h[:8]}"}
                break
    return gefunden


# --- Verlauf: lesen, ergaenzen, schreiben -----------------------------------

def verlauf_lesen(pfad: Path | str) -> dict:
    pfad = Path(pfad)
    if not pfad.exists():
        return {}
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def verlauf_schreiben(pfad: Path | str, daten: dict) -> None:
    pfad = Path(pfad)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1, sort_keys=True)
    tmp.replace(pfad)


def _ts_schluessel(ereignis: dict):
    try:
        return zeitmarke.nach_utc(ereignis.get("ts") or "")
    except ValueError:
        return ereignis.get("ts") or ""


def verlauf_aktualisieren(bestehend: dict, kennung: str, art: str,
                           neue_ereignisse: list[dict]) -> dict:
    """DIE BAUFORM des Auftrags (uebernommen von kern/baustein.py::
    herkunftsverlauf): ein Eintrag je Kennung wird ERGAENZT, nie neu
    angelegt. Ereignisse werden nach Zeitstempel sortiert eingefuegt -- so
    entsteht die Zeile 'zweimal weggelegt, beim dritten Mal gegriffen'
    (eingespielt, eingespielt, benutzt, eingespielt in genau dieser
    Reihenfolge, nicht in Einfuegereihenfolge)."""
    eintrag = bestehend.setdefault(kennung, {"art": art, "ereignisse": []})
    eintrag["ereignisse"].extend(neue_ereignisse)
    eintrag["ereignisse"].sort(key=_ts_schluessel)
    return bestehend


def _hat_benutzt(eintrag: dict) -> bool:
    return any(e.get("ereignis") == "benutzt" for e in eintrag.get("ereignisse", []))


# --- Ein Lauf: ein Transkript (+ optional Git) auswerten --------------------

def lauf(transkript_pfad: Path | str, wurzel: Path, jetzt_ts: str,
          verlauf_pfad: Path | str | None = None,
          git_seit: str | None = None) -> dict:
    """Fuehrt einen Auswertungslauf durch, ergaenzt den persistenten
    Verlauf und liefert den Bericht dieses Laufs (roh + normiert, siehe
    Modul-Docstring Auflage 1)."""
    verlauf_pfad = verlauf_pfad if verlauf_pfad is not None else STANDARD_VERLAUF
    bestand = verlauf_lesen(verlauf_pfad)

    einspielungen = einspielungen_aus_transkript(transkript_pfad)
    if not einspielungen:
        return {"kennungen_gesamt": 0, "einspielungen_roh": 0, "hinweis": "keine Einspielung im Transkript"}

    art_je_kennung: dict[str, str] = {}
    erste_seq: dict[str, int] = {}
    erste_ts: dict[str, str] = {}
    je_kennung: dict[str, list[dict]] = {}
    for e in einspielungen:
        k = e["kennung"]
        art_je_kennung[k] = e["art"]
        je_kennung.setdefault(k, []).append(e)
        if k not in erste_seq or e["seq"] < erste_seq[k]:
            erste_seq[k] = e["seq"]
            erste_ts[k] = zeitmarke.nach_utc(e["ts"]) if e.get("ts") else None

    benutzt_transkript = verwendungen_aus_transkript(transkript_pfad, art_je_kennung, erste_seq)

    fehlend_nach_transkript = {k: v for k, v in art_je_kennung.items() if k not in benutzt_transkript}
    benutzt_git: dict[str, dict] = {}
    if git_seit and fehlend_nach_transkript:
        grenze_ts_fuer_git = {k: erste_ts[k] for k in fehlend_nach_transkript if erste_ts.get(k)}
        benutzt_git = git_verwendungen(wurzel, fehlend_nach_transkript, grenze_ts_fuer_git, git_seit)

    benutzte_kennungen: dict[str, dict] = {**benutzt_transkript, **benutzt_git}

    for k, art in art_je_kennung.items():
        neue: list[dict] = []
        for e in je_kennung[k]:
            ts = zeitmarke.nach_utc(e["ts"]) if e.get("ts") else jetzt_ts
            neue.append({"ereignis": "eingespielt", "ts": ts, "seq": e["seq"],
                         "quelle": str(transkript_pfad)})
        treffer = benutzte_kennungen.get(k)
        if treffer is not None:
            ts = treffer.get("ts") or jetzt_ts
            neue.append({"ereignis": "benutzt", "ts": ts, "seq": treffer.get("seq"),
                         "quelle": treffer["quelle"]})
        else:
            neue.append({"ereignis": "unbeachtet", "ts": jetzt_ts, "seq": None, "quelle": "lauf"})
        verlauf_aktualisieren(bestand, k, art, neue)

    verlauf_schreiben(verlauf_pfad, bestand)

    # --- Bericht: roh vs. normiert (Auflage 1) ---
    haeufigkeit = Counter(e["kennung"] for e in einspielungen)
    einspielungen_roh = sum(haeufigkeit.values())
    kennungen_gesamt = len(haeufigkeit)
    top3_summe = sum(n for _, n in haeufigkeit.most_common(3))
    top3_anteil = round(100 * top3_summe / einspielungen_roh, 1) if einspielungen_roh else 0.0

    benutzte = set(benutzte_kennungen)
    normiert_quote = round(100 * len(benutzte) / kennungen_gesamt, 1) if kennungen_gesamt else 0.0
    # Roh-Quote: einspielgewichtet -- eine haeufig gezogene, EINMAL benutzte
    # Kennung zaehlt hier mit ALL ihren Einspielungen (der Verzerrungseffekt,
    # den L-8b377b beschreibt).
    roh_treffer = sum(haeufigkeit[k] for k in benutzte)
    roh_quote = round(100 * roh_treffer / einspielungen_roh, 1) if einspielungen_roh else 0.0

    spaetwirkung = []
    for k in benutzte:
        treffer = benutzte_kennungen[k]
        nutz_seq = treffer.get("seq")
        if nutz_seq is None:
            vor = len(je_kennung[k])  # git-Fund: alle bekannten Einspielungen liegen davor
        else:
            vor = sum(1 for e in je_kennung[k] if e["seq"] < nutz_seq)
        if vor >= 2:
            spaetwirkung.append(k)

    return {
        "kennungen_gesamt": kennungen_gesamt,
        "einspielungen_roh": einspielungen_roh,
        "top3_anteil_prozent": top3_anteil,
        "benutzt_kennungen": sorted(benutzte),
        "anzahl_benutzt": len(benutzte),
        "quote_normiert_prozent": normiert_quote,
        "quote_roh_prozent": roh_quote,
        "spaetwirkung_kennungen": sorted(spaetwirkung),
        "hinweis_normierung": (
            "quote_normiert_prozent zaehlt jede Kennung EINMAL, unabhaengig von "
            "ihrer Einspielhaeufigkeit -- quote_roh_prozent gewichtet nach "
            "Haeufigkeit und ueberschaetzt haeufig eingespielte Kennungen "
            "(L-8b377b). top3_anteil_prozent > 50 heisst: die Zahl beschreibt "
            "die Suche, nicht die Wirkung."
        ),
    }


# --- CLI ---------------------------------------------------------------

def _cli(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lauf", metavar="TRANSKRIPT")
    p.add_argument("--seit-git", metavar="ISO-DATUM")
    p.add_argument("--verlauf", metavar="PFAD")
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    if not args.lauf:
        p.error("--lauf <transkript.jsonl> oder --selftest erforderlich")

    ergebnis = lauf(args.lauf, _w, zeitmarke.jetzt(),
                     verlauf_pfad=args.verlauf, git_seit=args.seit_git)
    if args.bericht or True:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=1))
    return 0


# --- Selbsttest ----------------------------------------------------------

def _selftest() -> None:
    import tempfile

    JETZT = "2026-08-15T12:00:00Z"

    # A) kennungen_aus_block: beide Formen.
    block = ("<knowledge-recall>\n- [/tools/beispiel-pfad] [1 Tag alt] ...\n"
             "(error, 1x, L-abcdef, Sitzung ...)")
    kk = kennungen_aus_block(block)
    assert kk == {"/tools/beispiel-pfad": "knoten", "L-abcdef": "lehre"}, kk

    # B) wortgrenzen_treffer -- FALLE 2, echtes Fundstueck aus `git log -p`
    #    dieses Repos (2026-08-15): '/brainlehr' ist Praefix von
    #    '/brainlehr/betreiberentscheidung-adr-020' und von
    #    '/brainlehr-ausweise' -- beides KEIN Treffer.
    echt_1 = "+ neuer Knoten unter /brainlehr/betreiberentscheidung-adr-020 angelegt"
    echt_2 = "backup nach /brainlehr-ausweise/ verschoben"
    echt_3 = "Astknoten liegt unter /brainlehr, direkt darunter"
    assert wortgrenzen_treffer(echt_1, "/brainlehr", ist_pfad=True) is False, echt_1
    assert wortgrenzen_treffer(echt_2, "/brainlehr", ist_pfad=True) is False, echt_2
    assert wortgrenzen_treffer(echt_3, "/brainlehr", ist_pfad=True) is True, echt_3
    # naiver Substring-Vergleich (ohne Wortgrenzen) waere bei allen drei
    # positiv -- das IST die Falle, siehe Test test_wortgrenzen_faelschlich_...
    assert "/brainlehr" in echt_1 and "/brainlehr" in echt_2

    # C) Transkript-Parser + Verwendungserkennung, synthetisches Mini-Protokoll.
    with tempfile.TemporaryDirectory() as td:
        transkript = Path(td) / "sitzung.jsonl"
        zeilen = [
            {"attachment": {"type": "hook_additional_context",
                             "content": ["<knowledge-recall>\n(error, 1x, L-c9f9e9, Sitzung x)"]},
             "timestamp": "2026-08-15T10:00:00.000Z"},
            {"message": {"content": [{"type": "text", "text": "L-c9f9e9 erwaehnt, aber kein Werkzeug"}]}},
            {"message": {"content": [{"type": "tool_use", "name": "Agent",
                                       "input": {"prompt": "siehe L-c9f9e9: Grundrauschen"}}]},
             "timestamp": "2026-08-15T10:05:00.000Z"},
            # zweite Kennung, nie benutzt -> muss 'unbeachtet' bleiben.
            {"attachment": {"type": "hook_additional_context",
                             "content": ["<knowledge-recall>\n(insight, 1x, L-deadbe, Sitzung x)"]},
             "timestamp": "2026-08-15T10:06:00.000Z"},
        ]
        with open(transkript, "w", encoding="utf-8") as f:
            for z in zeilen:
                f.write(json.dumps(z, ensure_ascii=False) + "\n")

        einsp = einspielungen_aus_transkript(transkript)
        assert {e["kennung"] for e in einsp} == {"L-c9f9e9", "L-deadbe"}, einsp

        art = {"L-c9f9e9": "lehre", "L-deadbe": "lehre"}
        grenze = {"L-c9f9e9": 1, "L-deadbe": 4}
        gefunden = verwendungen_aus_transkript(transkript, art, grenze)
        assert "L-c9f9e9" in gefunden, gefunden
        assert gefunden["L-c9f9e9"]["seq"] == 3, gefunden
        # reiner Fliesstext (Zeile 2, vor dem Agent-Aufruf) darf NICHT zaehlen --
        # waere er beruecksichtigt, faende sich schon bei seq2 ein 'Treffer'.
        assert "L-deadbe" not in gefunden, gefunden

        # D) Voller Lauf inkl. Verlaufsschreibung.
        verlauf_pfad = Path(td) / "verlauf.json"
        bericht = lauf(transkript, _w, JETZT, verlauf_pfad=verlauf_pfad)
        assert bericht["kennungen_gesamt"] == 2, bericht
        assert bericht["einspielungen_roh"] == 2, bericht
        assert bericht["anzahl_benutzt"] == 1, bericht
        assert bericht["quote_normiert_prozent"] == 50.0, bericht
        assert bericht["top3_anteil_prozent"] == 100.0, bericht

        gespeichert = verlauf_lesen(verlauf_pfad)
        assert gespeichert["L-c9f9e9"]["ereignisse"][-1]["ereignis"] == "benutzt", gespeichert
        assert gespeichert["L-deadbe"]["ereignisse"][-1]["ereignis"] == "unbeachtet", gespeichert

        # E) SPAETWIRKUNG: eine zweite, spaetere Einspielung derselben Kennung
        #    (L-deadbe) wird diesmal benutzt -- DERSELBE Eintrag muss
        #    ergaenzt werden, nicht ein zweiter angelegt (Kern des Auftrags).
        transkript2 = Path(td) / "sitzung2.jsonl"
        zeilen2 = [
            {"attachment": {"type": "hook_additional_context",
                             "content": ["<knowledge-recall>\n(insight, 1x, L-deadbe, Sitzung y)"]},
             "timestamp": "2026-08-16T09:00:00.000Z"},
            {"message": {"content": [{"type": "tool_use", "name": "Agent",
                                       "input": {"prompt": "wende L-deadbe an"}}]},
             "timestamp": "2026-08-16T09:05:00.000Z"},
        ]
        with open(transkript2, "w", encoding="utf-8") as f:
            for z in zeilen2:
                f.write(json.dumps(z, ensure_ascii=False) + "\n")
        bericht2 = lauf(transkript2, _w, "2026-08-16T09:10:00Z", verlauf_pfad=verlauf_pfad)
        assert bericht2["anzahl_benutzt"] == 1, bericht2

        gespeichert2 = verlauf_lesen(verlauf_pfad)
        eintrag = gespeichert2["L-deadbe"]
        arten = [e["ereignis"] for e in eintrag["ereignisse"]]
        assert arten == ["eingespielt", "unbeachtet", "eingespielt", "benutzt"], arten
        # KEIN zweiter Eintrag fuer dieselbe Kennung -- ein Objekt bleibt eins.
        assert list(gespeichert2.keys()).count("L-deadbe") == 1

    print("SELFTEST OK: Kennungenerkennung, Wortgrenzen (echtes Fundstueck), "
          "Verwendungserkennung, Verlaufsergaenzung inkl. Spaetwirkung.")


if __name__ == "__main__":
    raise SystemExit(_cli())
