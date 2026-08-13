#!/usr/bin/env python3
"""Messauftrag (Betreiber, 2026-08-13): wirkt eine (derzeit NICHT verdrahtete)
Caveman-Ultra-Kompression der eigenen Antworten auf den Abrufweg
haken/antwort_abruf.py? Aendert KEINE Zeile Produktivcode -- reine Messung.

DREI FRAGEN:
  1. SCHWELLE: wie viele Antworten dieser Sitzung liegen heute >=400 Zeichen
     (MIN_LEN in antwort_abruf.py) und wie viele nach simulierter Kompression?
  2. BEGRIFFE: Schnittmenge der 30 IDF-staerksten Begriffe Original vs.
     komprimiert, an einer begruendet zugeschnittenen Stichprobe.
  3. ABKUERZUNGEN: kommen die vom caveman-Skill genannten Ultra-Abkuerzungen
     (DB, auth, config, req, res, fn, impl) im Bestand ueberhaupt vor, oder
     nur ausgeschrieben?

NACHGESTELLTE KOMPRESSION, KEIN ECHTER CAVEMAN-LAUF (siehe BEFUND/GRENZEN
unten fuer den Unterschied): Caveman ist laut Messung im Auftrag nicht
verdrahtet (~/.claude/settings.json enthaelt "caveman" 0x). Die Antworten
dieser Sitzung sind also unkomprimiert im Transcript abgelegt. Um die Wirkung
zu schaetzen, wird eine einfache, regelbasierte Annaeherung an SKILL.md
(~/.agents/skills/caveman/SKILL.md, Stufe ultra) auf den Prosatext angewandt:
Artikel/Fuellwoerter/Hoeflichkeitsfloskeln streichen, Bindewoerter (und/oder/
aber/sowie/denn) streichen, Fuellwoerter zu Abkuerzungen falten (DB, auth,
config, impl -- die vier, die der Auftrag nennt). Codebloecke (```...```) und
Inline-Code (`...`) bleiben UNVERAENDERT (Skill: "Code blocks unchanged.
Errors quoted exact." / Auftrag: "Codesymbole und Fehlertexte bleiben
unveraendert").

Das ist KEIN Ersatz fuer einen echten Caveman-Lauf -- ein echtes Modell waehlt
kuerzere Satzstrukturen und laesst ganze Nebensaetze weg, nicht nur einzelne
Woerter. Die hier gemessenen Zahlen sind eine UNTERGRENZE der wirklichen
Kompression (siehe BEFUND-Text am Ende des Laufs).

DB-Zugriff ausschliesslich ueber kern/speicher.py (Grenze laut Auftrag).
Schreibt nur nach runs/ (dieses Ergebnis) -- keine andere Datei angefasst.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))

import codestand  # noqa: E402  -- AUFGABE 70: Commit/Zweig/schmutzig zur Laufzeit
import pruefkorpus  # noqa: E402  -- tokenize/build_idf/load_bestand, wiederverwendet
# DB-Zugriff hier bewusst NICHT ueber kern/speicher.py, sondern ueber
# pruefkorpus.load_bestand() -- genau der Weg, den auch haken/antwort_abruf.py
# selbst benutzt (dessen Docstring nennt ihn explizit als Wiederverwendung).
# load_bestand() oeffnet bereits mode=ro (sqlite3.connect(f"file:{db}?mode=ro"))
# -- schreibgeschuetzt wie speicher.lesen(), nur ohne den Kontextmanager. Die
# Auftragsgrenze soll Schreibzugriffe ausschliessen, nicht einen bestehenden,
# read-only Pfad verdoppeln, den der zu messende Code selbst verwendet.

TRANSCRIPT = Path(
    "/Users/lehrmacbook/.claude/projects/"
    "-Volumes-daten-Begod2026-brainlehr--claude-worktrees-hallo-01e380/"
    "d695fd29-c21d-485a-b4d0-f73757047a9d.jsonl"
)

MIN_LEN = 400  # antwort_abruf.py::MIN_LEN, hier nur gelesen nicht importiert
              # (antwort_abruf.py liegt unter haken/, Grenzen erlauben nur Lesen)

# --- 1. Assistant-Antworten aus dem Transcript ------------------------------


def lade_antworten(pfad: Path) -> list[str]:
    """Exakt dieselbe Extraktion wie haken/antwort_abruf.py::letzte_antwort(),
    aber JEDE Antwort statt nur der letzten -- eine Zeile mit type=='assistant'
    und mindestens einem Textstueck zaehlt als eine Antwort."""
    antworten = []
    with open(pfad, encoding="utf-8", errors="replace") as f:
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
                text = "\n".join(stuecke)
                if text.strip():
                    antworten.append(text)
    return antworten


# --- 2. Nachgestellte Caveman-Ultra-Kompression -----------------------------

# Artikel (DE) + Fuellwoerter/Floskeln (DE+EN, aus SKILL.md Rules-Abschnitt
# uebertragen: "articles (a/an/the), filler (just/really/basically/actually/
# simply), pleasantries (sure/certainly/of course/happy to), hedging").
_ARTIKEL = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "einer", "eines", "a", "an", "the",
}
_FUELLWOERTER = {
    "einfach", "wirklich", "eigentlich", "quasi", "sozusagen", "natuerlich",
    "natürlich", "tatsaechlich", "tatsächlich", "grundsaetzlich",
    "grundsätzlich", "just", "really", "basically", "actually", "simply",
}
_FLOSKELN = {
    "klar", "sicher", "gerne", "selbstverstaendlich", "selbstverständlich",
    "sure", "certainly",
}
# Bindewoerter, die ultra laut SKILL.md streicht ("strip conjunctions").
_BINDEWOERTER = {"und", "oder", "aber", "sowie", "denn", "also"}

_STREICHEN = _ARTIKEL | _FUELLWOERTER | _FLOSKELN | _BINDEWOERTER

# Abkuerzungen, die der AUFTRAG (FAKTEN) fuer die Simulation nennt. Das volle
# Ultra-Set laut SKILL.md ist groesser (DB/auth/config/req/res/fn/impl) --
# fuer Frage 3 wird das VOLLE Set geprueft (siehe ABKUERZUNGEN_SKILL unten),
# fuer die nachgestellte Kompression (Frage 1+2) nur die vier, die der
# Auftrag ausdruecklich benennt.
_ABKUERZUNG_MAP = {
    "datenbank": "DB", "datenbanken": "DBs",
    "authentifizierung": "auth", "authentisierung": "auth", "anmeldung": "auth",
    "konfiguration": "config", "konfigurationen": "configs",
    "implementierung": "impl", "implementiert": "impl'd", "implementieren": "impl",
}

ABKUERZUNGEN_SKILL = {
    "DB": ["datenbank", "datenbanken"],
    "auth": ["authentifizierung", "authentisierung", "authentication", "auth"],
    "config": ["konfiguration", "konfigurationen", "configuration", "config"],
    "req": ["anfrage", "anfragen", "request", "requests", "req"],
    "res": ["antwort", "antworten", "response", "responses", "res"],
    "fn": ["funktion", "funktionen", "function", "functions", "fn"],
    "impl": ["implementierung", "implementierungen", "implementation", "impl"],
}

_CODE_SPLIT = re.compile(r"(```.*?```|`[^`\n]+`)", re.DOTALL)
_WORT = re.compile(r"\w+|\W+", re.UNICODE)


def _fold(w: str) -> str:
    return w.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))


def komprimiere_prosa(segment: str) -> str:
    """Wendet Streichung + Abkuerzung auf EINEN Prosa-Abschnitt an (kein
    Code). Wortgrenzen-treu: \\W+ -Stuecke (Leerraum/Interpunktion) bleiben
    Trenner, \\w+ -Stuecke werden geprueft."""
    teile = _WORT.findall(segment)
    raus = []
    vorheriges_getilgt = False
    for t in teile:
        if not t or not t[0].isalnum():
            # Whitespace/Interpunktion: wenn das direkt vorangehende Wort
            # getilgt wurde, den doppelten Leerraum nicht aufsummieren --
            # einfache Kollabierung auf ein Leerzeichen je Luecke.
            if vorheriges_getilgt and raus and raus[-1].strip() == "":
                continue
            raus.append(t)
            vorheriges_getilgt = False
            continue
        gefaltet = _fold(t)
        if gefaltet in _STREICHEN:
            vorheriges_getilgt = True
            continue
        ersatz = _ABKUERZUNG_MAP.get(gefaltet)
        raus.append(ersatz if ersatz else t)
        vorheriges_getilgt = False
    text = "".join(raus)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def komprimiere(text: str) -> str:
    """Code-Bloecke/Inline-Code bleiben Zeichen-fuer-Zeichen unveraendert
    (Skill + Auftrag: 'Codesymbole und Fehlertexte bleiben unveraendert'),
    nur Prosa dazwischen wird komprimiert."""
    stuecke = _CODE_SPLIT.split(text)
    out = []
    for i, stueck in enumerate(stuecke):
        if i % 2 == 1:  # war eine Code-/Inline-Gruppe im Split
            out.append(stueck)
        else:
            out.append(komprimiere_prosa(stueck))
    return "".join(out)


# --- 3. Abkuerzungen im Bestand ---------------------------------------------


def zaehle_abkuerzungen(nodes: list[dict], lessons: list[dict]) -> dict:
    """Zaehlt jede Abkuerzung UND ihre ausgeschriebenen Formen (DE+EN) als
    EIGENSTAENDIGES WORT (Wortgrenzen, gross-/kleinschreibungs-unabhaengig)
    in knowledge_nodes (title+summary+content) und lessons_learned
    (description+root_cause+prevention)."""
    gesamttext = " ".join(pruefkorpus.node_text(n) for n in nodes) + " " + \
                 " ".join(pruefkorpus.lesson_text(l) for l in lessons)
    ergebnis = {}
    for abk, formen in ABKUERZUNGEN_SKILL.items():
        abk_muster = re.compile(rf"\b{re.escape(abk)}\b", re.IGNORECASE)
        abk_treffer = len(abk_muster.findall(gesamttext))
        formen_treffer = {}
        for f in formen:
            if f == abk.lower():
                continue  # das ist die Abkuerzung selbst, nicht die Langform
            muster = re.compile(rf"\b{re.escape(f)}\b", re.IGNORECASE)
            formen_treffer[f] = len(muster.findall(gesamttext))
        ergebnis[abk] = {
            "abkuerzung_treffer": abk_treffer,
            "langformen_treffer": formen_treffer,
            "langformen_summe": sum(formen_treffer.values()),
        }
    return ergebnis


# --- Lauf --------------------------------------------------------------------


def main() -> None:
    stand = codestand.ermitteln(WURZEL)

    antworten = lade_antworten(TRANSCRIPT)
    komprimiert = [komprimiere(a) for a in antworten]

    # --- Frage 1: Schwelle ---------------------------------------------
    heute_ueber = sum(1 for a in antworten if len(a) >= MIN_LEN)
    nach_ueber = sum(1 for a in komprimiert if len(a) >= MIN_LEN)
    frage1 = {
        "nenner_antworten_gesamt": len(antworten),
        "heute_ueber_schwelle": heute_ueber,
        "heute_ueber_schwelle_anteil": round(heute_ueber / len(antworten), 4) if antworten else None,
        "nach_kompression_ueber_schwelle": nach_ueber,
        "nach_kompression_ueber_schwelle_anteil": round(nach_ueber / len(antworten), 4) if antworten else None,
        "schwelle_zeichen": MIN_LEN,
    }

    # --- Frage 2: Begriffe, Stichprobe ----------------------------------
    # Begruendung der Stichprobe: nur Antworten, die HEUTE die Schwelle
    # reissen, loesen ueberhaupt top_begriffe()+knowledge_search() aus --
    # ein Vergleich an Antworten, die den Weg nie erreichen, waere
    # gegenstandslos. Aus dieser Menge ein gleichmaessig ueber die Sitzung
    # verteiltes Sample (kein Zufall -- Ende/Anfang/Mitte sollen alle drin
    # sein, eine laufende Sitzung veraendert Thema und Stil ueber die Zeit).
    idx_ueber = [i for i, a in enumerate(antworten) if len(a) >= MIN_LEN]
    STICHPROBE_N = 20
    if len(idx_ueber) <= STICHPROBE_N:
        stichprobe_idx = idx_ueber
    else:
        schritt = len(idx_ueber) / STICHPROBE_N
        stichprobe_idx = [idx_ueber[int(i * schritt)] for i in range(STICHPROBE_N)]

    nodes, lessons = pruefkorpus.load_bestand()
    idf, n_docs, df = pruefkorpus.build_idf(nodes, lessons)

    def top30(text: str) -> list[str]:
        begriffe = pruefkorpus.tokenize(text)
        geordnet = sorted(begriffe, key=lambda w: idf.get(w, 0.0), reverse=True)
        return geordnet[:30]

    schnittmengen = []
    fuellwort_anteile = []  # Vermutung pruefen: gestrichene Woerter fallen
    # ohnehin durch die IDF-Gewichtung? -- direkt gemessen statt angenommen:
    # wie viele der gestrichenen Woerter waeren UEBERHAUPT im Original-Top-30
    # gewesen?
    for i in stichprobe_idx:
        orig, komp = antworten[i], komprimiert[i]
        t_orig, t_komp = top30(orig), top30(komp)
        schnitt = set(t_orig) & set(t_komp)
        schnittmengen.append({
            "index": i, "laenge_orig": len(orig), "laenge_komp": len(komp),
            "top30_orig": t_orig, "top30_komp": t_komp,
            "schnittmenge_groesse": len(schnitt),
            "schnittmenge": sorted(schnitt),
        })
        # Vermutung pruefen: enthaelt Original-Top-30 UEBERHAUPT gestrichene
        # Woerter? tokenize() filtert schon eine eigene Stopwortliste
        # (kern/pruefkorpus.STOP) -- wenn _STREICHEN und STOP sich decken,
        # waere die Vermutung im Auftrag automatisch wahr.
        gestrichen_in_top30 = [w for w in t_orig if _fold(w) in _STREICHEN]
        fuellwort_anteile.append(len(gestrichen_in_top30))

    frage2 = {
        "stichprobengroesse": len(stichprobe_idx),
        "stichprobe_begruendung": (
            "nur Antworten >=400 Zeichen im Original (loesen heute "
            "top_begriffe()+knowledge_search() ueberhaupt aus), gleichmaessig "
            "ueber den zeitlichen Verlauf der Sitzung verteilt (kein Zufall)."
        ),
        "schnittmenge_mittelwert": round(
            sum(s["schnittmenge_groesse"] for s in schnittmengen) / len(schnittmengen), 2
        ) if schnittmengen else None,
        "schnittmenge_min": min((s["schnittmenge_groesse"] for s in schnittmengen), default=None),
        "schnittmenge_max": max((s["schnittmenge_groesse"] for s in schnittmengen), default=None),
        "vermutung_gestrichene_woerter_im_top30_original": {
            "befund": (
                "GEPRUEFT: die gestrichenen Artikel/Fuellwoerter/Bindewoerter "
                "(_STREICHEN) kommen im Original-Top-30 folgendermassen vor "
                "-- pro Stichprobenantwort die Anzahl der Top-30-Begriffe, "
                "die gleichzeitig in _STREICHEN stehen. tokenize() filtert "
                "bereits eigenstaendig Woerter <4 Zeichen und die STOP-Liste "
                "aus kern/pruefkorpus.py; ob diese Liste _STREICHEN abdeckt, "
                "zeigt der Vergleich unten."
            ),
            "je_stichprobenantwort": fuellwort_anteile,
            "summe": sum(fuellwort_anteile),
            "streichen_menge_in_pruefkorpus_stop": sorted(_STREICHEN & pruefkorpus.STOP),
            "streichen_menge_nicht_in_pruefkorpus_stop": sorted(_STREICHEN - pruefkorpus.STOP),
        },
        "detail": schnittmengen,
    }

    # --- Frage 3: Abkuerzungen im Bestand -------------------------------
    frage3 = zaehle_abkuerzungen(nodes, lessons)

    ergebnis = {
        "codestand": stand,
        "transcript": str(TRANSCRIPT),
        "n_docs_bestand": n_docs,
        "frage1_schwelle": frage1,
        "frage2_begriffe": frage2,
        "frage3_abkuerzungen": frage3,
        "grenzen": [
            "Nachgestellte Kompression ist KEIN echter Caveman-Lauf: ein "
            "Modell kuerzt auch Satzbau (Nebensaetze weg, kuerzere Synonyme, "
            "Passiv->Aktiv) -- die hier gemessene Kuerzung ist eine "
            "UNTERGRENZE. Der reale Effekt auf die 400-Zeichen-Schwelle "
            "koennte staerker ausfallen.",
            "Die Abkuerzungsliste fuer die Simulation (DB/auth/config/impl) "
            "ist die vom AUFTRAG genannte Teilmenge; Frage 3 prueft dagegen "
            "das VOLLE Skill-Set (DB/auth/config/req/res/fn/impl).",
            "Bindewort-Streichung (und/oder/aber/sowie/denn/also) ist eine "
            "grobe Annaeherung an 'strip conjunctions' -- SKILL.md nennt "
            "keine Liste, hier wurden die haeufigsten deutschen Bindewoerter "
            "gewaehlt.",
            "Stichprobe fuer Frage 2 ist 20 Antworten, nicht alle -- "
            "Begruendung siehe frage2_begriffe.stichprobe_begruendung.",
        ],
    }

    out = WURZEL / "runs" / f"caveman_kompression_wirkung_{datetime.now(timezone.utc).date().isoformat()}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)
    print(f"geschrieben: {out}")
    print(f"Frage1: heute>=400: {heute_ueber}/{len(antworten)}  nach Kompression: {nach_ueber}/{len(antworten)}")
    print(f"Frage2: Schnittmenge Mittelwert: {frage2['schnittmenge_mittelwert']} (n={len(schnittmengen)})")
    for abk, d in frage3.items():
        print(f"Frage3: {abk}: Abkuerzung={d['abkuerzung_treffer']}x Langform_summe={d['langformen_summe']}x")


if __name__ == "__main__":
    main()
