#!/usr/bin/env python3
"""bauvermeidung.py -- vor dem Bauen fragen, ob es das schon gibt.

Betreiberentscheidung 2026-08-21 (Wissensknoten `cb2193a8`), woertlich:
"user sagt ich haette gerne einen kalender, brainlehr schaut autonom in
git, und schlaegt vor nicht selbst bauen unter xyz liegt schon genau das
was du willst". Die Reihenfolge steht im Knoten fest: ERST im eigenen Haus
nachsehen, DANN in der Welt (eigener, spaeterer Auftrag -- braucht Netz).
Diese Datei baut nur die innere Haelfte.

SIE IST KEIN NEUER SUCHWEG, SIE BUENDELT DREI VORHANDENE:

  1. hub/scripts/symbolindex.py  -- Taetigkeit im Quelltext (Docstring/
     Kommentar), ueber den GANZEN Verbund, nicht nur dieses Repo.
  2. knowledge_mcp_server.knowledge_search -- Wissensknoten UND Lehren,
     Stichwort+Bedeutung fusioniert. Deckt u.a. die eigene
     Faehigkeitsbeschreibung ab (melder/selbstbeschreibung.py legt ihre
     Knoten unter /brainlehr/faehigkeiten genau dorthin, wo diese Suche
     ohnehin nachsieht -- ein eigener Aufruf waere derselbe Weg zweimal).
  3. melder/ausloeserlos.py -- warnt, wenn ein Codetreffer aus (1) eine
     bekannt verdrahtungslose Datei ist (existiert, laeuft aber nie von
     selbst). Das ist die Haelfte von Bedingung 2 unten, die eine reine
     Fundstelle nicht zeigen kann.

DREI BEDINGUNGEN AUS DEM KNOTEN, technisch umgesetzt:

  BELEGPFLICHT: jeder Treffer traegt seine Fundstelle woertlich (Datei:Zeile
  bzw. Knoten-/Lehren-ID) UND den Original-Ausschnitt (Docstring-Erstzeile
  bzw. Summary) -- nie eine eigene Paraphrase. Ein Kanal ohne Treffer wird
  ausdruecklich als "keine Treffer" gefuehrt, nie einfach weggelassen --
  ein schweigendes Werkzeug ist von einem kaputten sonst nicht zu
  unterscheiden.

  "EXISTIERT" IST NICHT "PASST": das Skript entscheidet den Abgleich gegen
  die Absicht NICHT selbst (das waere geraten) -- es liefert den O-Ton, an
  dem ein Mensch (oder die aufrufende Sitzung) das selbst sieht, plus die
  Ausloeserlos-Warnung aus (3) als einzige automatisierbare Teilaussage
  darueber, ob ein Fund heute WIRKT.

  DER VORSCHLAG ENTSCHEIDET NICHT: die Ausgabe ist eine sortierte Fundliste
  oder ein ausdruecklicher Nullbefund mit dem abgesuchten Raum -- nie ein
  "bau/baue nicht".

WARUM KEIN EIGENER STICHWORTFILTER: eine gepflegte Stoppwortliste veraltet
(siehe symbolindex.py-Kopf zur selben Frage bei Synonymen). Die hier
verwendete ist bewusst kurz und nur fuer die deutsche Alltagsfrageform
("ich haette gerne einen X") gedacht, nicht fuer Fachtext.

Aufruf:
    python3 kern/bauvermeidung.py "ich haette gerne einen Kalender"
    python3 kern/bauvermeidung.py --json "..."
    python3 kern/bauvermeidung.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_W = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_W), str(_W / "kern"), str(_W / "melder"),
                str(_W / "haken")]

_HUB_SCRIPTS = Path("/Volumes/daten/Begod2026/hub/scripts")
sys.path.insert(0, str(_HUB_SCRIPTS))

import symbolindex  # noqa: E402 -- hub/scripts, GANZER Verbund
import knowledge_mcp_server as kms  # noqa: E402 -- nur Lesefunktionen aufgerufen

AUSLOESERLOS = _W / "melder" / "ausloeserlos.py"

# Fuellwoerter der deutschen Alltagsfrage "ich haette gerne einen X, der Y
# macht" -- keine Fachbegriffe, die veralten koennten (siehe Docstring).
_FUELLWOERTER = {
    "ich", "du", "er", "sie", "es", "wir", "ihr", "mein", "meine", "meinen",
    "haette", "hätte", "gerne", "gern", "moechte", "möchte", "will", "wuerde",
    "würde", "brauche", "braeuchte", "bräuchte", "soll", "sollte", "kann",
    "koennte", "könnte", "einen", "eine", "ein", "der", "die", "das", "dass",
    "und", "oder", "fuer", "für", "mit", "von", "zu", "im", "in", "am", "an",
    "auf", "bei", "um", "wie", "was", "wo", "nach", "ist", "sind", "war",
    "waren", "wird", "werden", "etwas", "so", "auch", "noch", "mal", "bitte",
    "einem", "einer", "dem", "den", "des",
}


def _suchbegriffe(absicht: str) -> list[str]:
    """Alltagssatz -> Kandidaten fuer symbolindex.search (ODER-verknuepft).
    Kurze Fuellwoerter raus, Rest auf drei Zeichen Mindestlaenge (FTS5-
    Trigram/Wort-Suche greift darunter kaum sinnvoll)."""
    worte = re.findall(r"[A-Za-zÄÖÜäöüß]+", absicht.lower())
    begriffe = []
    for w in worte:
        if w in _FUELLWOERTER or len(w) < 4:
            continue
        if w not in begriffe:
            begriffe.append(w)
    return begriffe or worte  # leerer Rest waere schlimmer als Fuellwoerter


def _code_treffer(begriffe: list[str], je_begriff: int = 8) -> list[dict]:
    """Je Suchbegriff EIN eigener Aufruf, nicht ein gemeinsames OR.

    ROT VOR GRUEN, selbst erlebt beim Bau dieser Datei: Ein gemeinsames
    OR-Query ueber alle Woerter der Absicht rangiert per BM25 ueber den
    GESAMTEN Verbund -- ein seltener Treffer (3 Dateien fuer
    "vertrauensliste") ging im Rang unter, sobald ein haeufiges Wort aus
    demselben Satz ("zwischen", in tausenden Testnamen) mit in dieselbe
    Anfrage kam. Getrennte Anfragen je Begriff koennen sich nicht
    gegenseitig verdraengen -- jedes Wort bekommt sein eigenes Zeitfenster."""
    treffer = []
    gesehen = set()
    for begriff in begriffe:
        for r in symbolindex.search([begriff], limit=je_begriff):
            schluessel = (r["root"], r["path"], r["line"])
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            treffer.append({
                "kanal": "code",
                "fundstelle": f"{r['root']}/{r['path']}:{r['line']}",
                "was": f"{r['kind']} {r['name']}",
                "beleg_text": r["doc"] or r["signature"],
                "traf_bei": begriff,
            })
    return treffer


def _wissen_treffer(absicht: str, max_results: int = 8) -> list[dict]:
    erg = kms.knowledge_search(absicht, scope="all", max_results=max_results)
    treffer = []
    for r in erg.get("results", []):
        treffer.append({
            "kanal": "wissen",
            "fundstelle": r.get("id") or r.get("node_path") or r.get("path"),
            "was": r.get("title") or r.get("type") or r.get("kind"),
            "beleg_text": r.get("summary") or r.get("description"),
        })
    return treffer


def _ausloeserlos_dateien() -> set[str]:
    """Ruft melder/ausloeserlos.py als Unterprozess -- eigene Bauform
    (Punkt 3 im Kopf), keine Neuimplementierung. Scheitert der Aufruf
    (z.B. Datei fehlt), wird das als leere Menge behandelt und im Ergebnis
    vermerkt statt den ganzen Lauf abzubrechen -- ein Hinweiskanal darf
    nicht den Hauptbefund mitreissen."""
    if not AUSLOESERLOS.exists():
        return set()
    try:
        out = subprocess.run(
            [sys.executable, str(AUSLOESERLOS), "--bericht"],
            capture_output=True, text=True, timeout=30, cwd=str(_W),
        ).stdout
    except Exception:
        return set()
    return {zeile.strip().lstrip("- ") for zeile in out.splitlines()
            if zeile.strip().startswith("-")}


def pruefe(absicht: str) -> dict:
    begriffe = _suchbegriffe(absicht)
    code = _code_treffer(begriffe)
    wissen = _wissen_treffer(absicht)

    ohne_ausloeser = _ausloeserlos_dateien()
    for t in code:
        pfad = t["fundstelle"].split(":")[0]
        for kandidat in ohne_ausloeser:
            if pfad.endswith(kandidat):
                t["warnung"] = ("melder/ausloeserlos.py: diese Datei hat "
                                "keinen bekannten Ausloeser -- existiert, "
                                "laeuft aber nicht von selbst")
                break

    treffer = code + wissen
    ergebnis = {
        "absicht": absicht,
        "suchbegriffe": begriffe,
        "abgesuchter_raum": [
            "hub/scripts/symbolindex.py (Code-Taetigkeit, ganzer Verbund)",
            "knowledge_mcp_server.knowledge_search (Wissensknoten + Lehren, "
            "scope=all)",
        ],
        "treffer": treffer,
        "urteil": None,
    }
    if treffer:
        ergebnis["urteil"] = (
            f"{len(treffer)} Fundstelle(n) -- Empfehlung, kein Veto: erst "
            "pruefen (siehe beleg_text je Treffer), ob es zur Absicht passt, "
            "bevor neu gebaut wird."
        )
    else:
        ergebnis["urteil"] = "NULLBEFUND -- im abgesuchten Raum nichts gefunden."
    return ergebnis


def _selftest() -> None:
    # Positivkontrolle: symbolindex muss die Vertrauensliste der Foederation
    # finden (L-39574b, melder/foederation.py::vertraue()) -- real existierend.
    erg = pruefe("ich haette gerne eine Vertrauensliste zwischen Instanzen")
    fundstellen = " ".join(t["fundstelle"] for t in erg["treffer"])
    assert "foederation.py" in fundstellen, (
        "Positivkontrolle B5.2 (foederation.py) nicht gefunden -- "
        f"Treffer {erg['treffer']}"
    )

    # Negativkontrolle: eine erfundene, garantiert nicht vorhandene Absicht
    # darf keinen Codetreffer erzeugen.
    erg = pruefe("ich haette gerne einen Quantenchip-Zeitreise-Uebersetzer-Flansch")
    code_treffer = [t for t in erg["treffer"] if t["kanal"] == "code"]
    assert not code_treffer, f"Negativkontrolle erzeugte Codetreffer: {code_treffer}"

    print("selbsttest: alle Zusicherungen halten")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("absicht", nargs="?", help="Absicht in Alltagssprache")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return 0
    if not a.absicht:
        p.print_help()
        return 1

    erg = pruefe(a.absicht)
    if a.json:
        print(json.dumps(erg, ensure_ascii=False, indent=2))
    else:
        print(f"Absicht: {erg['absicht']}")
        print(f"Suchbegriffe: {', '.join(erg['suchbegriffe'])}")
        if not erg["treffer"]:
            print("NULLBEFUND -- abgesuchter Raum:")
            for r in erg["abgesuchter_raum"]:
                print(f"  - {r}")
        for t in erg["treffer"]:
            print(f"[{t['kanal']}] {t['fundstelle']}")
            print(f"    {t['was']}: {t['beleg_text']}")
            if "warnung" in t:
                print(f"    WARNUNG: {t['warnung']}")
        print(erg["urteil"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
