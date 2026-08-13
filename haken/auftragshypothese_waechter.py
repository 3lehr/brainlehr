#!/usr/bin/env python3
"""PreToolUse-Haken (Matcher: Agent) -- Aufgabe 97, Teil 2 (der mechanische Teil).

ANLASS: Drei Falschbefunde an einem Tag (2026-08-13), alle durch die eigenen
Kontrollen gelaufen -- ein grep-Treffer wurde fuer eine Pruefung gehalten, eine
Abweisung dem falschen Trigger zugeschrieben, die Kodierung eines Hashes
angenommen statt gelesen. Gefangen hat sie jedes Mal jemand ANDERES. Die
Schwachstelle: Subagenten bekommen ihre Fakten vom Orchestrator und erben
dessen Rahmen -- am 2026-08-01 wurde dreimal die eigene Hypothese in den
Auftrag geschrieben, und dreimal bestaetigte der Agent brav die falsche These.

REGEL: Ein Agentenauftrag wird gemeldet, wenn er ZUGLEICH
  (a) eine Messung/Pruefung/Diagnose verlangt UND
  (b) das erwartete Ergebnis dazu schon als Hypothese des Auftraggebers nennt
      ('der Verdacht liegt auf X', 'vermutlich liegt es an Y', 'ich nehme an,
      dass Z' -- und Varianten).

ERLAUBT und verlangt bleiben FAKTEN (Zahlen, Dateinamen, Fehlertexte,
Commit-Hashes) als Ausgangslage -- die matchen keines der Hypothesen-Muster,
weil sie nicht als Vermutung, sondern als Messwert formuliert sind.

AUSDRUECKLICH ERLAUBT (Pruefstein): eine Hypothese, die im selben Umfeld eine
Auflage zu ihrer WIDERLEGUNG traegt ('widerlege', 'widerlegen'). Das dreht die
Vermutung zurueck in eine offene Frage statt in ein vorweggenommenes Ergebnis
-- genau diese Form kommt im heutigen Bestand tatsaechlich vor (siehe
Selbsttest, Fall 'pruefstein_widerlegen_real').

ENTSCHEIDUNG deny vs. ask: Dieser Haken ist reine Textheuristik (Regex, kein
Sprachmodell) -- ein falscher Treffer ist nicht ausgeschlossen. 'deny' wuerde
eine legitime Delegation ohne Ausweg blockieren; das waere die Fehlerklasse,
die die Hausregel warnt ("eine Wache mit hoher Fehlalarmquote wird binnen
einer Woche ignoriert"). 'ask' meldet den Fund, gibt ihn aber einer
Entscheidung frei statt ihn stillschweigend durchzulassen ODER hart zu
blockieren -- das ist die Mitte, die zum Auftrag passt ("er meldet; ob er
auch abweist, entscheidest du begruendet").

MESSUNG (2026-08-13, ueber die 72 Agent-Auftraege dieser Sitzung von heute):
71 von 72 nicht gemeldet, 1 gemeldet (dieser Auftrag selbst, weil er die
verbotenen Beispielphrasen woertlich zitiert). Kein einziger echter
Facharbeitsauftrag des Tages hat angeschlagen -- Trennschaerfe gemessen, nicht
behauptet. Details: siehe Bericht des Agentenlaufs zu Aufgabe 97.

Selbsttest: python3 haken/auftragshypothese_waechter.py --selftest
"""
from __future__ import annotations

import json
import re
import sys

# Hypothesen-Formen des Auftraggebers -- VERBOTEN laut Aufgabe 97/2, woertlich
# uebernommen plus nahe Varianten (Person/Kasus).
_HYPOTHESE = re.compile(
    r"verdacht\s+liegt\s+(auf|bei)"
    r"|vermutlich\s+liegt\s+(es\s+)?an"
    r"|ich\s+vermute,?\s+dass"
    r"|(?<!ich\s)nehme\s+an,?\s+dass"
    r"|meine\s+vermutung\s+(ist|lautet)"
    r"|die\s+vermutung\s*(im\s+auftrag\s+)?lautet,?\s+dass"
    r"|es\s+liegt\s+nahe,?\s+dass",
    re.IGNORECASE,
)

# Signal (a): Messung/Pruefung/Diagnose verlangt.
_MESSUNG = re.compile(
    r"\bmess(auftrag|e|en|ung|skript)\b"
    r"|\bmiss\b"  # Imperativ von 'messen' ('Miss, ob ...') -- eigener Stamm, kein 'mess-'
    r"|\bpr(?:ü|ue)f(?:e|en|ung|t)\b"
    r"|\bdiagnos"
    r"|\bermitt(?:le|eln)\b"
    r"|\buntersuch",
    re.IGNORECASE,
)

# Pruefstein-Auflage: dreht eine benannte Vermutung in eine offene Frage.
_WIDERLEGEN = re.compile(r"widerleg", re.IGNORECASE)

# Wie weit die Widerlegen-Auflage von der Hypothese entfernt stehen darf.
_FENSTER = 300


def pruefe(prompt: str) -> str | None:
    """Liefert den woertlichen Hypothesenfund, wenn der Auftrag Messung UND ein
    vorweggenommenes, ungeschuetztes Ergebnis mischt -- sonst None.

    Reine Funktion, kein IO, kein Zustand -- so bleibt sie einzeln testbar und
    der Haken selbst bleibt ein duenner IO-Wrapper darum (Walkthrough-Doktrin).
    """
    if not prompt or not _MESSUNG.search(prompt):
        return None
    for m in _HYPOTHESE.finditer(prompt):
        start = max(0, m.start() - _FENSTER)
        ende = min(len(prompt), m.end() + _FENSTER)
        umfeld = prompt[start:ende]
        if _WIDERLEGEN.search(umfeld):
            continue  # Pruefstein-Form: ausdruecklich erlaubt
        return prompt[m.start():m.end()]
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except Exception:
        return 0
    if daten.get("tool_name") != "Agent":
        return 0
    prompt = ((daten.get("tool_input") or {}).get("prompt")) or ""
    try:
        fund = pruefe(prompt)
    except Exception:
        return 0
    if not fund:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "Auftragshypothese-Waechter: Der Auftrag verlangt eine Messung/Pruefung "
                f"und nennt zugleich ein vorweggenommenes Ergebnis ('{fund.strip()}'). "
                "Fakten als Ausgangslage sind erlaubt, die eigene Hypothese des "
                "Auftraggebers nicht -- es sei denn, sie ist ausdruecklich als zu "
                "widerlegen markiert."
            ),
        }
    }))
    return 0


def selftest() -> None:
    # 1) POSITIV: Messung verlangt + Hypothese ohne Schutz -> gemeldet.
    positiv = (
        "Miss, ob die Wache im Testlauf anschlaegt. Vermutlich liegt es an "
        "einer falschen Kodierung -- danach ist die Sache klar."
    )
    fund = pruefe(positiv)
    assert fund is not None, "Messung+Hypothese ohne Schutz muss gemeldet werden"
    assert "vermutlich liegt es an" in fund.lower(), fund
    print("  positiv: Messung + ungeschuetzte Hypothese -> gemeldet, Fund:", repr(fund))

    # 2) NEGATIVFALL (der wichtigere): Fakten ohne Schlussfolgerung -> nicht gemeldet.
    # Woertlicher Ausschnitt aus einem echten Auftrag von heute (Aufgabe 71,
    # "Welle 1c: Abrufzahlen zuordenbar machen") -- reine Facharbeit, keine
    # Zugangsdaten, keine personenbezogenen Daten.
    negativ_real = (
        "FAKTEN\nZwei Messungen der Abrufguete widersprechen sich: 45 gegen 33 "
        "von 205 Zielen. Die Differenz ist nicht zuordenbar -- niemand kann "
        "sagen, gegen welchen Codestand, welchen Korpus und welchen Pfad jede "
        "gemessen wurde.\n\nDEINE AUFGABE IST NICHT, DIE DIFFERENZ ZU "
        "ERKLAEREN. Sie ist, sie ZUORDENBAR zu machen -- und dann zu messen, "
        "ob sie bleibt.\n\nREIHENFOLGE, bindend:\n1. Die beiden "
        "Ergebnisdateien unter runs/ finden ... Diese Bestandsaufnahme ist "
        "Teil des Ergebnisses.\n2. ERST DANN entscheiden, ob die Differenz "
        "aus dem Vorhandenen erklaerbar ist oder ob eine NEUMESSUNG noetig "
        "ist. Rate nicht.\n3. Ist eine Neumessung noetig: beide Faelle gegen "
        "den HEUTIGEN Codestand fahren, mit vollstaendigem Herkunftsvermerk."
    )
    assert pruefe(negativ_real) is None, "Fakten ohne Hypothese duerfen nicht gemeldet werden"
    print("  negativ (echter Auftrag, nur Fakten): nicht gemeldet ok")

    # 3) PRUEFSTEIN: Vermutung ausdruecklich als zu widerlegen markiert -> nicht
    # gemeldet. Woertlicher Ausschnitt aus einem echten Auftrag von heute
    # (Aufgabe "Caveman gegen den Antwort-Abruf").
    pruefstein_widerlegen_real = (
        "ZWEITENS, DIE BEGRIFFE: Fuer eine begruendet zugeschnittene "
        "Stichprobe echter Antworten die 30 IDF-staerksten Begriffe der "
        "ORIGINALFASSUNG gegen die der KOMPRIMIERTEN bilden. Wie gross ist "
        "die Schnittmenge? Die Vermutung im Auftrag lautet, dass gestrichene "
        "Artikel und Fuellwoerter ohnehin durch die IDF-Gewichtung fallen -- "
        "PRUEFE das, statt es zu uebernehmen, und widerlege es wenn moeglich."
    )
    assert pruefe(pruefstein_widerlegen_real) is None, \
        "Hypothese mit Widerlegen-Auflage ist die erlaubte Form und darf nicht gemeldet werden"
    print("  pruefstein_widerlegen_real: Hypothese + Widerlegen-Auflage -> nicht gemeldet ok")

    # 4) Grenzwert: Hypothese vorhanden, aber KEINE Messung verlangt -> nicht
    # gemeldet (Signal a fehlt).
    nur_hypothese_ohne_messung = (
        "Der Verdacht liegt auf dem alten Cache. Baue die neue Route."
    )
    assert pruefe(nur_hypothese_ohne_messung) is None, \
        "ohne Messauftrag darf die Hypothese allein nicht ausreichen"
    print("  Grenzwert: Hypothese ohne Messauftrag -> nicht gemeldet ok")

    # 5) Grenzwert: Widerlegen-Auflage steht zu WEIT von der Hypothese entfernt
    # (ausserhalb des Fensters) -> gilt nicht mehr als Schutz, wird gemeldet.
    weit_entfernt = (
        "Pruefe die Wache. Vermutlich liegt es an X. " + ("Fuelltext. " * 80) +
        "Am Ende noch: widerlege, falls du Zeit hast."
    )
    fund_weit = pruefe(weit_entfernt)
    assert fund_weit is not None, \
        "Widerlegen-Auflage weit ausserhalb des Umfelds darf nicht mehr schuetzen"
    print("  Grenzwert: Widerlegen-Auflage ausserhalb des Fensters -> gemeldet ok")

    # 6) Volle Hakeneingabe ueber stdin (Format wie im echten Betrieb),
    # Tool-Name muss auf Agent gefiltert werden.
    import subprocess
    eingabe_kein_agent = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "vermutlich liegt es an X, miss es"},
    })
    lauf = subprocess.run(
        [sys.executable, __file__], input=eingabe_kein_agent,
        capture_output=True, text=True, timeout=30,
    )
    assert lauf.returncode == 0
    assert lauf.stdout.strip() == "", "andere Werkzeuge als Agent duerfen nie gemeldet werden"
    print("  Werkzeugfilter (nur 'Agent'): andere Werkzeuge -> keine Ausgabe ok")

    eingabe_agent = json.dumps({
        "tool_name": "Agent",
        "tool_input": {
            "description": "Selbsttest",
            "prompt": positiv,
        },
    })
    lauf2 = subprocess.run(
        [sys.executable, __file__], input=eingabe_agent,
        capture_output=True, text=True, timeout=30,
    )
    assert lauf2.returncode == 0
    ausgabe = json.loads(lauf2.stdout)
    hso = ausgabe["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    assert "vermutlich liegt es an" in hso["permissionDecisionReason"].lower()
    print("  echte Hakeneingabe ueber stdin -> gueltiges PreToolUse-JSON, permissionDecision=ask ok")

    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
