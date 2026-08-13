"""Die Zahl der Plandateien OHNE die vierzeilige Auftragsform darf nur SINKEN.

ANLASS: Seit 2026-08-12 tragen Plandateien die Aufträge selbst -- ein Block
"Für alle Aufträge gleichermaßen gilt" und je Schritt eine Tabelle mit den
Zeilen Darf ändern / Tabu zusätzlich / Fakten / Abnahme. Vorbild:
docs/PLAN_MACAPP_2026-08-12.md, Abschnitt "Aufträge, fertig zum Übergeben".
Vier von der Hand formulierte Aufträge hatten an einem Tag zweimal einen
Agenten im Wartezustand enden lassen, weil die Auflage zum Testlauf
unterschiedlich scharf stand (Knoten 1d0d16bc).

WARUM RATSCHE UND NICHT VERBOT: Ein Verbot machte sofort das gute Dutzend
Bestandspläne rot, die älter sind als diese Form -- dieselbe Fehlerklasse
("blockierende Wache gegen unerfüllbare Regel") ist hier schon einmal
gemessen worden (tests/test_naht_ratsche.py). Die Ratsche lässt den Bestand
in Ruhe und verhindert nur das Wachsen: eine neue Plandatei ohne die Form
fällt auf, eine alte darf liegen bleiben.

BEFUND, der beim Bau dieser Datei auffiel: PLAN_MACAPP_2026-08-12.md wird im
Auftrag als "einzige vollständige Umsetzung" benannt, trägt aber in Schritt 4
und Schritt 5 keine "Tabu zusätzlich"-Zeile -- nur Darf-ändern, Fakten und
Abnahme sind in jedem Schritt tatsächlich vorhanden, Tabu nur an manchen.
Deshalb prüft diese Ratsche je Schritt genau diese drei Zeilen als Pflicht
und verlangt "Tabu zusätzlich" nur einmal irgendwo im Aufträge-Block der
Datei -- das ist die Messlatte, die der eigene Referenzplan tatsächlich
erfüllt. Wer strenger sein will (alle vier je Schritt, ausnahmslos), macht
damit auch das genannte Vorbild rot.

WAS SIE NICHT KANN: Sie erkennt nur echte Markdown-Tabellenzeilen der Form
"| **Darf ändern** | ... |" -- Fließtext, der die Auftragsform nur BESCHREIBT
oder ZITIERT (etwa in Anführungszeichen oder als Beispiel), erzeugt keine
solche Zeile und zählt nicht als erfüllt. Und sie zählt DATEIEN, nicht
Schritte: eine Datei mit einem vollständigen und einem lückenhaften Schritt
gilt insgesamt als unvollständig.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
BASIS = WURZEL / "tests" / "planform_basis.json"
PLAN_ORDNER = WURZEL / "docs"

_AUFTRAEGE_BLOCK = re.compile(r"^##\s+Auftr[äa]ge\b.*$", re.M)
_NAECHSTER_H2 = re.compile(r"^##\s+", re.M)
_SCHRITT = re.compile(r"^###\s+.*$", re.M)

_ZEILE_DARF = re.compile(r"^\|\s*\*\*Darf änder[n]?\*\*\s*\|", re.M)
_ZEILE_FAKTEN = re.compile(r"^\|\s*\*\*Fakten\*\*\s*\|", re.M)
_ZEILE_ABNAHME = re.compile(r"^\|\s*\*\*Abnahme\*\*\s*\|", re.M)
_ZEILE_TABU = re.compile(r"^\|\s*\*\*Tabu\b.*\*\*\s*\|", re.M)


def _auftraege_abschnitt(text: str) -> str | None:
    start = _AUFTRAEGE_BLOCK.search(text)
    if not start:
        return None
    rest = text[start.end():]
    ende = _NAECHSTER_H2.search(rest)
    return rest[: ende.start()] if ende else rest


def _schritt_abschnitte(auftraege_text: str) -> list[str]:
    stellen = [m.start() for m in _SCHRITT.finditer(auftraege_text)]
    if not stellen:
        return []
    stellen.append(len(auftraege_text))
    return [auftraege_text[a:b] for a, b in zip(stellen, stellen[1:])]


def hat_auftragsform(text: str) -> bool:
    """True, wenn die Datei je Schritt Darf-ändern/Fakten/Abnahme als echte
    Tabellenzeile trägt und Tabu-zusätzlich mindestens einmal im
    Aufträge-Block vorkommt. Siehe Modul-Docstring für die Begründung der
    Messlatte."""
    abschnitt = _auftraege_abschnitt(text)
    if abschnitt is None:
        return False
    schritte = _schritt_abschnitte(abschnitt)
    if not schritte:
        return False
    for schritt in schritte:
        if not (_ZEILE_DARF.search(schritt) and _ZEILE_FAKTEN.search(schritt)
                and _ZEILE_ABNAHME.search(schritt)):
            return False
    return bool(_ZEILE_TABU.search(abschnitt))


def plandateien_ohne_auftragsform() -> list[str]:
    treffer = []
    for pfad in sorted(PLAN_ORDNER.glob("PLAN_*.md")):
        text = pfad.read_text(encoding="utf-8")
        if not hat_auftragsform(text):
            treffer.append(str(pfad.relative_to(WURZEL)))
    return treffer


def test_planform_waechst_nicht():
    ist = set(plandateien_ohne_auftragsform())
    basis = set(json.loads(BASIS.read_text(encoding="utf-8")))

    neu = sorted(ist - basis)
    assert not neu, (
        f"Plandateien vorhanden: {len(list(PLAN_ORDNER.glob('PLAN_*.md')))}, "
        f"geprüft: {len(list(PLAN_ORDNER.glob('PLAN_*.md')))}, "
        f"beanstandet: {len(neu)} -- neue Plandatei(en) ohne die vierzeilige "
        "Auftragsform (je Schritt Darf ändern/Fakten/Abnahme, dazu Tabu "
        "zusätzlich mindestens einmal): " + ", ".join(neu) +
        " -- Vorbild docs/PLAN_MACAPP_2026-08-12.md, Abschnitt "
        "'Aufträge, fertig zum Übergeben'."
    )


def test_basis_bleibt_ehrlich():
    """Gegenprobe: Wird eine Bestandsdatei nachträglich vollständig, muss sie
    aus der Basis verschwinden -- sonst wächst der Spielraum still mit."""
    ist = set(plandateien_ohne_auftragsform())
    basis = set(json.loads(BASIS.read_text(encoding="utf-8")))

    erledigt = sorted(basis - ist)
    assert not erledigt, (
        "Diese Dateien stehen noch in der Basis, tragen aber inzwischen die "
        "vollständige Auftragsform: " + ", ".join(erledigt) +
        " -- aus tests/planform_basis.json streichen, damit die Ratsche "
        "wieder greift."
    )


def test_negativfall_zitat_zaehlt_nicht():
    """Eine Datei, die die Auftragsform nur beschreibt oder zitiert (Fließtext
    mit den Stichworten, keine echte Tabellenzeile), darf nicht als konform
    durchgehen."""
    zitat = (
        "## Aufträge, fertig zum Übergeben\n\n"
        "### Schritt 1 — Beispiel\n\n"
        "Dieser Plan beschreibt die Form: **Darf ändern**, **Tabu "
        "zusätzlich**, **Fakten**, **Abnahme** sind die vier Zeilen, die "
        "jeder Auftrag tragen soll. Hier steht das nur als Erklärung, keine "
        "Tabelle folgt.\n"
    )
    assert not hat_auftragsform(zitat)


def test_positivfall_erfuellt_die_form():
    voll = (
        "## Aufträge, fertig zum Übergeben\n\n"
        "### Schritt 1 — Beispiel\n\n"
        "| | |\n|---|---|\n"
        "| **Darf ändern** | `tests/` |\n"
        "| **Tabu zusätzlich** | `kern/` |\n"
        "| **Fakten** | Ein Satz. |\n"
        "| **Abnahme** | Rot vor grün. |\n"
    )
    assert hat_auftragsform(voll)


def test_rotprobe_fehlende_tabu_zeile_faellt_auf():
    """Rot-vor-grün-Beleg für die Ratsche selbst: eine neue Plandatei ohne
    die geforderten Zeilen wird angelegt, muss anschlagen, dann zurückgenommen."""
    wegwerf = PLAN_ORDNER / "PLAN_WEGWERF_ROTPROBE_9999-01-01.md"
    assert not wegwerf.exists(), "Wegwerfdatei existiert schon -- Kollision"
    try:
        wegwerf.write_text(
            "## Aufträge, fertig zum Übergeben\n\n"
            "### Schritt 1 — ohne Abnahme\n\n"
            "| | |\n|---|---|\n"
            "| **Darf ändern** | `tests/` |\n"
            "| **Fakten** | Ein Satz. |\n",
            encoding="utf-8",
        )
        vor = set(plandateien_ohne_auftragsform())
        assert "docs/PLAN_WEGWERF_ROTPROBE_9999-01-01.md" in vor, (
            "Ratsche schlägt bei einer unvollständigen neuen Plandatei nicht "
            "an -- rot-vor-grün-Beleg fehlgeschlagen"
        )
    finally:
        wegwerf.unlink(missing_ok=True)

    nach = set(plandateien_ohne_auftragsform())
    assert "docs/PLAN_WEGWERF_ROTPROBE_9999-01-01.md" not in nach
