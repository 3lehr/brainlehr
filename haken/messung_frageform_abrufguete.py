"""Aufgabe 75 (Linie B) -- Vermutung pruefen, nicht bestaetigen: Bekommen
W-Fragen ('wer/wann/wo/warum/wieso/wie/was/welche...' oder Satz endet auf
'?') schlechtere Abruftreffer als Auftraege, oder ist die eigentliche
Ursache die fehlende Adresse (Pfad/Kennung) in der Nachricht -- und
Frageform nur ein Merkmal, das mit fehlender Adresse zusammenfaellt?

Zwei unabhaengige Messungen, beide read-only, keine Datei ausserhalb
haken/ und tests/ veraendert:

1) Struktur an echten Nutzernachrichten (auftraege.jsonl, 1986 Zeilen):
   Anteil mit Pfad-Erwaehnung und Anteil mit Kennung-Erwaehnung, getrennt
   nach Frageform vs. Nicht-Frageform. Prueft den im Auftrag genannten
   Hintergrund (0,9 %/1,5 % vs. 18,6 %/15,2 %) an dieser Sitzung nach,
   mit eigener (einfacherer) Pfad/Kennung-Heuristik -- Zahlen koennen
   deshalb abweichen, das Muster ist die Aussage, nicht die Nachkommastelle.

2) Trefferguete am Pruefkorpus (runs/pruefkorpus.jsonl, 45 Faelle, 35
   loesbar/10 negativ, Ground Truth vorhanden): Zustand C ("beide_an",
   produktionsnah) ueber kern/messlauf_abrufguete.run_case()/target_hit()
   wiederverwendet (nur Import/Aufruf, keine Datei in kern/ veraendert),
   getrennt nach Frageform vs. Nicht-Frageform.

Ausfuehren: python3 haken/messung_frageform_abrufguete.py
Ergebnis: haken/messung_frageform_abrufguete_<datum>.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_W = Path(__file__).resolve().parent.parent
while not (_W / "schema.sql").exists() and _W != _W.parent:
    _W = _W.parent
sys.path[:0] = [str(_W)] + [str(_W / o) for o in ("kern", "haken")]

AUFTRAEGE = _W / "auftraege.jsonl"
KORPUS = _W / "runs" / "pruefkorpus.jsonl"

QWORTE = (
    "wer", "wen", "wem", "wessen", "wie", "was", "wann", "wo", "warum",
    "wieso", "weshalb", "wozu", "woran", "worin", "wodurch", "wohin",
    "woher", "welcher", "welche", "welches",
)
_ERSTES_WORT_RE = re.compile(r"[a-zäöüß]+", re.I)
# Pfad: absolut (/a/b) ODER relativ mit Trenner (a/b, kern/domaene.py) ODER
# eine blosse Datei mit Endung (schema.sql) -- alle drei kommen in echten
# Auftraegen vor ('siehe kern/domaene.py', 'schema.sql anpassen').
PFAD_RE = re.compile(
    r"(?<![\w./])/?[a-z0-9_][a-z0-9_\-]*(?:/[a-z0-9_][a-z0-9_\-]*)+(?:\.[a-z0-9]{1,5})?"
    r"|\b[a-z0-9_\-]+\.(?:py|sql|md|json|jsonl|js|ts|tsx|dart|swift|yaml|yml|toml|sh)\b",
    re.I,
)
KENNUNG_RE = re.compile(r"\bL-[0-9a-f]{6}\b|`[0-9a-f]{8}`|\b[0-9a-f]{8}\b(?=[`'\"\s.,)]|$)", re.I)


def ist_frage(text: str) -> bool:
    """Grenzwerte, die die Abnahme verlangt: Frage ohne Fragewort (endet
    nur auf '?'), Auftrag mit Fragezeichen irgendwo im Fliesstext (zaehlt
    hier NICHT als Frage -- nur das Satzende oder das erste Wort
    entscheiden, sonst waere jeder Auftrag mit einer rhetorischen
    Zwischenfrage eine 'Frage'), gemischte Form (erstes Wort ist W-Wort,
    Rest ein Auftrag -- zaehlt als Frage, das erste Wort ist die Anrede an
    den Abruf), sehr kurze Frage ('Wieso?') -- deckt der erste Zweig ab."""
    t = text.strip()
    if not t:
        return False
    letzte_zeile = t.splitlines()[-1].strip()
    if letzte_zeile.endswith("?"):
        return True
    m = _ERSTES_WORT_RE.match(t)
    return bool(m) and m.group(0).lower() in QWORTE


def nennt_pfad(text: str) -> bool:
    return bool(PFAD_RE.search(text))


def nennt_kennung(text: str) -> bool:
    return bool(KENNUNG_RE.search(text))


def messung_struktur() -> dict:
    zeilen = [json.loads(l) for l in open(AUFTRAEGE, encoding="utf-8") if l.strip()]
    eindeutig = {}
    for z in zeilen:
        t = z.get("text", "")
        if t:
            eindeutig[t] = True
    texte = list(eindeutig.keys())

    gruppen = {"frage": [], "auftrag": []}
    for t in texte:
        gruppen["frage" if ist_frage(t) else "auftrag"].append(t)

    out = {"gesamt_zeilen": len(zeilen), "eindeutige_texte": len(texte)}
    for name, ts in gruppen.items():
        n = len(ts)
        pfad = sum(nennt_pfad(t) for t in ts)
        kennung = sum(nennt_kennung(t) for t in ts)
        out[name] = {
            "n": n,
            "anteil_an_eindeutigen": round(n / len(texte), 4) if texte else None,
            "pfad_prozent": round(100 * pfad / n, 1) if n else None,
            "kennung_prozent": round(100 * kennung / n, 1) if n else None,
        }
    return out


def messung_trefferguete() -> dict:
    import messlauf_abrufguete as msl  # noqa: E402 -- nur Import/Aufruf

    cases = msl.load_cases()
    solvable = [c for c in cases if c["category"] != "negative"]

    gruppen = {"frage": [], "auftrag": []}
    for c in solvable:
        gruppen["frage" if ist_frage(c["task"]) else "auftrag"].append(c)

    out = {}
    with msl._with_state(msl.STATES["C_beide_an"]):
        for name, cs in gruppen.items():
            treffer = 0
            for c in cs:
                nodes, lessons = msl.run_case(c)
                if msl.target_hit(c, nodes, lessons):
                    treffer += 1
            out[name] = {"n": len(cs), "treffer": treffer,
                         "trefferguete_prozent": round(100 * treffer / len(cs), 1) if cs else None}
    return out


def demo() -> None:
    """Selbsttest der Klassifikation -- Grenzwerte aus der Abnahme."""
    assert ist_frage("Wieso?") is True
    assert ist_frage("Warum laeuft das nicht?") is True
    assert ist_frage("Bau mir das. Warum eigentlich nicht gleich so?") is True
    assert ist_frage("Baue X, pruefe ob Y? Danach committen.") is False
    assert ist_frage("Wer hat das requested? Fixe es.") is True  # erstes Wort entscheidet mit
    assert ist_frage("Fixe den Fehler in kern/domaene.py") is False
    assert ist_frage("") is False
    assert nennt_pfad("siehe kern/domaene.py und /brainlehr/foo-bar") is True
    assert nennt_pfad("schema.sql anpassen") is True
    assert nennt_pfad("kein Pfad hier") is False
    assert nennt_kennung("Knoten 1a2b3c4d oder L-a9ccd0") is True
    assert nennt_kennung("nichts davon") is False
    print("demo: alle Selbsttests bestanden")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
        sys.exit(0)

    demo()
    befund = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "aufgabe": 75,
        "struktur_auftraege_jsonl": messung_struktur(),
        "trefferguete_pruefkorpus_zustand_C": messung_trefferguete(),
    }
    print(json.dumps(befund, ensure_ascii=False, indent=2))
    out_path = Path(__file__).parent / f"messung_frageform_abrufguete_{datetime.now().date()}.json"
    out_path.write_text(json.dumps(befund, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {out_path}")
