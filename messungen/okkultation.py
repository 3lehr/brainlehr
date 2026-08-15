#!/usr/bin/env python3
"""Okkultation -- misst der Speicher ueberhaupt etwas, oder redet er nur mit.

Auftrag: docs/PLAN_OKKULTATION_2026-08-12.md (VOLLSTAENDIG dort). Dieses
Modul ist AUFTRAG D aus docs/PLAN_PARALLEL_2026-08-13.md: nur neue Dateien
unter messungen/ und runs/, haken/ bleibt unangetastet. Das Abschalten der
Einspielung geschieht HIER, indem query() direkt mit und ohne den daraus
gebauten Block aufgerufen wird -- kein Eingriff am Haken.

DER SELBSTBEZUG DES VORLAEUFERS (2026-08-07, Knoten 34ef6d8e), und wie er
hier ausgeschlossen wird: Der MIT-Block enthielt damals die Loesung im
Wortlaut (per lesson_query MIT Kenntnis der richtigen Lehre in den Suchtext
geschrieben) -- gemessen wurde also "hilft es, dem Modell die Antwort in
den Prompt zu schreiben", nicht ob der Speicher selbst etwas beitraegt.
Zwei Gegenmassnahmen:
  1. Der MIT-Block entsteht ausschliesslich ueber den echten Abrufweg
     (knowledge_recall_hook.keywords()+query() auf dem unveraenderten
     Aufgabentext) -- keine Handauswahl, keine Kenntnis des Ziels beim Abruf.
  2. Aus dem M1-Pool (siehe unten) sind Faelle der Klasse 'kennung' bewusst
     AUSGESCHLOSSEN: dort steht die Ziel-Kennung woertlich im Aufgabentext
     (z.B. 'L-abc123' oder '/pfad/knoten'), ein Modell koennte sie einfach
     abschreiben -- MIT und OHNE waeren dann ununterscheidbar aus einem
     Grund, der mit dem Speicher nichts zu tun hat. Es bleiben die Klassen
     'pfad' und 'lese': die Ziel-Kennung wird dort NIE im Text genannt,
     nur ueber code_kanten (Datei->Wissen) bzw. ein Lese-Ereignis abgeleitet.

DREI FALLMENGEN/BEDINGUNGEN je Fall:
  MIT   echter Abruf (keywords+query auf brainlehr.db), als
        <knowledge-recall>-Block angehaengt -- Format 1:1 wie der echte Haken.
  OHNE  derselbe Prompt, kein Block.
  NEG   derselbe Prompt + ein Block aus /nasa-llis/* (1641 absichtlich
        fremde Knoten, siehe Modulkopf messlauf_abrufguete_v2 bzw. Knoten
        /brainlehr/fremder-pruefkorpus-gefunden-1637-nasa) -- laengenangepasst
        an den echten MIT-Block desselben Falls. Negativkontrolle: ist NEG
        so gut wie MIT, misst der Versuch die LAENGE, nicht den Inhalt.

M1 (Zielaufgaben, Erfolg mechanisch): aus dem bestehenden, von messungen/
echtkorpus.py gesammelten Bestand runs/echtkorpus_2026-08-12T1000.json
(89 Faelle, NUR GELESEN, keine Aenderung an echtkorpus.py). 'Ziel im
Ergebnis' operationalisiert als: nennt/nutzt die Antwort den Zielknoten
oder die Ziel-Lehre erkennbar (Pfad, Kennung oder unterscheidungskraeftiges
Titelwort), wenn sie die Aufgabe angeht? Aufgabe fuer den Hauptfaden (siehe
--auswerten): 'Was ist dein erster Handgriff, und worauf stuetzt du ihn? Nenne
das gestuetzte Wissen (Pfad/Kennung), falls vorhanden.' -- eine kurze
Antwort, kein voller Aufgabendurchlauf (der ist bei mehrseitigen
Orchestrator-Prompts nicht in vertretbarer Zeit reproduzierbar).

M2 (Fragen ohne Ziel, kein Erfolgsurteil): echte 'frage'-Nachrichten aus
Sitzungstranskripten (messungen/echtkorpus.sitzungs_nachrichten(), nur
gelesen), bei denen WEDER ein Pfad- noch ein Kennungs-Ziel aufloest -- also
wirklich ziellos im Sinne des Sammlers. Bewertet wird, ob sich die Antwort
MIT vs. OHNE inhaltlich unterscheidet UND ob sich NEG vs. OHNE unterscheidet
(Negativkontrolle wie bei M1, s.u. -- ohne sie ist nicht unterscheidbar, ob
ein Unterschied vom INHALT des Blocks kommt oder nur davon, dass ueberhaupt
einer anhaengt). Beides Textvergleich, kein Erfolgsurteil.

DREITEILUNG wie kern/wissensnutzen_blind.py (nur gelesen, nicht importiert
-- eigene Kopie des Musters, weil kern/ fuer diese Sitzung tabu ist):
  1. --aufgaben   Abruf + Promptbau, KEIN Modellaufruf (dieses Skript)
  2. Hauptfaden   die Zellen tatsaechlich beantworten (Agent-Aufrufe, blind
                  je Bedingung, aus dem Orchestrator dieser Sitzung -- ein
                  Python-Skript kann keinen Subagenten starten, L-a69129)
  3. --auswerten  Antworten gegen Ziel pruefen (dieses Skript), KEIN
                  Modellaufruf

Aufruf:
    python3 okkultation.py --aufgaben runs/okkultation_aufgaben_<datum>.json
    python3 okkultation.py --auswerten AUFGABEN ANTWORTEN --out runs/okkultation_<datum>.json
    python3 okkultation.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Repo-Wurzel an schema.sql festmachen (Muster aus messungen/echtkorpus.py
# und kern/wissensnutzen_blind.py) -- eine feste Ebenenzahl bricht beim
# naechsten Umzug lautlos.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import argparse
import hashlib
import json
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

import codekanten as ck  # noqa: E402 -- nur gelesen (kandidaten/wissen_zu)
import echtkorpus as ek  # noqa: E402 -- nur gelesen (satzart/_ist_echte_frage/sitzungs_nachrichten)
import ort  # noqa: E402
import speicher  # noqa: E402
import zeitmarke  # noqa: E402
import knowledge_recall_hook as rh  # noqa: E402 -- der echte Abrufweg, unveraendert benutzt

WURZEL = _w
DB = str(ort.DB)
M1_QUELLE = WURZEL / "runs" / "echtkorpus_2026-08-12T1000.json"
OUT_DEFAULT = WURZEL / "runs" / "okkultation_aufgaben.json"

# Klassen, die den Selbstbezug ausschliessen (s. Modulkopf).
M1_ERLAUBTE_KLASSEN = ("pfad", "lese")

_WERKZEUG_HINWEIS = (
    " Benutze dabei KEIN Suchwerkzeug (kein knowledge_search, kein read, "
    "kein grep im Repo) -- die Antwort soll ausschliesslich aus diesem "
    "Prompt schoepfen. Halte in deiner Antwortzelle das Pflichtfeld "
    "'werkzeuge_benutzt' fest (true/false): ob du waehrenddessen doch ein "
    "Werkzeug benutzt hast. Fehlt das Feld oder ist es true, faellt die "
    "Zelle aus der Auswertung.")

M1_TASK_ANWEISUNG = (
    "\n\n---\nAufgabe an dich: Was ist dein ERSTER Handgriff auf diese "
    "Nachricht, in maximal 4 Saetzen? Nenne dabei, falls vorhanden, den "
    "genauen Pfad oder die genaue Kennung des Wissens, auf das du dich "
    "stuetzt. Kein voller Aufgabendurchlauf, nur der erste Schritt und "
    "seine Begruendung." + _WERKZEUG_HINWEIS)
M2_TASK_ANWEISUNG = (
    "\n\n---\nAufgabe an dich: Beantworte diese Frage in maximal 6 Saetzen, "
    "so wie du es in einer echten Sitzung taetest." + _WERKZEUG_HINWEIS)

# WERKZEUG -- vierte Bedingung, nur fuer M1 (Betreiberidee 2026-08-15): wie
# OHNE, aber Suchwerkzeuge sind ausdruecklich ERLAUBT. Miss nicht "hilft der
# Speicher", sondern "ist das Ziel ohne Einspielung ERREICHBAR" -- die
# Dreiteilung aus dreiteilung_erreichbarkeit() unten braucht dafuer eine
# eigene Zelle je Fall, keine Wiederverwendung von OHNE (die verbietet
# Werkzeuge ausdruecklich, die Frage hier ist eine andere).
M1_WERKZEUG_ANWEISUNG = (
    "\n\n---\nAufgabe an dich: Was ist dein ERSTER Handgriff auf diese "
    "Nachricht, in maximal 4 Saetzen? Nenne dabei, falls vorhanden, den "
    "genauen Pfad oder die genaue Kennung des Wissens, auf das du dich "
    "stuetzt. Kein voller Aufgabendurchlauf, nur der erste Schritt und "
    "seine Begruendung. ANDERS ALS SONST darfst du hier Suchwerkzeuge "
    "benutzen (knowledge_search, read, grep im Repo, git log) -- das ist "
    "ausdruecklich Teil dieser Bedingung: gemessen wird, ob du das Wissen "
    "SELBST findest, ohne dass es dir vorgelegt wurde. Halte in deiner "
    "Antwortzelle das Pflichtfeld 'werkzeuge_benutzt' fest (true/false) "
    "und, falls true, zusaetzlich 'werkzeug_pfad' (welches Werkzeug, "
    "welcher Fund).")


# --------------------------------------------------------------------- Block
def format_block(nodes: list, lessons: list) -> str:
    """1:1 dasselbe Ausgabeformat wie knowledge_recall_hook.main() baut (die
    Frageform-Rahmung ausgenommen -- die ist Anrede, kein Inhalt), damit ein
    Hauptfaden genau das sieht, was eine echte Sitzung ihm zeigen wuerde."""
    lines = ["<knowledge-recall>",
             "Aus dem Speicher, ungeprueft. Trifft das hier zu?"]
    for n in nodes:
        fremd = f" [anderes Projekt: {n['foreign_project']}]" if n.get("foreign_project") else ""
        lines.append(f"- [{n['path']}]{rh.alter(n.get('updated_at'))}{fremd} "
                     f"{rh.entschaerfe_fuer_ausgabe(n['title'])}: "
                     f"{rh.entschaerfe_fuer_ausgabe(n['summary'])}")
    for l in lessons:
        tag = "LESSON" if l["severity"] in ("critical", "high") else "Lesson"
        prev = f" -> {rh.entschaerfe_fuer_ausgabe(l['prevention'])}" if l.get("prevention") else ""
        lines.append(f"- {tag} ({l['type']}, {l['occurrences']}x, {l['id']}): "
                     f"{rh.entschaerfe_fuer_ausgabe(l['description'])}{prev}")
    lines.append("</knowledge-recall>")
    return "\n".join(lines)


def retrieve(prompt: str, cwd: str | None = None) -> tuple[list, list]:
    """Der echte Abrufweg, direkt aufgerufen -- KEIN log_recall() (das
    schriebe in die Betriebsdatenbank und wuerde die echten Kennzahlen
    anderer Sitzungen verunreinigen; query() selbst schreibt nichts)."""
    kws = rh.keywords(prompt)
    if len(kws) < rh.MIN_HITS:
        return [], []
    return rh.query(kws, cwd=cwd)


def foreign_block(ziel_laenge: int, conn: sqlite3.Connection, seed: int) -> str:
    """Negativkontrolle: laengenangepasster Block aus /nasa-llis/* -- real,
    aus der DB, aber thematisch fremd zu jeder brainlehr-Aufgabe (1641
    absichtlich fremde Knoten, s. Modulkopf). Deterministisch ueber seed
    (kein random.random(), damit ein Lauf reproduzierbar bleibt)."""
    rows = conn.execute(
        "SELECT path, title, summary, updated_at FROM knowledge_nodes "
        "WHERE path LIKE '/nasa-llis/%' AND zurueckgezogen = 0 "
        "ORDER BY id LIMIT 200").fetchall()
    if not rows:
        return "<knowledge-recall>\n(keine Fremdknoten verfuegbar)\n</knowledge-recall>"
    start = seed % len(rows)
    gewaehlt = []
    text = ""
    i = start
    # so lange Knoten anhaengen, bis die Ziellaenge erreicht oder der Pool
    # erschoepft ist -- Laenge ist das Kriterium, nicht eine feste Anzahl.
    for _ in range(len(rows)):
        n = dict(rows[i % len(rows)])
        gewaehlt.append(n)
        text = format_block(gewaehlt, [])
        i += 1
        if len(text) >= ziel_laenge:
            break
    if len(text) > ziel_laenge:
        # Auf Zeilengrenze kappen, damit kein Knoten mitten im Satz endet --
        # sonst waere die Kappung selbst schon ein Signal (unvollstaendiger
        # Eintrag sieht anders aus als ein echter).
        zeilen = text.split("\n")
        acc, laenge = [], 0
        for z in zeilen:
            if laenge + len(z) + 1 > ziel_laenge and acc[-1:] != ["</knowledge-recall>"]:
                break
            acc.append(z)
            laenge += len(z) + 1
        if acc[-1] != "</knowledge-recall>":
            acc.append("</knowledge-recall>")
        text = "\n".join(acc)
    return text


# ----------------------------------------------------------------------- M1
def m1_pool() -> list[dict]:
    daten = json.loads(M1_QUELLE.read_text(encoding="utf-8"))
    return [f for f in daten["faelle"] if f["klasse"] in M1_ERLAUBTE_KLASSEN]


def m1_sample(n: int, seed: int = 0) -> list[dict]:
    """Deterministische, ueber satzart geschichtete Auswahl (stabile
    Reihenfolge nach Hash statt random.shuffle -- reproduzierbar ohne
    Zustand)."""
    pool = m1_pool()
    pool.sort(key=lambda f: hashlib.sha256(
        (str(seed) + f["prompt"]).encode("utf-8")).hexdigest())
    fragen = [f for f in pool if f["satzart"] == "frage"]
    auftraege = [f for f in pool if f["satzart"] == "auftrag"]
    # Anteil an fragen im Pool beibehalten, mindestens 1 falls vorhanden.
    n_frage = max(1, round(n * len(fragen) / max(1, len(pool)))) if fragen else 0
    n_frage = min(n_frage, len(fragen), n)
    n_auftrag = min(n - n_frage, len(auftraege))
    return (fragen[:n_frage] + auftraege[:n_auftrag])[:n]


# ----------------------------------------------------------------------- M2
def _hat_aufloesbares_ziel(text: str, conn: sqlite3.Connection, index: dict) -> bool:
    pfade = sorted(k for k in ck.kandidaten(text) if "/" in k)
    for k in pfade:
        for w in ck.wissen_zu(k, conn):
            if not w["mehrdeutig"]:
                return True
    for k in sorted(ek.kennungen(text)):
        if ek.kennung_pruefen(k, conn):
            return True
    return False


def m2_pool(conn: sqlite3.Connection, max_laenge: int = 600) -> list[str]:
    """Echte Fragen ohne aufloesbares Ziel -- ziellos im Sinne von
    echtkorpus.py, nicht erfunden. max_laenge begrenzt auf handhabbare
    Fragen (keine mehrseitigen Auftraege, die satzart() ohnehin als
    'auftrag' einstufen wuerde -- Deckel nur gegen Ausreisser)."""
    nachrichten = ek._ohne_doppelte(ek.sitzungs_nachrichten())
    m1_prompts = {f["prompt"] for f in json.loads(
        M1_QUELLE.read_text(encoding="utf-8"))["faelle"]}
    raus = []
    for text in nachrichten:
        if text in m1_prompts or len(text) > max_laenge:
            continue
        if ek.satzart(text) != "frage":
            continue
        if _hat_aufloesbares_ziel(text, conn, None):
            continue
        raus.append(text)
    return raus


def m2_sample(n: int, conn: sqlite3.Connection, seed: int = 0) -> list[str]:
    pool = m2_pool(conn)
    pool.sort(key=lambda t: hashlib.sha256((str(seed) + t).encode("utf-8")).hexdigest())
    return pool[:n]


# --------------------------------------------------------------- aufgaben()
def aufgaben_erzeugen(m1_n: int, m2_n: int, seed: int = 0, cwd: str | None = None,
                       m1_werkzeug: bool = False) -> dict:
    """Schritt 1 der Dreiteilung: Abruf + Promptbau, KEIN Modellaufruf.
    Gibt die vollstaendige Arbeitsliste fuer den Hauptfaden zurueck.

    m1_werkzeug: zusaetzliche WERKZEUG-Zelle je M1-Fall bauen (s.
    M1_WERKZEUG_ANWEISUNG). Vorgabe False, damit bestehende Aufrufe
    (CLI-Default, alte Aufgabendateien) unveraendert bleiben -- die
    Dreiteilung ist eine Erweiterung, kein Ersatz."""
    cwd = cwd or str(WURZEL)
    zellen: list[dict] = []
    einspielungen: Counter = Counter()  # fuer die Schiefe-Gegenprobe
    with speicher.lesen(DB) as conn:
        m1 = m1_sample(m1_n, seed)
        m2 = m2_sample(m2_n, conn, seed)

        for i, fall in enumerate(m1):
            nodes, lessons = retrieve(fall["prompt"], cwd=cwd)
            for n in nodes:
                einspielungen[n["path"]] += 1
            for l in lessons:
                einspielungen[l["id"]] += 1
            block_mit = format_block(nodes, lessons) if (nodes or lessons) else None
            case_id = f"m1-{i:02d}"
            basis = fall["prompt"] + M1_TASK_ANWEISUNG
            varianten = {"OHNE": basis}
            if block_mit:
                varianten["MIT"] = f"{fall['prompt']}\n\n{block_mit}{M1_TASK_ANWEISUNG}"
                varianten["NEG"] = (f"{fall['prompt']}\n\n"
                                     f"{foreign_block(len(block_mit), conn, seed + i)}"
                                     f"{M1_TASK_ANWEISUNG}")
            if m1_werkzeug:
                # Keine Wiederverwendung von 'basis' -- die enthaelt die
                # Werkzeug-Verbots-Anweisung woertlich, die hier falsch waere.
                varianten["WERKZEUG"] = fall["prompt"] + M1_WERKZEUG_ANWEISUNG
            for cond, prompt in varianten.items():
                zellen.append({
                    "key": f"{case_id}|{cond}", "gruppe": "M1", "case_id": case_id,
                    "condition": cond, "prompt": prompt,
                    "ziele": fall["ziele"], "klasse": fall["klasse"], "satzart": fall["satzart"],
                    "abruf_leer": not (nodes or lessons),
                })

        for i, text in enumerate(m2):
            nodes, lessons = retrieve(text, cwd=cwd)
            for n in nodes:
                einspielungen[n["path"]] += 1
            for l in lessons:
                einspielungen[l["id"]] += 1
            block_mit = format_block(nodes, lessons) if (nodes or lessons) else None
            case_id = f"m2-{i:02d}"
            varianten = {"OHNE": text + M2_TASK_ANWEISUNG}
            if block_mit:
                varianten["MIT"] = f"{text}\n\n{block_mit}{M2_TASK_ANWEISUNG}"
                varianten["NEG"] = (f"{text}\n\n"
                                     f"{foreign_block(len(block_mit), conn, seed + i + 1000)}"
                                     f"{M2_TASK_ANWEISUNG}")
            for cond, prompt in varianten.items():
                zellen.append({
                    "key": f"{case_id}|{cond}", "gruppe": "M2", "case_id": case_id,
                    "condition": cond, "prompt": prompt, "ziele": None,
                    "abruf_leer": not (nodes or lessons),
                })

    gesamt = sum(einspielungen.values())
    drei_haeufigste = sum(c for _, c in einspielungen.most_common(3))
    schiefe = (drei_haeufigste / gesamt) if gesamt else None

    return {
        "erzeugt_am": zeitmarke.jetzt(),
        "m1_angefragt": m1_n, "m1_geliefert": len(m1),
        "m2_angefragt": m2_n, "m2_geliefert": len(m2),
        "m1_pool_groesse": len(m1_pool()),
        "zellen": zellen,
        "schiefe_gegenprobe": {
            "einspielungen_gesamt": gesamt,
            "drei_haeufigste_anteil": schiefe,
            "drei_haeufigste": einspielungen.most_common(3),
            "hinweis": "> 0.5 heisst: die Kennzahl beschreibt die Suche, nicht den Nutzen",
        },
    }


# -------------------------------------------------------------- auswerten()
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß0-9_/.\-]{4,}")


def _ziel_treffer(antwort: str, ziele: list[dict]) -> bool:
    """Mechanische Pruefung fuer M1: nennt die Antwort den Zielpfad/die
    Zielkennung (voll oder als Pfad-Endstueck, z.B. nur den Dateinamen
    bzw. den letzten Pfadabschnitt eines Knotens)?

    Das Endstueck-Fallback gilt NICHT fuer Projektwurzeln wie '/brainlehr'
    (genau ein '/'): deren 'letztes Stueck' ist der Projektname selbst, und
    der taucht in praktisch jeder Antwort ueber dieses Projekt auf -- das
    waere kein Beleg fuer Wissensnutzung, sondern ein Fehlalarm. Gemessen
    2026-08-13: /brainlehr traf im NEG-Lauf ueber das blosse Wort
    'brainlehr-interne Messaufgabe', ohne dass der Zielknoten gemeint war.
    Erst ab zwei '/' (also einer echten Unterseite) ist das Endstueck
    unterscheidungskraeftig genug."""
    text = antwort or ""
    for z in ziele:
        zid = z["id"]
        if zid in text:
            return True
        if zid.startswith("/") and zid.count("/") == 1:
            continue  # Projektwurzel wie '/brainlehr', s. Docstring
        letztes_stueck = zid.rsplit("/", 1)[-1]
        if len(letztes_stueck) >= 4 and letztes_stueck in text:
            return True
    return False


def _antwort_lesen(eintrag) -> tuple[str | None, bool]:
    """Liest eine Antwortzelle. Pflichtfeld 'werkzeuge_benutzt' (Teil 2 des
    Auftrags): fehlt es, oder meldet es True, ist die Zelle fuer die Quoten
    GESPERRT -- sonst koennte die OHNE-Bedingung heimlich ueber ein
    Suchwerkzeug doch an den Speicher gekommen sein, und die Messung waere
    wertlos. Altformat (nackter String ohne Feld) hat das Pflichtfeld nie
    -> ebenfalls ausgeschlossen, nicht stillschweigend als 'kein Werkzeug'
    gelesen (fail-closed statt fail-open)."""
    if isinstance(eintrag, dict):
        antwort = eintrag.get("antwort")
        if "werkzeuge_benutzt" not in eintrag or eintrag["werkzeuge_benutzt"]:
            return antwort, True
        return antwort, False
    return eintrag, True  # String ohne Feld -> ausgeschlossen


def leck_pruefung(text: str, ziele: list[dict]) -> tuple[bool, list[str]]:
    """Auftrag Risiko 1 (Leck): nachpruefbarer Guard, kein Ermahnungssatz.
    Prueft, ob ein Text (z.B. ein von einem informierten Agenten formulierter
    Kriterientext fuer den Richter, siehe okkultation_richter.py) eine
    Ziel-Kennung woertlich enthaelt -- dieselbe Logik wie _ziel_treffer,
    hier VOR dem Einsatz als Schranke statt hinterher als Erfolgsmass.
    Rueckgabe: (leck_gefunden, betroffene_ziel_ids)."""
    treffer = [z["id"] for z in (ziele or []) if _ziel_treffer(text, [z])]
    return (bool(treffer), treffer)


def dreiteilung_erreichbarkeit(aufgaben: dict, antworten: dict) -> dict:
    """Auftragserweiterung (Betreiberidee 2026-08-15): braucht die vierte
    Zelle WERKZEUG je M1-Fall (aufgaben_erzeugen(..., m1_werkzeug=True)).
    Klassifiziert jeden Fall mechanisch in genau eine von drei Klassen --
    die Dreiteilung, die laut Auftrag allen bisherigen Zahlen des Hauses
    fehlt -- plus 'unbestimmt' fuer Faelle ohne verwertbare Datenlage:
      gefunden_mit_einspielung  MIT trifft das Ziel
      selbst_gefunden           MIT trifft NICHT, aber WERKZEUG trifft
      gar_nicht_gefunden        weder MIT noch WERKZEUG trifft
      unbestimmt                Zelle/Antwort fehlt, oder WERKZEUG-Zelle
                                 ohne das Pflichtfeld 'werkzeuge_benutzt'
    KEIN Modellaufruf, reine Nachauswertung wie auswerten()."""
    faelle: dict[str, dict] = {}
    for zelle in aufgaben["zellen"]:
        if zelle["gruppe"] != "M1":
            continue
        faelle.setdefault(zelle["case_id"], {"ziele": zelle["ziele"], "bedingungen": {}})
        faelle[zelle["case_id"]]["bedingungen"][zelle["condition"]] = zelle

    gegeben = antworten.get("antworten", {})
    klassen: Counter = Counter()
    einzelheiten = []
    for case_id, fall in faelle.items():
        mit_zelle = fall["bedingungen"].get("MIT")
        werkzeug_zelle = fall["bedingungen"].get("WERKZEUG")
        if mit_zelle is None or werkzeug_zelle is None:
            klassen["unbestimmt"] += 1
            einzelheiten.append({"case_id": case_id, "klasse": "unbestimmt",
                                  "grund": "MIT- oder WERKZEUG-Zelle fehlt im Aufgabensatz"})
            continue
        mit_eintrag = gegeben.get(mit_zelle["key"])
        werkzeug_eintrag = gegeben.get(werkzeug_zelle["key"])
        if mit_eintrag is None or werkzeug_eintrag is None:
            klassen["unbestimmt"] += 1
            einzelheiten.append({"case_id": case_id, "klasse": "unbestimmt",
                                  "grund": "Antwort fehlt"})
            continue
        mit_antwort, mit_ausg = _antwort_lesen(mit_eintrag)
        # WERKZEUG erwartet ausdruecklich eine Angabe zur Werkzeugnutzung --
        # anders als bei OHNE ist True hier KEIN Ausschlussgrund (Werkzeuge
        # sind erlaubt), das FEHLEN des Feldes aber schon (fail-closed: ohne
        # das Feld ist unbekannt, ob und wie das Ziel gefunden wurde).
        if isinstance(werkzeug_eintrag, dict) and "werkzeuge_benutzt" in werkzeug_eintrag:
            werkzeug_antwort, werkzeug_ausg = werkzeug_eintrag.get("antwort"), False
        else:
            werkzeug_antwort, werkzeug_ausg = None, True
        if mit_ausg or werkzeug_ausg:
            klassen["unbestimmt"] += 1
            einzelheiten.append({"case_id": case_id, "klasse": "unbestimmt",
                                  "grund": "Pflichtfeld 'werkzeuge_benutzt' fehlt/verletzt"})
            continue
        mit_treffer = _ziel_treffer(mit_antwort, fall["ziele"])
        werkzeug_treffer = _ziel_treffer(werkzeug_antwort, fall["ziele"])
        klasse = ("gefunden_mit_einspielung" if mit_treffer else
                   "selbst_gefunden" if werkzeug_treffer else "gar_nicht_gefunden")
        klassen[klasse] += 1
        einzelheiten.append({"case_id": case_id, "klasse": klasse,
                              "mit_treffer": mit_treffer, "werkzeug_treffer": werkzeug_treffer})

    gesamt = (klassen["gefunden_mit_einspielung"] + klassen["selbst_gefunden"]
              + klassen["gar_nicht_gefunden"])  # unbestimmt zaehlt NICHT mit
    return {
        "gesamt": gesamt,
        "gefunden_mit_einspielung": klassen["gefunden_mit_einspielung"],
        "selbst_gefunden": klassen["selbst_gefunden"],
        "gar_nicht_gefunden": klassen["gar_nicht_gefunden"],
        "unbestimmt": klassen["unbestimmt"],
        "einzelheiten": einzelheiten,
        "hinweis": "misst, ob das Ziel OHNE Einspielung ueber Werkzeuge "
                   "erreichbar war -- trennt 'der Speicher lieferte es' von "
                   "'der Agent haette es auch so gefunden'.",
    }


def _quote(treffer: int, n: int) -> dict:
    return {
        "treffer": treffer, "n": n,
        "anteil": (treffer / n) if n else None,
        "hinweis": None if n else "keine verwertbaren Zellen",
    }


def auswerten(aufgaben: dict, antworten: dict) -> dict:
    """Schritt 3: Antworten des Hauptfadens gegen die Ziele pruefen (M1) bzw.
    nur auf Unterschied hin vergleichen (M2). KEIN Modellaufruf.

    Zellen, deren Pflichtfeld 'werkzeuge_benutzt' fehlt oder True meldet,
    gehen NICHT in die Quoten ein (s. _antwort_lesen) -- sie werden separat
    als ausgeschlossen gezaehlt."""
    gegeben = antworten.get("antworten", {})
    m1_conditions: dict[str, list[bool]] = {}
    m1_faelle_ausgewertet = 0
    m1_fehlbestand = []
    m1_werkzeug_ausgeschlossen = []
    m2_ergebnisse = []
    m2_fehlbestand = []
    m2_werkzeug_ausgeschlossen = []

    # M1: je Fall alle vorhandenen Bedingungen einsammeln.
    faelle_m1: dict[str, dict] = {}
    for zelle in aufgaben["zellen"]:
        if zelle["gruppe"] != "M1":
            continue
        faelle_m1.setdefault(zelle["case_id"], {"ziele": zelle["ziele"], "bedingungen": {}})
        faelle_m1[zelle["case_id"]]["bedingungen"][zelle["condition"]] = zelle

    # Liefer-Analyse (zusaetzlich zur reinen Trefferquote): unter den
    # Faellen, wo der MIT-Block das Ziel tatsaechlich ENTHIELT (Retrieval-
    # Treffer), wie oft taucht das Ziel dann auch in der MIT-Antwort auf?
    # Trennt 'findet das Falsche' (Retrieval-Fehlgriff) von 'wird nicht
    # benutzt' (geliefert, aber in der Antwort ignoriert) -- genau die
    # Unterscheidung, um die es in diesem Versuch laut Auftrag geht.
    geliefert_und_benutzt = 0
    geliefert_gesamt = 0

    for case_id, fall in faelle_m1.items():
        m1_faelle_ausgewertet += 1
        mit_zelle = fall["bedingungen"].get("MIT")
        block_enthaelt_ziel = (
            mit_zelle is not None and
            any(z["id"] in mit_zelle.get("prompt", "") for z in fall["ziele"]))
        for cond, zelle in fall["bedingungen"].items():
            eintrag = gegeben.get(zelle["key"])
            if eintrag is None:
                m1_fehlbestand.append(zelle["key"])
                continue
            antwort, ausgeschlossen = _antwort_lesen(eintrag)
            if ausgeschlossen:
                m1_werkzeug_ausgeschlossen.append(zelle["key"])
                continue
            treffer = _ziel_treffer(antwort, fall["ziele"])
            m1_conditions.setdefault(cond, []).append(treffer)
            if cond == "MIT" and block_enthaelt_ziel:
                geliefert_gesamt += 1
                if treffer:
                    geliefert_und_benutzt += 1

    # M2: MIT vs OHNE, nur Unterschied feststellen -- kein Erfolgsurteil.
    faelle_m2: dict[str, dict] = {}
    for zelle in aufgaben["zellen"]:
        if zelle["gruppe"] != "M2":
            continue
        faelle_m2.setdefault(zelle["case_id"], {})[zelle["condition"]] = zelle

    for case_id, bedingungen in faelle_m2.items():
        mit = bedingungen.get("MIT")
        neg = bedingungen.get("NEG")
        ohne = bedingungen.get("OHNE")

        eintrag_ohne = gegeben.get(ohne["key"]) if ohne else None
        eintrag_mit = gegeben.get(mit["key"]) if mit else None
        eintrag_neg = gegeben.get(neg["key"]) if neg else None
        if eintrag_ohne is None or (mit and eintrag_mit is None) or (neg and eintrag_neg is None):
            m2_fehlbestand.append(case_id)
            continue

        a_ohne, ausg_ohne = _antwort_lesen(eintrag_ohne)
        a_mit, ausg_mit = (_antwort_lesen(eintrag_mit) if mit else (None, False))
        a_neg, ausg_neg = (_antwort_lesen(eintrag_neg) if neg else (None, False))
        if ausg_ohne:
            m2_werkzeug_ausgeschlossen.append(ohne["key"])
        if mit and ausg_mit:
            m2_werkzeug_ausgeschlossen.append(mit["key"])
        if neg and ausg_neg:
            m2_werkzeug_ausgeschlossen.append(neg["key"])

        # vergleichbar nur, wenn WEDER die OHNE- noch die Gegenzelle wegen
        # Werkzeugnutzung gesperrt ist -- eine gesperrte Zelle darf keine
        # Quote mehr fuellen (Auftrag Teil 2).
        mit_vergleichbar = (mit is not None) and not ausg_ohne and not ausg_mit
        neg_vergleichbar = (neg is not None) and not ausg_ohne and not ausg_neg

        unterschiedlich = mit_vergleichbar and _wesentlich_unterschiedlich(a_mit, a_ohne)
        unterschiedlich_neg = neg_vergleichbar and _wesentlich_unterschiedlich(a_neg, a_ohne)
        m2_ergebnisse.append({
            "case_id": case_id, "hat_mit_bedingung": mit is not None,
            "hat_neg_bedingung": neg is not None,
            "mit_vergleichbar": mit_vergleichbar, "neg_vergleichbar": neg_vergleichbar,
            "unterschiedlich": unterschiedlich, "unterschiedlich_neg": unterschiedlich_neg,
            "antwort_ohne": a_ohne, "antwort_mit": a_mit, "antwort_neg": a_neg,
        })

    m2_mit_vergleichbar = [e for e in m2_ergebnisse if e["mit_vergleichbar"]]
    unterschied_n = sum(1 for e in m2_mit_vergleichbar if e["unterschiedlich"])
    m2_neg_vergleichbar = [e for e in m2_ergebnisse if e["neg_vergleichbar"]]
    unterschied_neg_n = sum(1 for e in m2_neg_vergleichbar if e["unterschiedlich_neg"])

    def _m1_quote(cond: str) -> dict:
        werte = m1_conditions.get(cond, [])
        return _quote(sum(werte), len(werte))

    return {
        "ausgewertet_am": zeitmarke.jetzt(),
        "m1": {
            "faelle": m1_faelle_ausgewertet,
            "MIT": _m1_quote("MIT"), "OHNE": _m1_quote("OHNE"), "NEG": _m1_quote("NEG"),
            "fehlbestand": m1_fehlbestand,
            "werkzeug_ausgeschlossen": m1_werkzeug_ausgeschlossen,
            "liefer_analyse": {
                "geliefert_gesamt": geliefert_gesamt,
                "geliefert_und_benutzt": geliefert_und_benutzt,
                "anteil": (geliefert_und_benutzt / geliefert_gesamt) if geliefert_gesamt else None,
                "hinweis": "unter den Faellen, wo der MIT-Block das Ziel enthielt "
                           "(Retrieval-Treffer): wie oft taucht es dann auch in der "
                           "Antwort auf? Trennt Retrieval-Fehlgriff von Nichtnutzung.",
            },
        },
        "m2": {
            # unveraendert in der Bedeutung ggue. vor der NEG-Erweiterung:
            # MIT gegen OHNE, nur unter vergleichbaren (nicht werkzeug-
            # ausgeschlossenen) Zellen.
            "faelle_mit_mit_bedingung": len(m2_mit_vergleichbar),
            "unterschiedlich": unterschied_n,
            "unterschiedlich_anteil": (unterschied_n / len(m2_mit_vergleichbar)) if m2_mit_vergleichbar else None,
            # neu: NEG gegen OHNE -- Negativkontrolle. Ist dieser Anteil
            # aehnlich hoch wie der MIT-Anteil, unterscheidet die Antwort
            # nur "haengt ueberhaupt ein Block an", nicht dessen Inhalt.
            "faelle_mit_neg_bedingung": len(m2_neg_vergleichbar),
            "unterschiedlich_neg": unterschied_neg_n,
            "unterschiedlich_neg_anteil": (unterschied_neg_n / len(m2_neg_vergleichbar)) if m2_neg_vergleichbar else None,
            "werkzeug_ausgeschlossen": m2_werkzeug_ausgeschlossen,
            "ergebnisse": m2_ergebnisse,
            "fehlbestand": m2_fehlbestand,
            "hinweis": "Unterschied ist kein Nutzen -- kein Erfolgsurteil gefaellt.",
        },
        "schiefe_gegenprobe": aufgaben.get("schiefe_gegenprobe"),
    }


def _wesentlich_unterschiedlich(a: str, b: str) -> bool:
    """Grober, aber mechanischer Unterschieds-Test: normalisierte
    Wortmengen, Jaccard < 0.6 gilt als 'unterschiedlich'. Ersetzt keinen
    blinden menschlichen/Dritten-Vergleich (der gehoert in die Antwortdatei
    als eigenes Feld, hier nur die mechanische Voreinschaetzung)."""
    wa = set(w.lower() for w in _WORT.findall(a or ""))
    wb = set(w.lower() for w in _WORT.findall(b or ""))
    if not wa and not wb:
        return False
    if not wa or not wb:
        return True
    jacc = len(wa & wb) / len(wa | wb)
    return jacc < 0.6


# ---------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aufgaben", metavar="DATEI",
                     help="Schritt 1: Abruf + Promptbau schreiben, kein Modellaufruf")
    ap.add_argument("--m1-n", type=int, default=12)
    ap.add_argument("--m2-n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--m1-werkzeug", action="store_true",
                     help="vierte M1-Zelle WERKZEUG mitbauen (Dreiteilung Erreichbarkeit)")
    ap.add_argument("--auswerten", nargs=2, metavar=("AUFGABEN", "ANTWORTEN"),
                     help="Schritt 3: Antworten pruefen, kein Modellaufruf")
    ap.add_argument("--dreiteilung", nargs=2, metavar=("AUFGABEN", "ANTWORTEN"),
                     help="Dreiteilung Erreichbarkeit (braucht WERKZEUG-Zellen), kein Modellaufruf")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.aufgaben:
        daten = aufgaben_erzeugen(args.m1_n, args.m2_n, args.seed, args.cwd,
                                   m1_werkzeug=args.m1_werkzeug)
        ziel = Path(args.aufgaben)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"M1: {daten['m1_geliefert']}/{daten['m1_angefragt']} Faelle aus Pool "
              f"{daten['m1_pool_groesse']} -- M2: {daten['m2_geliefert']}/{daten['m2_angefragt']}")
        print(f"Zellen gesamt: {len(daten['zellen'])}")
        print(f"Schiefe (3 haeufigste / gesamt): {daten['schiefe_gegenprobe']['drei_haeufigste_anteil']}")
        print(f"Geschrieben: {ziel}")
        return

    if args.auswerten:
        aufg = json.loads(Path(args.auswerten[0]).read_text(encoding="utf-8"))
        antw = json.loads(Path(args.auswerten[1]).read_text(encoding="utf-8"))
        ergebnis = auswerten(aufg, antw)
        out = Path(args.out or (WURZEL / "runs" / "okkultation_ergebnis.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
        m1 = ergebnis["m1"]
        for cond in ("MIT", "OHNE", "NEG"):
            q = m1[cond]
            print(f"M1 {cond:5s} {q['treffer']}/{q['n']} "
                  f"({q['anteil']:.2f})" if q["anteil"] is not None else f"M1 {cond:5s} {q['hinweis']}")
        print(f"M1 werkzeug-ausgeschlossen: {len(m1['werkzeug_ausgeschlossen'])}")
        m2 = ergebnis["m2"]
        print(f"M2 unterschiedlich (MIT/OHNE): {m2['unterschiedlich']}/{m2['faelle_mit_mit_bedingung']}")
        print(f"M2 unterschiedlich (NEG/OHNE): {m2['unterschiedlich_neg']}/{m2['faelle_mit_neg_bedingung']}")
        print(f"M2 werkzeug-ausgeschlossen: {len(m2['werkzeug_ausgeschlossen'])}")
        print(f"Geschrieben: {out}")
        return

    if args.dreiteilung:
        aufg = json.loads(Path(args.dreiteilung[0]).read_text(encoding="utf-8"))
        antw = json.loads(Path(args.dreiteilung[1]).read_text(encoding="utf-8"))
        ergebnis = dreiteilung_erreichbarkeit(aufg, antw)
        out = Path(args.out or (WURZEL / "runs" / "okkultation_dreiteilung.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"gefunden_mit_einspielung: {ergebnis['gefunden_mit_einspielung']}/{ergebnis['gesamt']}")
        print(f"selbst_gefunden: {ergebnis['selbst_gefunden']}/{ergebnis['gesamt']}")
        print(f"gar_nicht_gefunden: {ergebnis['gar_nicht_gefunden']}/{ergebnis['gesamt']}")
        print(f"unbestimmt: {ergebnis['unbestimmt']}")
        print(f"Geschrieben: {out}")
        return

    ap.print_help()


# ------------------------------------------------------------------- Tests
def _selftest() -> None:
    """Rot-vor-gruen, ohne DB/Netz: Blockformat, Zieltreffer, Auswertung."""
    block = format_block(
        [{"path": "/a/b", "title": "T", "summary": "S", "updated_at": None}],
        [{"id": "L-aaaaaa", "severity": "low", "type": "insight", "occurrences": 1,
          "description": "D", "prevention": None}],
    )
    assert "<knowledge-recall>" in block and "/a/b" in block and "L-aaaaaa" in block

    # Zieltreffer: voller Pfad, nur das letzte Stueck, und ein Fehlschlag.
    assert _ziel_treffer("siehe /a/b/c fuer Details", [{"art": "knoten", "id": "/a/b/c"}])
    assert _ziel_treffer("Datei heisst existenzpruefung.py", [{"art": "knoten", "id": "haken/existenzpruefung.py"}])
    assert not _ziel_treffer("nichts Passendes hier", [{"art": "knoten", "id": "/x/y/z"}])
    # Grenzfall: ein zu kurzes Endstueck (<4 Zeichen) darf nicht faelschlich treffen.
    assert not _ziel_treffer("ab", [{"art": "knoten", "id": "/x/ab"}])
    # Regression 2026-08-13: eine Projektwurzel ('/brainlehr', ein '/') darf
    # nicht ueber ihr 'Endstueck' (der Projektname selbst) treffen -- der
    # taucht in fast jeder Antwort ueber das Projekt auf, ganz ohne dass der
    # Zielknoten gemeint war (echter Fehlalarm im NEG-Lauf).
    assert not _ziel_treffer(
        "Das ist eine brainlehr-interne Messaufgabe ohne Bezug.",
        [{"art": "knoten", "id": "/brainlehr"}])
    assert _ziel_treffer("siehe /brainlehr fuer Details", [{"art": "knoten", "id": "/brainlehr"}])

    # auswerten(): synthetische Aufgaben+Antworten, alle drei Bedingungen
    # in M1 UND M2 (M2-NEG ist Teil 1 des Auftrags: Negativkontrolle auch
    # dort, sonst nicht unterscheidbar ob der Unterschied vom INHALT oder
    # nur davon kommt, dass ueberhaupt ein Block anhaengt).
    aufgaben = {"schiefe_gegenprobe": {"drei_haeufigste_anteil": 0.1}, "zellen": [
        {"key": "m1-00|MIT", "gruppe": "M1", "case_id": "m1-00", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/x/y"}],
         "prompt": "Frage\n\n<knowledge-recall>\n- [/x/y] ...\n</knowledge-recall>"},
        {"key": "m1-00|OHNE", "gruppe": "M1", "case_id": "m1-00", "condition": "OHNE",
         "ziele": [{"art": "knoten", "id": "/x/y"}]},
        {"key": "m1-00|NEG", "gruppe": "M1", "case_id": "m1-00", "condition": "NEG",
         "ziele": [{"art": "knoten", "id": "/x/y"}]},
        {"key": "m2-00|MIT", "gruppe": "M2", "case_id": "m2-00", "condition": "MIT", "ziele": None},
        {"key": "m2-00|OHNE", "gruppe": "M2", "case_id": "m2-00", "condition": "OHNE", "ziele": None},
        {"key": "m2-00|NEG", "gruppe": "M2", "case_id": "m2-00", "condition": "NEG", "ziele": None},
    ]}
    # Pflichtfeld 'werkzeuge_benutzt' (Teil 2): je Zelle ein Objekt statt
    # eines nackten Strings. m1-00|NEG verneint Werkzeugnutzung ausdruecklich
    # -- muss NORMAL in die Quote eingehen (Negativfall der Abnahme).
    antworten = {"antworten": {
        "m1-00|MIT": {"antwort": "Ich stuetze mich auf /x/y, das passt genau.",
                      "werkzeuge_benutzt": False},
        "m1-00|OHNE": {"antwort": "Ich rate auf gut Glueck, kein Anhaltspunkt.",
                       "werkzeuge_benutzt": False},
        "m1-00|NEG": {"antwort": "Der fremde Block handelt von etwas anderem, ich rate.",
                      "werkzeuge_benutzt": False},
        "m2-00|MIT": {"antwort": "Ja, das ist moeglich, siehe die genannte Einschraenkung.",
                      "werkzeuge_benutzt": False},
        "m2-00|OHNE": {"antwort": "Ja, das ist grundsaetzlich moeglich.",
                       "werkzeuge_benutzt": False},
        "m2-00|NEG": {"antwort": "Ja, das ist grundsaetzlich moeglich.",
                      "werkzeuge_benutzt": False},
    }}
    erg = auswerten(aufgaben, antworten)
    assert erg["m1"]["MIT"]["treffer"] == 1 and erg["m1"]["MIT"]["n"] == 1
    assert erg["m1"]["OHNE"]["treffer"] == 0
    assert erg["m1"]["NEG"]["treffer"] == 0
    assert erg["m2"]["faelle_mit_mit_bedingung"] == 1
    # NEG-Vergleich fuer M2: gleicher Wortlaut wie OHNE -> nicht unterschiedlich.
    assert erg["m2"]["faelle_mit_neg_bedingung"] == 1
    assert erg["m2"]["unterschiedlich_neg"] == 0
    assert erg["m1"]["werkzeug_ausgeschlossen"] == []
    assert erg["m2"]["werkzeug_ausgeschlossen"] == []
    # Liefer-Analyse: der MIT-Block enthielt /x/y (Retrieval-Treffer), und
    # die Antwort nutzte es auch -> 1/1.
    la = erg["m1"]["liefer_analyse"]
    assert la["geliefert_gesamt"] == 1 and la["geliefert_und_benutzt"] == 1

    # Fehlbestand: eine fehlende Antwort darf nicht stillschweigend uebergangen werden.
    luecke = auswerten(aufgaben, {"antworten": {
        "m1-00|MIT": {"antwort": "x", "werkzeuge_benutzt": False},
        "m1-00|OHNE": {"antwort": "y", "werkzeuge_benutzt": False},
        "m2-00|MIT": {"antwort": "a", "werkzeuge_benutzt": False},
        "m2-00|OHNE": {"antwort": "b", "werkzeuge_benutzt": False}}})
    assert "m1-00|NEG" in luecke["m1"]["fehlbestand"]
    assert "m2-00" in luecke["m2"]["fehlbestand"]

    # Teil 2, Abnahme (a): fehlt das Pflichtfeld, geht die Zelle NICHT in
    # die Quote ein, sondern zaehlt getrennt als ausgeschlossen.
    antw_ohne_feld = json.loads(json.dumps(antworten))
    antw_ohne_feld["antworten"]["m1-00|MIT"] = "nackter String, kein Feld"
    erg_o = auswerten(aufgaben, antw_ohne_feld)
    assert erg_o["m1"]["MIT"]["n"] == 0  # nicht mehr in der Quote
    assert erg_o["m1"]["MIT"]["anteil"] is None
    assert erg_o["m1"]["MIT"]["hinweis"] == "keine verwertbaren Zellen"
    assert "m1-00|MIT" in erg_o["m1"]["werkzeug_ausgeschlossen"]

    # Teil 2, Abnahme: werkzeuge_benutzt=True sperrt die Zelle ebenso.
    antw_mit_werkzeug = json.loads(json.dumps(antworten))
    antw_mit_werkzeug["antworten"]["m2-00|MIT"]["werkzeuge_benutzt"] = True
    erg_w = auswerten(aufgaben, antw_mit_werkzeug)
    assert erg_w["m2"]["faelle_mit_mit_bedingung"] == 0
    assert "m2-00|MIT" in erg_w["m2"]["werkzeug_ausgeschlossen"]

    # Grenzwert: sind ALLE M1-Zellen ausgeschlossen, keine Quote als 0%
    # ausweisen, sondern erkennbar als "keine verwertbaren Zellen".
    alles_werkzeug = {"antworten": {
        k: (v if k.startswith("m2") else {"antwort": v["antwort"], "werkzeuge_benutzt": True})
        for k, v in antworten["antworten"].items()}}
    erg_alles = auswerten(aufgaben, alles_werkzeug)
    for cond in ("MIT", "OHNE", "NEG"):
        assert erg_alles["m1"][cond]["n"] == 0
        assert erg_alles["m1"][cond]["anteil"] is None
        assert erg_alles["m1"][cond]["hinweis"] == "keine verwertbaren Zellen"

    # leck_pruefung(): findet eine woertlich enthaltene Ziel-Kennung
    # (Auftrag Risiko 1) -- und der Negativfall, ein sauberer Text.
    leckt, betroffen = leck_pruefung(
        "Kriterium: die Antwort sollte /x/y nennen.", [{"id": "/x/y"}])
    assert leckt and betroffen == ["/x/y"]
    sauber, betroffen2 = leck_pruefung(
        "Kriterium: die Antwort sollte die Reihenfolge begruenden.", [{"id": "/x/y"}])
    assert not sauber and betroffen2 == []

    # dreiteilung_erreichbarkeit(): vier Klassen mechanisch aus MIT+WERKZEUG.
    aufg_dt = {"zellen": [
        {"key": "m1-00|MIT", "gruppe": "M1", "case_id": "m1-00", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/a/eins"}]},
        {"key": "m1-00|WERKZEUG", "gruppe": "M1", "case_id": "m1-00", "condition": "WERKZEUG",
         "ziele": [{"art": "knoten", "id": "/a/eins"}]},
        {"key": "m1-01|MIT", "gruppe": "M1", "case_id": "m1-01", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/a/zwei"}]},
        {"key": "m1-01|WERKZEUG", "gruppe": "M1", "case_id": "m1-01", "condition": "WERKZEUG",
         "ziele": [{"art": "knoten", "id": "/a/zwei"}]},
        {"key": "m1-02|MIT", "gruppe": "M1", "case_id": "m1-02", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/a/drei"}]},
        {"key": "m1-02|WERKZEUG", "gruppe": "M1", "case_id": "m1-02", "condition": "WERKZEUG",
         "ziele": [{"art": "knoten", "id": "/a/drei"}]},
        {"key": "m1-03|MIT", "gruppe": "M1", "case_id": "m1-03", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/a/vier"}]},
        {"key": "m1-03|WERKZEUG", "gruppe": "M1", "case_id": "m1-03", "condition": "WERKZEUG",
         "ziele": [{"art": "knoten", "id": "/a/vier"}]},
    ]}
    antw_dt = {"antworten": {
        # Fall 1: MIT trifft -> gefunden_mit_einspielung.
        "m1-00|MIT": {"antwort": "siehe /a/eins", "werkzeuge_benutzt": False},
        "m1-00|WERKZEUG": {"antwort": "nichts gefunden", "werkzeuge_benutzt": True, "werkzeug_pfad": "grep"},
        # Fall 2: MIT verfehlt, WERKZEUG trifft -> selbst_gefunden.
        "m1-01|MIT": {"antwort": "keine Ahnung", "werkzeuge_benutzt": False},
        "m1-01|WERKZEUG": {"antwort": "siehe /a/zwei via grep", "werkzeuge_benutzt": True, "werkzeug_pfad": "grep"},
        # Fall 3: beide verfehlen -> gar_nicht_gefunden.
        "m1-02|MIT": {"antwort": "keine Ahnung", "werkzeuge_benutzt": False},
        "m1-02|WERKZEUG": {"antwort": "auch nichts gefunden", "werkzeuge_benutzt": False},
        # Fall 4: WERKZEUG-Zelle ohne Pflichtfeld -> unbestimmt (fail-closed).
        "m1-03|MIT": {"antwort": "keine Ahnung", "werkzeuge_benutzt": False},
        "m1-03|WERKZEUG": "nackter String ohne Feld",
    }}
    dt = dreiteilung_erreichbarkeit(aufg_dt, antw_dt)
    assert dt["gefunden_mit_einspielung"] == 1
    assert dt["selbst_gefunden"] == 1
    assert dt["gar_nicht_gefunden"] == 1
    assert dt["unbestimmt"] == 1
    assert dt["gesamt"] == 3  # unbestimmt zaehlt NICHT in die drei Klassen

    # M1-Pool schliesst 'kennung' aus (Selbstbezug-Ausschluss).
    if M1_QUELLE.exists():
        pool = m1_pool()
        assert all(f["klasse"] in M1_ERLAUBTE_KLASSEN for f in pool)
        assert not any(f["klasse"] == "kennung" for f in pool)

    print("selftest ok: Blockformat, Zieltreffer (voll/Endstueck/Grenzfall/Fehlschlag), "
          "auswerten() (M1 drei Bedingungen, M2 MIT+NEG, Fehlbestand, "
          "Werkzeug-Ausschluss, Grenzwert alle ausgeschlossen), M1-Pool-Ausschluss, "
          "leck_pruefung(), dreiteilung_erreichbarkeit() (vier Klassen)",
          file=_sys.stderr)


if __name__ == "__main__":
    main()
