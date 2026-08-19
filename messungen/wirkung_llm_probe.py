#!/usr/bin/env python3
"""Wirkungsmessung ueber ein echtes Modell -- Ergaenzung zu
messungen/wirkung_ohne_gedaechtnis.py (misst dort nur die ZUFUHR, weil kein
Modell erreichbar war: kein Paket 'anthropic', kein Schluessel, siehe dessen
Modulkopf und runs/wirkung_ohne_gedaechtnis_2026-08-18T194429.json,
modell_verfuegbar=false). Jetzt laeuft Ollama lokal (OpenAI-kompatible API
unter http://127.0.0.1:11434/v1/chat/completions, gemma4:12b, kein
Schluessel noetig) -- Auftrag 2026-08-18.

EIGENES SKRIPT statt Erweiterung der Vorlage: die Vorlage bleibt der Beleg
fuer den Modell-Ausfall zu ihrem Zeitpunkt (ihr eigener Modulkopf erklaert
genau das); ein echter Modellaufruf ist ein anderer Pruefgegenstand
(Netzwerk, Zeit, Nichtdeterminismus des Modells) und verdient eine eigene
Datei. Wiederverwendet OHNE Kopie: lade_faelle/rang_des_ziels aus
vier_gatearten.py, zielausschnitt/mit_speicher_enthaelt_ziel/
ohne_speicher_enthaelt_ziel/positivkontrolle/KORPUS aus
wirkung_ohne_gedaechtnis.py, knowledge_search aus dem echten Produktivweg
(knowledge_mcp_server).

STICHPROBE, kein Volllauf: gemessen (1 Aufruf, max_tokens=400) ~9.3s netto
Modellzeit; bei laengeren Prompts (Hintergrundwissen im Speicherpfad,
max_tokens=800 wegen Reasoning-Vorspann des Modells, siehe Befund im
Auftrag) ist mit deutlich mehr zu rechnen. 35 Faelle x 2 Laeufe waeren damit
nicht in vertretbarer Zeit fahrbar. Gewaehlt: 10 Zielfaelle (darunter der
retrieval-bestaetigte Positivfall) + 4 Negativfaelle = 14 Faelle x 2 Laeufe
= 28 Modellaufrufe. n wird im Ergebnis ausdruecklich als Stichprobe
ausgewiesen, nicht als Vollmessung.

AUSWAHL DER 10 ZIELFAELLE (deterministisch, keine Zufallsziehung): zuerst
der Fall, dessen target_id mit der bereits bestehenden Positivkontrolle aus
wirkung_ohne_gedaechtnis.positivkontrolle() uebereinstimmt (Ziel liegt
nachweislich auf Rang 1 der Speicher-Zufuhr). Danach je 4 weitere Faelle,
bei denen mit_speicher_enthaelt_ziel() wahr bzw. falsch ist (Listenreihen-
folge aus dem Korpus, keine Ziehung) -- das deckt sowohl den Fall ab, in dem
der Speicher etwas zu bieten hat, als auch den, in dem er es nicht hat.

BLINDBEWERTUNG (der heikle Teil): Die Bewertungsfunktion bewertung() erhaelt
ausschliesslich (Antworttext, target_label). Sie bekommt nie mitgeteilt, ob
die Antwort aus dem Lauf MIT oder OHNE Speicher stammt -- diese Information
existiert an der Stelle im Code, an der bewertung() aufgerufen wird, gar
nicht als Parameter. Es ist KEINE Handbewertung und KEIN LLM-als-Richter
(das haette ueber Formulierungen im Bedingungsnamen stolpern koennen),
sondern eine deterministische Wortabgleichsfunktion, die fuer A und B im
selben Codepfad, in derselben Reihenfolge, mit denselben Regeln laeuft. Es
gibt dadurch keine Stelle im Ablauf, an der Wissen ueber die Bedingung in
die Bewertung einfliessen koennte.

KRITERIUM: Anteil der inhaltstragenden Woerter (Laenge >= 4, deutsche
Kleinschreibung, kleine Stoppwortliste ausgefiltert) aus target_label, die
woertlich in der Antwort vorkommen. Schwelle 0.4 (mind. 40% der
Schluesselwoerter) -- grob, transparent, vor der Messung festgelegt, nicht
nachtraeglich an ein Ergebnis angepasst.

NEGATIVKONTROLLE AUF LLM-EBENE: die 10 category=negative-Faelle haben kein
target_label -- "besser" ist dort so wenig definierbar wie im Vorlagen-
skript. Geprueft wird stattdessen KONTAMINATION: enthaelt die
Speicher-Antwort Woerter aus dem eingespielten (aber fachfremden)
Hintergrundwissen, die weder in der Aufgabe noch in der speicherlosen
Antwort vorkommen? Das ist das Gegenstueck zu Gate 2 aus vier_gatearten.py
auf der Erzeugungsstufe: wenn der Speicher hier haeufig durchschlaegt,
wuerde ein reines "wurde etwas uebernommen"-Kriterium faelschlich Wirkung
zeigen.

AUFGABE 99 (2026-08-18), NACHTRAG: Lauf runs/wirkung_llm_probe_
2026-08-18T210154.json bestand die Negativkontrolle nicht (2 von 4
kontaminiert). Wortweise Pruefung der beiden Faelle ergab zwei Befunde,
beide in signifikante_woerter()/kontamination() behoben:
(1) STOPWORTE ist transliteriert geschrieben ("ueber", "koennen", ...),
    echter Modelltext traegt aber Umlaute ("über", "können") -- kein
    Stoppwort mit Umlaut griff je. signifikante_woerter() normalisiert
    Umlaute jetzt VOR dem Abgleich.
(2) Beide falsch-positiven Faelle hatten eine LEERE speicherlose Antwort
    (finish_reason "length", 0 Zeichen). Bei leerer Baseline ist jedes Wort
    der Speicher-Antwort trivial "neu" -- der Vergleich misst dann die
    leere Baseline, nicht die Wirkung des Speichers. kontamination() gibt
    jetzt None (nicht messbar) statt False/True zurueck, wenn eine der
    beiden Antworten leer ist -- dieselbe Behandlung wie bewertung() sie
    fuer kein_ergebnis_mit/ohne bei den Zielfaellen schon bekommt.
Gegenprobe auf den gespeicherten Antworttexten (kein neuer Modelllauf):
runs/kriterium_99_gegenprobe.json.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import knowledge_mcp_server as kms  # noqa: E402 -- Produktivweg, kein Nachbau
from vier_gatearten import lade_faelle, rang_des_ziels  # noqa: E402
from wirkung_ohne_gedaechtnis import (  # noqa: E402 -- Vorlage, wiederverwendet
    KORPUS,
    mit_speicher_enthaelt_ziel,
    positivkontrolle,
    zielausschnitt,
)

OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
MODELL = "gemma4:12b"
MAX_TOKENS = 3000
# GEMESSEN 2026-08-18, zwei Laeufe mit DEMSELBEN Prompt (Positivkontrolle,
# 3213 Zeichen mit Speicher):
#   max_tokens=800  -> finish_reason "length", content 0 Zeichen
#   max_tokens=3000 -> finish_reason "stop",   content 4161 Zeichen
#
# gemma4 ist ein Reasoning-Modell: die Denkschritte skalieren mit der
# Prompt-Laenge, und ein Speicher-Prompt ist rund dreimal so lang wie der
# nackte. Bei 800 war das Budget verbraucht, BEVOR eine Antwort begann --
# deshalb kamen im Lauf 2026-08-18T210154 alle vier leeren Antworten
# ausschliesslich MIT Speicher und keine einzige ohne.
#
# Das ist die teuerste Sorte Messfehler, weil sie wie ein ERGEBNIS aussieht:
# "mit Speicher keine Antwort" liest sich als Wirkungslosigkeit, war aber
# eine Grenze des Aufbaus. Wer hier den Wert senkt, misst wieder das Budget
# statt die Wirkung.
N_ZIEL = 10
N_NEGATIV = 4
SCHWELLE = 0.4
STOPWORTE = {
    "eine", "einer", "einem", "einen", "eines", "dass", "sich", "sind",
    "wird", "werden", "wurde", "wurden", "haben", "hatte", "hatten", "auch",
    "nicht", "kann", "koennen", "muss", "muessen", "soll", "sollen", "wenn",
    "waehrend", "durch", "ueber", "unter", "nach", "vor", "bei", "aus",
    "dabei", "diese", "dieser", "dieses", "dort", "hier", "dann", "noch",
    "dafuer", "damit", "dadurch", "dessen", "deren",
}


_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def signifikante_woerter(text: str) -> set[str]:
    """AUFGABE 99, 2026-08-18: normalisiert Umlaute (ae/oe/ue/ss) VOR dem
    Stoppwortabgleich. Befund am alten Lauf runs/wirkung_llm_probe_
    2026-08-18T210154.json: STOPWORTE ist in transliterierter Schreibweise
    gepflegt ("ueber", "koennen", "waehrend", ...), der Text aus echten
    Modellantworten aber in echten Umlauten ("über", "können", "während").
    Ohne Normalisierung greift KEIN Stoppwort mit Umlaut je -- ein
    Negativfall (Ordnungsamt-Frage) wurde dadurch allein wegen des Wortes
    "über" als kontaminiert gewertet."""
    text = (text or "").lower().translate(_UMLAUT)
    toks = re.findall(r"[a-z]{4,}", text)
    return {t for t in toks if t not in STOPWORTE}


def bewertung(antwort: str, target_label: str) -> bool | None:
    """True/False, oder None wenn target_label keine pruefbaren Woerter hat."""
    ziel_woerter = signifikante_woerter(target_label)
    if not ziel_woerter:
        return None
    treffer = signifikante_woerter(antwort) & ziel_woerter
    return (len(treffer) / len(ziel_woerter)) >= SCHWELLE


def kontamination(
    antwort_mit: str, antwort_ohne: str, memory_text: str, task: str,
    leer_mit: bool = False, leer_ohne: bool = False,
) -> bool | None:
    """True/False, oder None wenn nicht messbar.

    AUFGABE 99, 2026-08-18: Befund am alten Lauf -- BEIDE kontaminierten
    Negativfaelle (Knoten-Frage, Ordnungsamt-Frage) hatten eine LEERE
    speicherlose Antwort (finish_reason 'length', 0 Zeichen -- bekanntes
    Restrisiko von gemma4 als Reasoning-Modell, siehe MAX_TOKENS-Kommentar
    oben; unabhaengig von den dort schon 3000 gesetzten Tokens). Bei leerer
    Baseline enthaelt fremd_in_ohne IMMER die leere Menge -- jedes Wort aus
    der Speicher-Antwort zaehlt dann automatisch als 'neu', unabhaengig
    davon, ob der Speicher tatsaechlich durchschlug. Der Vergleich ist bei
    leerer Baseline nicht aussagekraeftig und wird als nicht messbar (None)
    ausgewiesen, statt einen Wert zu erzwingen -- dieselbe Behandlung, die
    bewertung() bei leeren Antworten schon bekommt (s_mit/s_ohne = None)."""
    if leer_mit or leer_ohne:
        return None
    memory_woerter = signifikante_woerter(memory_text) - signifikante_woerter(task)
    fremd_in_mit = signifikante_woerter(antwort_mit) & memory_woerter
    fremd_in_ohne = signifikante_woerter(antwort_ohne) & memory_woerter
    return len(fremd_in_mit - fremd_in_ohne) >= 2


def memory_text(task: str) -> str:
    out = kms.knowledge_search(task, scope="all", max_results=5)
    zeilen = []
    for r in out["results"]:
        if r.get("kind") == "node":
            zeilen.append(f"- {r.get('title', '')}: {r.get('summary', '')}")
        else:
            zeilen.append(f"- {r.get('summary', '')}")
    return "\n".join(zeilen)


def frage_ollama(prompt: str) -> tuple[str, str]:
    """Returns (content, finish_reason). Leerer content bei finish_reason
    'length' ist KEIN Fehler -- siehe Modulkopf: Reasoning frisst das Budget."""
    payload = json.dumps({
        "model": MODELL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read())
    choice = d["choices"][0]
    return choice["message"].get("content") or "", choice.get("finish_reason", "")


def prompt_ohne(task: str) -> str:
    return f"Beantworte kurz und konkret auf Deutsch:\n\n{task}"


def prompt_mit(task: str, memory: str) -> str:
    return (
        f"Hintergrundwissen aus dem Wissensspeicher:\n{memory}\n\n"
        f"Beantworte kurz und konkret auf Deutsch, nutze das Hintergrundwissen "
        f"wo es passt:\n\n{task}"
    )


def waehle_zielfaelle(faelle_mit_ziel: list[dict], pk_ziel: str) -> list[dict]:
    pk_fall = next(f for f in faelle_mit_ziel if f["target_id"] == pk_ziel)
    rest = [f for f in faelle_mit_ziel if f["target_id"] != pk_ziel]
    gut, schlecht = [], []
    for f in rest:
        mit, _ = mit_speicher_enthaelt_ziel(f)
        (gut if mit else schlecht).append(f)
    ausgewaehlt = [pk_fall] + gut[:4] + schlecht[:5]
    return ausgewaehlt[:N_ZIEL]


def selftest() -> None:
    assert bewertung("Der Buckeberg Konsil regelt die Governance.", "Buckeberg Konsil Governance") is True
    assert bewertung("Voellig andere Antwort ueber Kochrezepte.", "Buckeberg Konsil Governance") is False
    assert bewertung("egal was", "") is None
    assert signifikante_woerter("Und dass sich wird") == set()
    # AUFGABE 99: Umlaut-Stoppwort muss jetzt greifen (vorher nie, weil
    # STOPWORTE transliteriert war und der Text echte Umlaute traegt).
    assert "ueber" not in signifikante_woerter("Er sprach über die Sache.")
    # AUFGABE 99: leere Baseline -> nicht messbar, nicht automatisch "True".
    assert kontamination("Kalibrierbremse Plan Aufgabe", "", "Kalibrierbremse Plan", "x",
                          leer_mit=False, leer_ohne=True) is None
    assert kontamination("x", "x", "y", "z", leer_mit=True, leer_ohne=False) is None
    print("selftest: ok", file=sys.stderr)


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return

    faelle_mit_ziel, faelle_ohne_ziel = lade_faelle(KORPUS)
    pk = positivkontrolle(faelle_mit_ziel)
    if not pk["bestanden"]:
        print("BEFUND: retrieval-Positivkontrolle nicht bestanden -- Aufbau verdaechtig, Abbruch.", file=sys.stderr)
        sys.exit(1)

    ziel_faelle = waehle_zielfaelle(faelle_mit_ziel, pk["ziel"])
    negativ_faelle = faelle_ohne_ziel[:N_NEGATIV]

    je_fall = []
    kein_ergebnis_mit = 0
    kein_ergebnis_ohne = 0
    mit_speicher_besser = 0
    ohne_speicher_besser = 0
    t0 = time.time()

    for f in ziel_faelle:
        task = f["task"]
        ziel_txt = zielausschnitt(f) or f.get("target_label", "")
        mem = memory_text(task)

        antwort_ohne, fr_ohne = frage_ollama(prompt_ohne(task))
        antwort_mit, fr_mit = frage_ollama(prompt_mit(task, mem))

        leer_ohne = fr_ohne == "length" and not antwort_ohne.strip()
        leer_mit = fr_mit == "length" and not antwort_mit.strip()
        kein_ergebnis_ohne += int(leer_ohne)
        kein_ergebnis_mit += int(leer_mit)

        s_ohne = None if leer_ohne else bewertung(antwort_ohne, ziel_txt)
        s_mit = None if leer_mit else bewertung(antwort_mit, ziel_txt)
        if s_mit:
            mit_speicher_besser += 1
        if s_ohne:
            ohne_speicher_besser += 1

        je_fall.append({
            "ziel": f["target_id"], "art": f["target_kind"], "target_label": ziel_txt,
            "ohne_speicher": {"antwort": antwort_ohne, "finish_reason": fr_ohne, "trifft_ziel": s_ohne},
            "mit_speicher": {"antwort": antwort_mit, "finish_reason": fr_mit, "trifft_ziel": s_mit},
        })
        print(f"  {f['target_id']}: ohne={s_ohne} mit={s_mit}", file=sys.stderr)

    negativ_zeilen = []
    n_kontaminiert = 0
    n_kontam_nicht_messbar = 0
    for f in negativ_faelle:
        task = f["task"]
        mem = memory_text(task)
        antwort_ohne, fr_ohne = frage_ollama(prompt_ohne(task))
        antwort_mit, fr_mit = frage_ollama(prompt_mit(task, mem))
        leer_ohne = fr_ohne == "length" and not antwort_ohne.strip()
        leer_mit = fr_mit == "length" and not antwort_mit.strip()
        kontam = kontamination(antwort_mit, antwort_ohne, mem, task, leer_mit, leer_ohne)
        n_kontaminiert += int(kontam is True)
        n_kontam_nicht_messbar += int(kontam is None)
        negativ_zeilen.append({
            "frage": task,
            "ohne_speicher": {"antwort": antwort_ohne, "finish_reason": fr_ohne},
            "mit_speicher": {"antwort": antwort_mit, "finish_reason": fr_mit},
            "kontaminiert": kontam,
        })
        print(f"  negativ: kontaminiert={kontam}", file=sys.stderr)

    dauer_s = round(time.time() - t0, 1)
    n = len(ziel_faelle)

    ergebnis = {
        "weg": (
            "gemma4:12b ueber Ollama OpenAI-kompatible API (http://127.0.0.1:11434/v1/"
            "chat/completions), Speicher-Zufuhr ueber knowledge_mcp_server.knowledge_search() "
            "(echter Produktivweg, max_results=5)"
        ),
        "modell": MODELL,
        "kriterium": (
            f"'besser' = mindestens {int(SCHWELLE*100)}% der inhaltstragenden Woerter "
            "(Laenge>=4, Stoppwortliste ausgefiltert) aus target_label kommen woertlich in "
            "der Antwort vor. Automatische Funktion bewertung(antwort, target_label) -- kein "
            "LLM-als-Richter, keine Handbewertung."
        ),
        "n": n,
        "n_negativ": len(negativ_faelle),
        "hinweis_stichprobe": (
            f"STICHPROBE, kein Volllauf ueber alle 35 Faelle: {n} Zielfaelle + "
            f"{len(negativ_faelle)} Negativfaelle x 2 Laeufe = {2*(n+len(negativ_faelle))} "
            f"Modellaufrufe, {dauer_s}s Gesamtlaufzeit."
        ),
        "mit_speicher": mit_speicher_besser,
        "ohne_speicher": ohne_speicher_besser,
        "differenz": mit_speicher_besser - ohne_speicher_besser,
        "kein_ergebnis": {
            "mit_speicher": kein_ergebnis_mit, "ohne_speicher": kein_ergebnis_ohne,
            "hinweis": "finish_reason=='length' mit leerem content -- zaehlt NICHT als Fehlantwort, separat ausgewiesen.",
        },
        "blindbewertung": (
            "bewertung() erhaelt ausschliesslich (Antworttext, target_label) als Parameter -- "
            "welcher Lauf (mit/ohne Speicher) die Antwort erzeugt hat, ist an dieser Stelle im "
            "Code nicht vorhanden und kann daher nicht einfliessen. Dieselbe deterministische "
            "Wortabgleichsfunktion laeuft fuer beide Bedingungen im selben Codepfad. Kein "
            "LLM-als-Richter (koennte ueber Bedingungsnamen im Prompt stolpern), keine "
            "Handbewertung durch den Messenden (der wusste beim Schreiben von bewertung() nicht, "
            "welche konkrete Antwort er je Fall erhalten wuerde)."
        ),
        "positivkontrolle_retrieval": pk,
        "positivkontrolle_llm": next(
            (e for e in je_fall if e["ziel"] == pk["ziel"]), None
        ),
        "negativkontrolle": {
            "n": len(negativ_zeilen),
            "kontaminiert": n_kontaminiert,
            "nicht_messbar": n_kontam_nicht_messbar,
            "bestanden": n_kontaminiert == 0,
            "kriterium": (
                "kontamination(): Umlaute vor dem Wortabgleich normalisiert (ae/oe/ue/ss), "
                "sonst greift kein Stoppwort mit Umlaut (Befund Aufgabe 99). Mind. 2 "
                "inhaltstragende Woerter aus dem eingespielten Hintergrundwissen (abzueglich "
                "Woerter, die schon in der Aufgabe stehen), die NUR in der Speicher-Antwort "
                "vorkommen, nicht in der speicherlosen -- Indiz, dass fachfremdes Material aus "
                "dem Speicher durchschlaegt. None (nicht messbar) statt False, wenn eine der "
                "beiden Antworten leer ist (finish_reason 'length', 0 Zeichen): eine leere "
                "Baseline macht jedes Wort der Speicher-Antwort trivial 'neu' und wuerde die "
                "Kontamination ueberzeichnen (Befund Aufgabe 99: beide falsch-positiven Faelle "
                "im Lauf 2026-08-18T210154 hatten genau diese leere Baseline)."
            ),
            "je_frage": negativ_zeilen,
        },
        "grenze": [
            "Stichprobe (14 von 35 Zielfaellen bzw. 4 von 10 Negativfaellen), keine Vollmessung -- "
            "siehe hinweis_stichprobe.",
            "Ein Modelllauf ist nicht deterministisch (Temperatur nicht auf 0 gesetzt) -- ein "
            "zweiter Lauf koennte andere Einzelwerte liefern, insbesondere bei knappen Faellen.",
            "bewertung() ist eine grobe Wortabgleichsfunktion, kein semantisches Verstehen -- "
            "eine sinngemaess richtige Antwort mit anderen Worten wird als 'trifft nicht' gewertet.",
            "kontamination() ist ein Indiz, kein Beweis: Ueberschneidungen koennen auch aus "
            "allgemeinem Vokabular stammen, das zufaellig in Aufgabe UND Hintergrundwissen fehlt.",
            "Der echte Recall-Hook (haken/knowledge_recall_hook.py) laeuft hier nicht mit -- "
            "memory_text() ist eine eigene, einfachere Formatierung der Top-5-Treffer.",
            "Gilt fuer einen Zeitpunkt (2026-08-18) gegen den aktuell laufenden Bestand und das "
            "aktuell installierte gemma4:12b.",
        ],
        "je_fall": je_fall,
    }

    if not ergebnis["positivkontrolle_llm"] or not ergebnis["positivkontrolle_llm"]["mit_speicher"]["trifft_ziel"]:
        print("BEFUND: Positivkontrolle auf LLM-Ebene NICHT bestanden (mit_speicher traf das Ziel nicht) -- Aufbau verdaechtig.", file=sys.stderr)
    if n_kontaminiert > 0:
        print(f"BEFUND: Negativkontrolle verletzt -- {n_kontaminiert} von {len(negativ_zeilen)} Faellen kontaminiert.", file=sys.stderr)

    out_path = _w / "runs" / f"wirkung_llm_probe_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_path}")
    print(f"n={n} mit_speicher={mit_speicher_besser} ohne_speicher={ohne_speicher_besser} "
          f"differenz={ergebnis['differenz']} negativkontrolle_bestanden={ergebnis['negativkontrolle']['bestanden']} "
          f"dauer={dauer_s}s")


if __name__ == "__main__":
    main()
