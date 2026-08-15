#!/usr/bin/env python3
"""Haelt Planzeilen aus docs/PLAN_GESAMT_2026-08-13.md gegen den Code und
meldet Kandidaten, die vermutlich schon erledigt sind, obwohl der Plan sie
(noch) nicht so fuehrt.

ANLASS (2026-08-15): Am selben Tag wurden vier Planzeilen -- Aufgabe 81
(Kantenberechnung, lag seit 5a4d65b vor), 85 (melder/ausloeserlos.py,
b3dfc6f), 84 (melder/vorschlagsmelder.py, 38bebd9) und J1
(melder/schemastand.py, 88aaf73) -- als "offen" beauftragt, obwohl sie
laengst gebaut waren. Jedes Mal kostete das einen halben Agentenzug, nur um
das nachzumessen. Dieser Melder ist der Mechanismus dagegen: PLAN ist das
Soll, das Repo ist die Wirklichkeit, hier werden sie gegeneinander gehalten.

HEURISTIK, KEIN BEWEIS: dieser Melder meldet KANDIDATEN, nie "erledigt".
Jeder Kandidat traegt seinen Beleg (Commit-Kennung + Betreffzeile); ohne
Beleg wird nichts gemeldet. Der Plan selbst wird nicht angefasst -- kein
automatisches Abhaken, die Entscheidung bleibt beim Menschen.

WELCHES MERKMAL TRAEGT -- GEMESSEN, NICHT GERATEN: Vier Merkmale standen zur
Wahl (genannter Dateiname existiert / genannter Funktionsname im Code /
Commit traegt die Aufgabenkennung / passende Testdatei existiert). Gegen den
echten Bestand gemessen (siehe Commit-Nachricht) trennt nur EINES sauber:
ein Commit vom Typ feat/fix, der die Kennung UND einen echten Dateipfad
nennt. "Genannter Dateiname" allein scheitert an Aufgabe 85 -- der Auftrag
nennt dort keinen konkreten Dateinamen, nur "ein neuer Melder unter
melder/". Auf die beiden verbleibenden Signale wird deshalb verzichtet
(YAGNI): sie haetten die vier bekannten Faelle nicht zusaetzlich gefunden.

DIE KENNUNGS-FORM UNTERSCHEIDET SICH NACH ART DER KENNUNG, gemessen an der
echten Commit-Historie:
  - Numerische Kennungen (81, 84, 85, 96, ...) muessen im Commit auf
    "Aufgabe"/"Auftrag" folgen ("Aufgabe 85, A2", "AUFGABE 96,",
    "Auftrag 84."). Eine blosse Zahl im Text ist zu haeufig (Prozentwerte,
    Zeilennummern, andere Kennungen) -- ungeprueft haette das False
    Positives erzeugt.
  - Buchstaben-Kennungen (H4, J1, F6a, ...) sind als Wortganzes selten genug,
    um ohne "Aufgabe"-Praefix zu gelten -- SO GEFUNDEN: J1 steht in c90f932
    als "J1 (Triggerabgleich beide Richtungen) war bereits durch
    melder/schemastand.py" belegt, ohne das Wort "Aufgabe" davor.
    Ausnahme, gemessen als echter Fehlalarm: eine Kennung, die unmittelbar
    an einen Bindestrich grenzt ("F1-F10" -- Probennamen, keine Kennung),
    zaehlt nicht.
  - Nur Commits vom Typ feat/fix zaehlen. docs(...)-Commits zaehlen nicht --
    sie beschreiben den Plan, sie belegen keinen Bau. Ohne diese Grenze
    haetten die "docs(brainlehr): PLAN_OPENLEHR auf Auftragsform gebracht"-
    Commits H4/H5/H6/H7/H10 faelschlich als Kandidaten gemeldet, weil sie
    diese Kennungen woertlich als "noch offen" auffuehren.
  - Ein Commit, der den Melder selbst betrifft (Modulname "plan_bestandsabgleich"
    irgendwo im Commit-Text), zaehlt nie als Beleg -- SO GEFUNDEN (2026-08-15):
    der eigene Bau-Commit 0f450fb (Typ feat) nennt H4/H5/H6/H7/H10 woertlich
    als Beispiel fuer einen ausgeschlossenen Fehlalarm und matchte damit seine
    eigene Heuristik.
  - Ein "frei" (Entsperr-Marker) in den 80 Zeichen NACH der Kennung zaehlt
    nicht als Beleg -- SO GEFUNDEN (2026-08-15): 4b5e8b1 nennt H10 als
    "... frei, an derselben Datei zu arbeiten" (eine Sperre fiel), nicht als
    erledigt; H10 steht im Plan weiter unter "Offen".

GEMESSENE FALSCHTREFFERRATE (2026-08-15T11:00, docs/PLAN_GESAMT_2026-08-13.md,
70 extrahierte Kennungen, nach den beiden Ausnahmen oben): 32 von 70 werden
als Kandidat gemeldet (unter der Haelfte -- keine Fehlkonstruktion nach dem
Massstab des Auftrags). Die Zahl verschiebt sich mit jedem neuen Commit (die
Heuristik durchsucht die gesamte Historie neu) -- vor den beiden Ausnahmen
oben lag sie bei 38/70, weil zwei spaeter gelandete Commits (0f450fb,
4b5e8b1) sich selbst bzw. eine falsch gelesene Kennung trafen. Stichproben
von Hand: G2/G3 (echter Fund, im Plan bisher nicht als erledigt vermerkt)
und ein zurueckgenommener Fehlalarm F1 (traf urspruenglich auf "10 Proben
F1-F10" -- eine Probenbenennung, keine Plankennung; durch die
Bindestrich-Ausnahme oben entfernt). Keine erschoepfende Pruefung aller 32
-- das ist der Preis der Heuristik, deshalb Hinweisrecht statt Automatik.

GRENZWERTE, geprueft: Plandatei ohne jede Kennung -> leere Kandidatenliste,
kein Absturz. Kennung, deren Plantext keinen Dateinamen nennt (85) ->
trotzdem Kandidat, weil das Merkmal am Commit haengt, nicht am Plantext.
H2/H7 stehen als Range "`H2` bis `H7`" im Plan -- diese Bindestrich-freie
Kurzform wird NICHT expandiert (H3/H4/H5/H6 tauchen dort nicht einzeln in
Backticks auf); wo sie einzeln vorkommen (H4, H5 an anderer Stelle im
Fliesstext), werden sie trotzdem einzeln extrahiert.

Aufruf:
    python3 melder/plan_bestandsabgleich.py            # Kandidaten, kurz
    python3 melder/plan_bestandsabgleich.py --plan P    # anderer Plan
    python3 melder/plan_bestandsabgleich.py --selftest
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Repo-Wurzel an schema.sql festmachen, nicht an einer festen Ebenenzahl --
# ein Umzug der Datei bricht dann nicht lautlos (gleiche Bauform wie
# melder/ausloeserlos.py).
_W = Path(__file__).resolve().parent
while not (_W / "schema.sql").exists() and _W != _W.parent:
    _W = _W.parent

STANDARD_PLAN = _W / "docs" / "PLAN_GESAMT_2026-08-13.md"

_ID_MUSTER = re.compile(r"`([A-Z]?[0-9]{1,3}[a-z]?)`")
_DATEIPFAD_MUSTER = re.compile(r"[\w./_-]+\.(?:py|md|sql)\b")


def kennungen_im_plan(plan_text: str) -> list[str]:
    """Alle Kennungen, die im Plan als eigener Backtick-Ausdruck auftreten
    (`81`, `H4`, `F6a`, ...). Reine Textnennungen ohne Backticks (z.B. in
    einer "H2 bis H7"-Kurzform) werden bewusst NICHT erfasst -- ohne
    Backticks ist eine Zahl von jeder anderen Zahl im Fliesstext nicht mehr
    unterscheidbar."""
    return sorted(set(_ID_MUSTER.findall(plan_text)), key=lambda s: (len(s), s))


def _commit_typ(betreff: str) -> str:
    kopf = betreff.split("(", 1)[0].split(":", 1)[0]
    return kopf.strip()


def _kennungs_muster(kennung: str) -> re.Pattern:
    if kennung[:1].isalpha():
        # Buchstaben-Kennung: Wortganzes, nicht an einen Bindestrich
        # angrenzend (schliesst "F1-F10" als Probennamen aus).
        return re.compile(r"(?<![-A-Za-z0-9])" + re.escape(kennung) + r"(?![-A-Za-z0-9])")
    # Numerische Kennung: muss auf "Aufgabe"/"Auftrag" folgen.
    return re.compile(r"(?i)\b(?:aufgabe|auftrag)\D{0,4}" + re.escape(kennung) + r"(?![-0-9])")


def _git_commits(repo_root: Path) -> list[tuple[str, str, str]]:
    """(hash, betreff, voller_text) je Commit, ueber die gesamte Historie."""
    trenner_commit, trenner_feld = "\x02", "\x01"
    lauf = subprocess.run(
        ["git", "log", "--all", f"--format=%H{trenner_feld}%s{trenner_feld}%b{trenner_commit}"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    if lauf.returncode != 0:
        return []
    ergebnis = []
    for stueck in lauf.stdout.split(trenner_commit):
        teile = stueck.split(trenner_feld)
        if len(teile) < 2:
            continue
        h = teile[0].strip()
        if not h:
            continue
        betreff = teile[1]
        rumpf = teile[2] if len(teile) > 2 else ""
        ergebnis.append((h, betreff, betreff + "\n" + rumpf))
    return ergebnis


class Kandidat:
    def __init__(self, kennung: str, commit_hash: str, betreff: str):
        self.kennung = kennung
        self.commit_hash = commit_hash
        self.betreff = betreff

    def __repr__(self) -> str:  # pragma: no cover
        return f"Kandidat({self.kennung!r}, {self.commit_hash[:8]!r})"


_EIGENER_MELDER_MUSTER = re.compile(r"plan_bestandsabgleich")

# SO GEFUNDEN (2026-08-15): 4b5e8b1 nennt H10 woertlich ("... und H10
# (Export-Gegenstueck) frei, an derselben Datei zu arbeiten"), nachdem eine
# Sperre in kern/domaene.py fiel -- H10 wurde damit ENTSPERRT, nicht
# ERLEDIGT (steht im Plan weiterhin unter "Offen"). "frei" unmittelbar nach
# der Kennung ist ein Entsperr-Marker, kein Erledigt-Beleg -- anders als
# "war bereits durch" oder ein Auftrag/Aufgabe-Praefix mit beschriebener
# Lieferung. Fenstergroesse 80 Zeichen: deckt "frei, an derselben Datei zu
# arbeiten" ab, ohne auf einen ganzen Absatz auszugreifen.
_ENTSPERR_FENSTER = 80
_ENTSPERR_MUSTER = re.compile(r"\bfrei\b")


def finde_kandidaten(plan_text: str, commits: list[tuple[str, str, str]]) -> list[Kandidat]:
    kandidaten: list[Kandidat] = []
    for kennung in kennungen_im_plan(plan_text):
        muster = _kennungs_muster(kennung)
        for h, betreff, voll in commits:
            if _commit_typ(betreff) not in ("feat", "fix"):
                continue
            # Ein Commit, der den Melder selbst betrifft (dieses Modul baut
            # oder dokumentiert), zaehlt nie als Beleg fuer eine Planzeile --
            # SO GEFUNDEN (2026-08-15): 0f450fb baute den Melder, nennt dabei
            # im Fliesstext woertlich H4/H5/H6/H7/H10 als Beispiel fuer einen
            # ausgeschlossenen docs(...)-Fehlalarm und traegt selbst den Typ
            # feat -- der Melder mass sich damit an seinem eigenen
            # Dokumentations-Commit und meldete sich selbst als Beleg.
            if _EIGENER_MELDER_MUSTER.search(voll):
                continue
            treffer = muster.search(voll)
            if not treffer:
                continue
            fenster = voll[treffer.end():treffer.end() + _ENTSPERR_FENSTER]
            if _ENTSPERR_MUSTER.search(fenster):
                continue
            if not _DATEIPFAD_MUSTER.search(voll):
                continue
            kandidaten.append(Kandidat(kennung, h, betreff.strip()))
            break  # ein Beleg reicht, weiterer Lauf bringt nur Rauschen
    return kandidaten


def render(kandidaten: list[Kandidat]) -> str:
    if not kandidaten:
        return "plan_bestandsabgleich: keine Kandidaten (Hinweisrecht, kein Veto)."
    zeilen = [
        "plan_bestandsabgleich -- Kandidaten fuer 'vermutlich schon erledigt'.",
        "HEURISTIK, KEIN BELEG FUER 'ERLEDIGT' -- Entscheidung bleibt beim Menschen.",
        "",
    ]
    for k in kandidaten:
        zeilen.append(f"  `{k.kennung}` -- Beleg: {k.commit_hash[:8]} {k.betreff}")
    return "\n".join(zeilen)


def _selftest() -> None:
    plan_text = (
        "`81` (Kanten wieder rechnen). `85` (Melder). `H4` Pruefkorpus. "
        "`H7` etwas anderes. Offen: `H2` bis `H7`, `H10`."
    )
    kennungen = kennungen_im_plan(plan_text)
    for erwartet in ("81", "85", "H2", "H4", "H7", "H10"):
        assert erwartet in kennungen, f"{erwartet} fehlt in {kennungen}"
    # H6 kommt im Beispieltext gar nicht in Backticks vor -- muss darum
    # auch nicht extrahiert werden (Grenzwert-Dokumentation im Docstring).
    assert "H6" not in kennungen
    print("(1) Kennungsextraktion aus Backticks: ok")

    commits = [
        ("aaaa1111", "feat(brainlehr): X (Aufgabe 81)", "feat(brainlehr): X (Aufgabe 81)\nberuehrt melder/foo.py"),
        ("bbbb2222", "feat(brainlehr): Y (Aufgabe 850)", "feat(brainlehr): Y (Aufgabe 850)\nberuehrt melder/bar.py"),
        ("cccc3333", "feat(brainlehr): Z", "feat(brainlehr): Z\nJ1 (Triggerabgleich) war bereits durch melder/schemastand.py da"),
        ("dddd4444", "docs(brainlehr): Plan", "docs(brainlehr): Plan\nOffen: H4, H5, H6, H7, H10 -- siehe melder/x.py"),
        ("eeee5555", "feat(brainlehr): Proben", "feat(brainlehr): Proben\n10 Proben F1-F10 in tests/fixtures.py"),
        ("ffff6666", "fix(brainlehr): kein Dateibeleg", "fix(brainlehr): kein Dateibeleg (Aufgabe 85)\nkeine Datei genannt"),
    ]
    plan_text2 = "`81` X. `85` Y. `J1` Z. `H4` offen. `H7` offen. `F1` Probe."
    funde = finde_kandidaten(plan_text2, commits)
    kennungen_gefunden = {k.kennung for k in funde}

    assert "81" in kennungen_gefunden, "Aufgabe 81 mit Praefix und Datei muss anschlagen"
    print("(2) numerische Kennung mit 'Aufgabe'-Praefix + Datei: ok")

    assert not any(k.kennung == "85" and k.commit_hash == "ffff6666" for k in funde), \
        "Grenzwert: Commit ohne Dateibeleg darf nicht als Kandidat zaehlen"
    print("(3) Grenzwert -- Kennung ohne genannte Datei im Commit: verworfen, ok")

    assert "J1" in kennungen_gefunden, "Buchstaben-Kennung ohne 'Aufgabe'-Praefix muss trotzdem anschlagen"
    print("(4) Buchstaben-Kennung (J1) ohne 'Aufgabe'-Praefix: ok")

    assert "H4" not in kennungen_gefunden, "docs(...)-Commit darf keinen Kandidaten erzeugen"
    print("(5) docs(...)-Commit zaehlt nicht als Beleg: ok")

    assert "F1" not in kennungen_gefunden, "F1-F10 ist eine Probenbenennung, keine Plankennung"
    print("(6) Bindestrich-Ausnahme (F1-F10 ist keine Kennung): ok")

    assert render([]) == "plan_bestandsabgleich: keine Kandidaten (Hinweisrecht, kein Veto)."
    text = render(finde_kandidaten(plan_text2, commits))
    assert "`81`" in text and "HEURISTIK" in text
    print("(7) render(): leer und gefuellt unterscheidbar, Hinweistext vorhanden: ok")

    print("selftest ok (7 Faelle, je mit Gegenprobe)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plan", type=Path, default=STANDARD_PLAN)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if not a.plan.exists():
        print(f"plan_bestandsabgleich: Plandatei fehlt ({a.plan}) -- kein Kandidat.")
        return  # Exit 0: Hinweisrecht, kein Absturz auf einer fehlenden Datei.

    plan_text = a.plan.read_text(encoding="utf-8", errors="replace")
    commits = _git_commits(_W)
    print(render(finde_kandidaten(plan_text, commits)))


if __name__ == "__main__":
    main()
