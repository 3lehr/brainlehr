#!/usr/bin/env python3
"""Richter mit Soll-Antwort -- Erweiterung von okkultation.py um die
Betreiberidee vom 2026-08-15: "Ein Subagent spawnt einen anderen. Der erste
kennt das Wissen, der zweite nicht. Der erste kann dann pruefen."

WOZU: okkultation.py entscheidet M1 (Zielaufgaben) mechanisch ueber
_ziel_treffer(), weil dort eine Ziel-Kennung feststeht. Fuer M2 (echte Fragen
OHNE Ziel) gibt es keine Kennung zum Abgleichen -- nur ein Textvergleich
(_wesentlich_unterschiedlich), der Unterschied misst, nicht Richtigkeit. Der
Richter schliesst genau diese Luecke: ein informierter Agent liest die Frage
UND den echten Wissens-Block und schreibt VORHER fest, an welchen
beobachtbaren Tatsachen sich eine informierte Antwort erkennen liesse --
danach erst sieht irgendjemand (Mensch oder Code) die uninformierte Antwort.

DIE ZWEI RISIKEN UND WIE HIER DAGEGEN GEBAUT WURDE (Auftragstext):

Risiko 1 (Leck): Der informierte Agent koennte den Auftragstext fuer den
uninformierten Agenten formulieren und dabei die Antwort hineinschreiben.
GEGENMASSNAHME, STRUKTURELL statt durch Ermahnung: Der informierte Agent
bekommt hier NIE die Aufgabe, einen Prompt fuer den uninformierten Agenten zu
schreiben. Die Prompts (OHNE/MIT/NEG/WERKZEUG) entstehen ausschliesslich in
okkultation.aufgaben_erzeugen() -- reiner Code, kein Modellaufruf, seit dem
Vorlaeufer vom 2026-08-12 so gebaut. Der informierte Agent schreibt
AUSSCHLIESSLICH Richter-Kriterien (RICHTER_KRITERIEN_AUFTRAG unten), niemals
Prompttext, niemals eine eigene Antwort auf die Frage. Als Netz DARUNTER (fuer
den Fall, dass jemand diese Trennung spaeter aufweicht) gibt es zusaetzlich
leck_pruefung_kriterien(): sie prueft KRITERIENTEXT mechanisch auf woertlich
enthaltene Ziel-Kennungen -- s. Beleg in _selftest() (ein absichtlich
leckendes Kriterium wird erkannt und verworfen).

Risiko 2 (Voreingenommenheit): Ein Richter, der die Zielantwort kennt, koennte
zu ihr hin bewerten. GEGENMASSNAHME: kriterien_pruefen() ist KEIN Modellaufruf,
sondern reiner Text-Abgleich (Substring, wie ok._ziel_treffer). Ein
mechanischer Pruefer hat keinen Begriff von "das ist die MIT-Antwort" -- er
bekommt nur Kriterienliste + Antworttext, in dieser Reihenfolge, ohne Label.
Die Voreingenommenheitsprobe aus dem Auftrag ("beide Ausgaben blind bewerten")
ist damit dem Konstrukt nach erledigt, nicht nur ausgefuehrt: blindheitsnachweis()
zeigt zusaetzlich MECHANISCH, dass das Ergebnis unveraendert bleibt, wenn die
Bedingungs-Labels vor der Pruefung vertauscht werden -- ein Beweis, keine
Behauptung. Was das NICHT prueft: ob der informierte Agent die KRITERIEN
selbst schon in Richtung "was im Block steht" waehlt (Bestaetigungsfehler bei
der Kriterienerstellung, nicht bei der Pruefung) -- dagegen hilft nur, dass
Kriterien FAKTEN aus dem Wissen sind (Zahlen, Namen, Entscheidungen), die
unabhaengig davon gelten, ob die uninformierte Antwort sie zufaellig auch
nennt oder nicht.

DREITEILUNG (nicht hier, sondern okkultation.dreiteilung_erreichbarkeit()):
die vierte Bedingung WERKZEUG fuer M1 gehoert dorthin, weil sie mechanisch
ueber _ziel_treffer ausgewertet wird wie MIT/OHNE/NEG -- kein Richter noetig,
dort ist die Ziel-Kennung ja bekannt.

DREITEILUNG DER SCHRITTE (wie okkultation.py, gleiches Muster):
  1. hier: kriterien_pruefen()/leck_pruefung_kriterien() -- reiner Code
  2. Hauptfaden: EIN informierter Agent schreibt Kriterien (vor jeder
     uninformierten Antwort), separate uninformierte Agenten beantworten
     OHNE/MIT/NEG blind -- ein Python-Skript kann keinen Subagenten starten
     (L-a69129), das ist Orchestrator-Arbeit.
  3. hier: auswerten_richter() -- reiner Code, kein Modellaufruf.

Aufruf: python3 okkultation_richter.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import okkultation as ok  # noqa: E402 -- leck_pruefung() wiederverwendet

WURZEL = _w

# Vorlage fuer den Auftrag an den INFORMIERTEN Agenten (Orchestrator-Auftrag,
# kein Python-Aufruf -- s. Modulkopf, L-a69129). Wird woertlich verwendet,
# damit die Trennung "nur Kriterien, nie Prompttext/Antwort" nachpruefbar an
# EINER Stelle steht, nicht in jedem einzelnen Agentenauftrag neu formuliert.
RICHTER_KRITERIEN_AUFTRAG = (
    "Du bekommst eine Frage und einen Wissens-Block (<knowledge-recall>), "
    "der einem anderen Agenten zu dieser Frage vorgelegt wuerde. Ein "
    "GETRENNTER, uninformierter Agent wird dieselbe Frage GLEICH DANACH "
    "beantworten -- mal mit diesem Block, mal ohne, mal mit einem "
    "themenfremden Block. Deine Aufgabe ist NICHT, die Frage zu "
    "beantworten. Deine Aufgabe ist ausschliesslich: schreibe 2 bis 4 "
    "beobachtbare, mechanisch pruefbare Kriterien, an denen erkennbar "
    "waere, dass eine Antwort dieses Wissen tatsaechlich genutzt hat -- "
    "konkrete Fakten (Zahlen, Namen, Entscheidungen, Kennungen) aus dem "
    "Block, NICHT 'ist die Antwort gut' oder aehnliche Werturteile. Gib "
    "NUR eine JSON-Liste zurueck, Format: "
    '[{"text": "kurze Beschreibung des Kriteriums", '
    '"muster": ["woertliches Suchmuster 1", "Muster 2"]}, ...]. '
    "'muster' sind die exakten Woerter/Zahlen, nach denen mechanisch (nicht "
    "durch dich) in der spaeteren Antwort gesucht wird. Schreibe KEINEN "
    "Fliesstext, keine eigene Antwort, keinen Auftragstext fuer den "
    "anderen Agenten.")


# ------------------------------------------------------------ mechanisch
def leck_pruefung_kriterien(kriterien: list[dict], ziele: list[dict]) -> tuple[bool, list[dict]]:
    """Netz UNTER der strukturellen Trennung (s. Modulkopf): prueft jeden
    Kriterientext + jedes Suchmuster auf woertlich enthaltene Ziel-Kennungen.
    Ein Kriterium wie 'nenne /brainlehr/foo' waere kein beobachtbares Faktum
    mehr, sondern ein Abschreib-Hinweis -- muss verworfen werden."""
    befunde = []
    for k in kriterien:
        text = k.get("text", "") + " " + " ".join(k.get("muster", []))
        leckt, ids = ok.leck_pruefung(text, ziele)
        if leckt:
            befunde.append({"kriterium": k, "betroffene_ziele": ids})
    return (bool(befunde), befunde)


def kriterien_pruefen(kriterien: list[dict], antwort: str) -> dict:
    """Mechanischer Richter (Risiko 2, s. Modulkopf): kein Modellaufruf,
    reiner Substring-Abgleich (case-insensitive). Je Kriterium: erfuellt,
    wenn IRGENDEIN Muster im Antworttext vorkommt."""
    text = (antwort or "").lower()
    ergebnisse = []
    for k in kriterien:
        muster = k.get("muster", [])
        treffer = [m for m in muster if m.lower() in text]
        ergebnisse.append({"text": k.get("text", ""), "erfuellt": bool(treffer),
                            "treffer_muster": treffer})
    n = len(ergebnisse)
    erfuellt = sum(1 for e in ergebnisse if e["erfuellt"])
    return {"kriterien": ergebnisse, "erfuellt": erfuellt, "n": n,
            "anteil": (erfuellt / n) if n else None}


def richten(kriterien: list[dict], antworten: dict[str, str]) -> dict:
    """Wendet kriterien_pruefen() auf mehrere gelabelte Antworten an (z.B.
    {'MIT': ..., 'OHNE': ..., 'NEG': ...}). Das Label spielt in der Pruefung
    selbst keine Rolle -- kriterien_pruefen() sieht nur den Text -- es dient
    hier nur der Zuordnung im Ergebnis."""
    return {cond: kriterien_pruefen(kriterien, text) for cond, text in antworten.items()}


def blindheitsnachweis(kriterien: list[dict], antworten: dict[str, str]) -> dict:
    """Beleg statt Behauptung fuer die Voreingenommenheitsprobe (Risiko 2):
    vertauscht die Labels VOR der Pruefung (der mechanische Richter bekommt
    also unter neutralen Namen 'x0', 'x1', ... genau dieselben Texte in
    anderer Reihenfolge) und zeigt, dass jeder Text -- unabhaengig vom Label,
    unter dem er geprueft wird -- dieselbe Quote erhaelt. Ein Richter, der
    Labels *nicht liest* (wie hier), kann per Konstruktion nicht zugunsten
    eines Labels urteilen; das hier ist der mechanische Nachweis dafuer,
    nicht nur die Konstruktions-Behauptung."""
    namen = sorted(antworten.keys())
    verblindet = {f"x{i}": antworten[name] for i, name in enumerate(namen)}
    normal = richten(kriterien, antworten)
    blind = richten(kriterien, verblindet)
    abweichungen = []
    for i, name in enumerate(namen):
        a = normal[name]["anteil"]
        b = blind[f"x{i}"]["anteil"]
        if a != b:
            abweichungen.append({"label": name, "anteil_normal": a, "anteil_blind": b})
    return {"stimmt_ueberein": not abweichungen, "abweichungen": abweichungen,
            "hinweis": "identische Quote mit und ohne Label -- der mechanische "
                       "Richter kann Labels nicht sehen, also auch nicht "
                       "bevorzugen. Was das NICHT prueft: Bestaetigungsfehler "
                       "bei der KRITERIEN-Erstellung durch den informierten "
                       "Agenten selbst (s. Modulkopf)."}


# --------------------------------------------------------------- Schritt 3
def auswerten_richter(kriterien: list[dict], antworten: dict[str, dict]) -> dict:
    """Schritt 3: wendet kriterien_pruefen() auf die vom Hauptfaden
    gesammelten M2-Antworten an (Format wie okkultation._antwort_lesen:
    dict mit 'antwort'+'werkzeuge_benutzt', oder Altformat-String -- Altformat
    wird wie dort fail-closed behandelt: werkzeuge_benutzt unbekannt ->
    ausgeschlossen)."""
    ausgewertet = {}
    ausgeschlossen = []
    texte = {}
    for cond, eintrag in antworten.items():
        antwort, ausg = ok._antwort_lesen(eintrag)
        if ausg:
            ausgeschlossen.append(cond)
            continue
        texte[cond] = antwort
    urteile = richten(kriterien, texte)
    for cond, urteil in urteile.items():
        ausgewertet[cond] = urteil
    return {
        "kriterien": kriterien,
        "urteile": ausgewertet,
        "werkzeug_ausgeschlossen": ausgeschlossen,
        "blindheitsnachweis": blindheitsnachweis(kriterien, texte) if len(texte) > 1 else None,
    }


# ---------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auswerten", nargs=2, metavar=("KRITERIEN", "ANTWORTEN"),
                     help="Schritt 3: Kriterien auf gesammelte Antworten anwenden")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.auswerten:
        kriterien = json.loads(Path(args.auswerten[0]).read_text(encoding="utf-8"))
        antworten = json.loads(Path(args.auswerten[1]).read_text(encoding="utf-8"))
        ergebnis = auswerten_richter(kriterien, antworten.get("antworten", antworten))
        out = Path(args.out or (WURZEL / "runs" / "okkultation_richter_ergebnis.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
        for cond, urteil in ergebnis["urteile"].items():
            print(f"{cond}: {urteil['erfuellt']}/{urteil['n']}")
        print(f"Geschrieben: {out}")
        return

    ap.print_help()


# ------------------------------------------------------------------- Tests
def _selftest() -> None:
    """Rot-vor-gruen, ohne Netz/Modellaufruf: mechanische Pruefung, Leck,
    Blindheitsnachweis."""
    kriterien = [
        {"text": "nennt die Schwelle 0,65", "muster": ["0,65", "0.65"]},
        {"text": "nennt den Knoten /brainlehr/schwelle", "muster": ["/brainlehr/schwelle"]},
    ]

    # kriterien_pruefen: positiv, negativ, teilweise.
    voll = kriterien_pruefen(kriterien, "Die Schwelle liegt bei 0,65, siehe /brainlehr/schwelle.")
    assert voll["erfuellt"] == 2 and voll["n"] == 2 and voll["anteil"] == 1.0
    leer = kriterien_pruefen(kriterien, "Ich habe dazu keine Information.")
    assert leer["erfuellt"] == 0
    teil = kriterien_pruefen(kriterien, "Ich vermute 0,65, mehr weiss ich nicht.")
    assert teil["erfuellt"] == 1

    # Leckpruefung: Beleg, dass sie ein absichtlich leckendes Kriterium
    # ERKENNT UND VERWIRFT (Auftrag: "mit Beleg, dass sie wirkt").
    leckendes_kriterium = [{"text": "nenne die Kennung /brainlehr/geheimziel",
                             "muster": ["/brainlehr/geheimziel"]}]
    ziele = [{"id": "/brainlehr/geheimziel"}]
    leckt, befunde = leck_pruefung_kriterien(leckendes_kriterium, ziele)
    assert leckt is True and len(befunde) == 1
    # Nach dem Verwerfen (Simulation: Kriterium entfernt) bleibt kein Leck.
    bereinigt = [k for k in leckendes_kriterium
                 if not ok.leck_pruefung(k["text"] + " " + " ".join(k["muster"]), ziele)[0]]
    assert bereinigt == []
    leckt2, _ = leck_pruefung_kriterien(bereinigt, ziele)
    assert leckt2 is False
    # Negativfall: ein sauberes Kriterium leckt nicht.
    sauberes_kriterium = [{"text": "nennt die Reihenfolge der Schritte", "muster": ["zuerst", "danach"]}]
    leckt3, _ = leck_pruefung_kriterien(sauberes_kriterium, ziele)
    assert leckt3 is False

    # Blindheitsnachweis: identische Quote mit vertauschten Labels.
    antworten = {
        "MIT": "Die Schwelle liegt bei 0,65, siehe /brainlehr/schwelle.",
        "OHNE": "Ich habe dazu keine Information.",
        "NEG": "Space Shuttle Program, Orbiter, Avionics.",
    }
    bn = blindheitsnachweis(kriterien, antworten)
    assert bn["stimmt_ueberein"] is True and bn["abweichungen"] == []

    # auswerten_richter(): Werkzeug-Ausschluss wie in okkultation.py, plus
    # Blindheitsnachweis wird mitgefuehrt.
    erg = auswerten_richter(kriterien, {
        "MIT": {"antwort": antworten["MIT"], "werkzeuge_benutzt": False},
        "OHNE": {"antwort": antworten["OHNE"], "werkzeuge_benutzt": False},
        "NEG": "nackter String ohne Feld",  # Altformat -> ausgeschlossen
    })
    assert erg["urteile"]["MIT"]["erfuellt"] == 2
    assert erg["urteile"]["OHNE"]["erfuellt"] == 0
    assert "NEG" in erg["werkzeug_ausgeschlossen"]
    assert erg["blindheitsnachweis"]["stimmt_ueberein"] is True

    print("selftest ok: kriterien_pruefen() (voll/leer/teilweise), "
          "leck_pruefung_kriterien() (Leck erkannt+verworfen, Negativfall), "
          "blindheitsnachweis() (Labeltausch ohne Aenderung), "
          "auswerten_richter() (Werkzeug-Ausschluss)", file=_sys.stderr)


if __name__ == "__main__":
    main()
