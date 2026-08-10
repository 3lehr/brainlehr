#!/usr/bin/env python3
"""vorschlag.py — schlaegt faellige Werkzeuge und Faehigkeiten vor, startet nichts.

Planschritt S18. Der Speicher antwortet heute nur, wenn er gefragt wird. Er
soll VORSCHLAGEN, welche Lehren ein Werkzeug oder eine Faehigkeit verdienen
-- aber die Bedingung fuer "automatisch starten" ist die maschinelle
Abnahme, und die fehlt noch. Darum bleibt dieses Werkzeug beim Vorschlag
stehen: es liest die Datenbank, schreibt NICHTS hinein, legt ausser seiner
eigenen Textausgabe keine Datei an und startet keinen Agenten. Ein Vorschlag
ist ein Entwurf, kein Auftrag -- wer ihn ausfuehrt, entscheidet ein Mensch.

Zwei Kandidatenklassen, aus dem Bestand (L-b79360), nicht aus Geschmack:

  PRUEFSTEIN-Kandidaten: antipattern-Lehren mit mindestens zwei Vorkommen
  (occurrences >= 2), zu denen es noch KEINEN Pruefstein gibt. Erkennung:
  die Lehrkennung (z.B. "L-352afa") kommt woertlich in einer .py-Datei
  dieses Repos vor -- bestehende Pruefsteine zitieren ihre Lehre so im
  Kommentar (siehe deckelreihe.py, faehigkeiten.py). PREIS dieser Regel:
  eine Lehre, die nur ZUFAELLIG irgendwo genannt wird (z.B. in einer
  Uebergabe-Notiz oder einem Docstring, der sie nur erwaehnt statt
  gegen sie zu pruefen), gilt hier faelschlich als bereits behandelt.
  Diese Regel prueft Erwaehnung, nicht Wirksamkeit.

  FAEHIGKEIT-Kandidaten: pattern-Lehren, deren description oder prevention
  woertlich das Wort "Reihenfolge" nennt (mechanisierbare Reihenfolge ist
  kein Pruefstein-Fall -- ein Ablauf braucht Prosa/eine Faehigkeit, kein
  boolesches Praedikat), und die im Repo noch nirgends zitiert werden.

Je Kandidat ein AUFTRAGSENTWURF nach dem systemweiten Vier-Teile-Schema
(Fakten/Grenzen/Abnahme/Einsatz) -- gefuellt aus der Lehre, nicht erfunden.

Usage:
  python3 vorschlag.py --bericht    # Vorschlaege auf stdout
  python3 vorschlag.py --selftest   # Selbsttest gegen eine temporaere DB
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from haken.ort import DB as _DB, WURZEL  # noqa: E402

DB = str(_DB)
MAX_JE_KATEGORIE = 3
_AUSGENOMMEN = {"tests", "__pycache__", ".git", ".claude", "node_modules"}
_ID_MUSTER = re.compile(r"^L-[0-9a-f]{6}$")


# ---------- Repo-weite Zitatsuche ----------

def gezitierte_ids(repo_root: Path) -> set[str]:
    """Menge aller Lehrkennungen (L-xxxxxx), die woertlich in irgendeiner
    .py-Datei des Repos vorkommen -- unabhaengig davon, ob als Pruefstein
    oder nur als Erwaehnung (siehe Docstring-Vorbehalt oben)."""
    gefunden: set[str] = set()
    muster = re.compile(r"L-[0-9a-f]{6}")
    for pfad in repo_root.rglob("*.py"):
        if any(teil in _AUSGENOMMEN for teil in pfad.relative_to(repo_root).parts[:-1]):
            continue
        try:
            text = pfad.read_text(errors="replace")
        except OSError:
            continue
        gefunden.update(muster.findall(text))
    return gefunden


# ---------- Kandidatenauswahl ----------

def pruefstein_kandidaten(conn: sqlite3.Connection, zitiert: set[str]) -> list[dict]:
    rows = conn.execute(
        "SELECT id, occurrences, description, root_cause, prevention "
        "FROM lessons_learned WHERE type = 'antipattern' AND occurrences >= 2 "
        "ORDER BY occurrences DESC, id ASC"
    ).fetchall()
    return [
        {"id": r[0], "occurrences": r[1], "description": r[2],
         "root_cause": r[3], "prevention": r[4]}
        for r in rows if r[0] not in zitiert
    ]


def faehigkeit_kandidaten(conn: sqlite3.Connection, zitiert: set[str]) -> list[dict]:
    rows = conn.execute(
        "SELECT id, occurrences, description, root_cause, prevention "
        "FROM lessons_learned WHERE type = 'pattern' "
        "AND (description LIKE '%Reihenfolge%' OR prevention LIKE '%Reihenfolge%') "
        "ORDER BY occurrences DESC, id ASC"
    ).fetchall()
    return [
        {"id": r[0], "occurrences": r[1], "description": r[2],
         "root_cause": r[3], "prevention": r[4]}
        for r in rows if r[0] not in zitiert
    ]


# ---------- Auftragsentwurf ----------

def _erster_satz(text: str | None) -> str:
    if not text:
        return "(prevention leer -- kein Einsatz-Satz ableitbar)"
    text = text.strip()
    treffer = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    return treffer[0].strip()


def auftragsentwurf(lehre: dict, art: str) -> str:
    """art: 'Pruefstein' oder 'Faehigkeit'. Fakten woertlich aus description
    und root_cause, Einsatz aus dem ersten Satz von prevention -- nichts
    davon wird umformuliert."""
    zeilen = [
        f"### Auftragsentwurf {lehre['id']} ({art}, {lehre['occurrences']}x)",
        "",
        "Fakten:",
        f"- description: {lehre['description']}",
        f"- root_cause: {lehre['root_cause'] or '(leer)'}",
        "",
        "Grenzen:",
        "- (leer -- zur Auftragszeit aus dem Agentenregister ergaenzen: "
        "welche Dateien laufende Agenten gerade halten und tabu sind)",
        "",
        "Abnahme:",
        "- rot vor gruen: Testfall gegen den jetzigen Stand schreiben, "
        "woertlich als fehlschlagend melden, danach bauen.",
        "- Grenzwert: Schwelle-1, Schwelle, Schwelle+1 pruefen.",
        "- Negativfall: ein Fall, der die Lehre NICHT verletzt, muss "
        "durchlaufen (kein falsches Positiv).",
        "",
        f"Einsatz: {_erster_satz(lehre['prevention'])}",
    ]
    return "\n".join(zeilen)


# ---------- Bericht ----------

def erhebe(conn: sqlite3.Connection, repo_root: Path) -> tuple[list[dict], list[dict]]:
    zitiert = gezitierte_ids(repo_root)
    return pruefstein_kandidaten(conn, zitiert), faehigkeit_kandidaten(conn, zitiert)


def render(pruefstein: list[dict], faehigkeit: list[dict]) -> str:
    lines = [
        "# Vorschlaege — faellige Werkzeuge/Faehigkeiten aus dem Speicher",
        "",
        "Dies sind Entwuerfe, keine Auftraege. Nichts wurde gestartet, "
        "nichts in die Datenbank geschrieben.",
        "",
        f"## Pruefstein-Kandidaten ({len(pruefstein)} gefunden, "
        f"hoechstens {MAX_JE_KATEGORIE} gezeigt)",
        "",
    ]
    if not pruefstein:
        lines.append("(keine)")
    for lehre in pruefstein[:MAX_JE_KATEGORIE]:
        lines.append(auftragsentwurf(lehre, "Pruefstein"))
        lines.append("")
    rest_p = max(0, len(pruefstein) - MAX_JE_KATEGORIE)
    if rest_p:
        lines.append(f"... und {rest_p} weitere Pruefstein-Kandidaten, nicht gezeigt.")
        lines.append("")

    lines.append(
        f"## Faehigkeit-Kandidaten ({len(faehigkeit)} gefunden, "
        f"hoechstens {MAX_JE_KATEGORIE} gezeigt)"
    )
    lines.append("")
    if not faehigkeit:
        lines.append("(keine)")
    for lehre in faehigkeit[:MAX_JE_KATEGORIE]:
        lines.append(auftragsentwurf(lehre, "Faehigkeit"))
        lines.append("")
    rest_f = max(0, len(faehigkeit) - MAX_JE_KATEGORIE)
    if rest_f:
        lines.append(f"... und {rest_f} weitere Faehigkeit-Kandidaten, nicht gezeigt.")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return

    if "--bericht" in sys.argv:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
        try:
            pruefstein, faehigkeit = erhebe(conn, WURZEL)
        finally:
            conn.close()
        print(render(pruefstein, faehigkeit))
        return

    print(__doc__)


# ---------- Selbsttest gegen eine temporaere Datenbank ----------

def selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo = td / "repo"
        repo.mkdir()

        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE lessons_learned (id TEXT, type TEXT, occurrences INTEGER, "
            "description TEXT, root_cause TEXT, prevention TEXT)"
        )
        zeilen = [
            # (a) zwei Vorkommen, kein Zitat -> Kandidat
            ("L-aaaaaa", "antipattern", 2, "Fehler A passiert zweimal.",
             "Ursache A.", "Vermeide A."),
            # (b) zwei Vorkommen, ABER Kennung steht im Repo -> kein Kandidat
            ("L-bbbbbb", "antipattern", 2, "Fehler B passiert zweimal.",
             "Ursache B.", "Vermeide B."),
            # (c) Grenzwert: genau EIN Vorkommen -> kein Kandidat
            ("L-cccccc", "antipattern", 1, "Fehler C passiert einmal.",
             "Ursache C.", "Vermeide C."),
            # Faehigkeit: pattern mit "Reihenfolge" im Text, unzitiert
            ("L-dddddd", "pattern", 5, "Ein Muster mit fester Reihenfolge.",
             "Weil Schritt 1 Schritt 2 voraussetzt.", "Erst pruefen, dann schreiben."),
            # pattern OHNE "Reihenfolge" -> kein Faehigkeit-Kandidat
            ("L-eeeeee", "pattern", 5, "Ein Muster ohne das Schluesselwort.",
             "Ursache E.", "Tu E."),
        ]
        conn.executemany(
            "INSERT INTO lessons_learned VALUES (?,?,?,?,?,?)", zeilen
        )

        # Pruefstein fuer L-bbbbbb existiert bereits (Kennung im Quelltext zitiert).
        (repo / "bestehender_pruefstein.py").write_text(
            '"""Prueft gegen L-bbbbbb."""\nassert True\n'
        )

        pruefstein, faehigkeit = erhebe(conn, repo)
        pids = {k["id"] for k in pruefstein}
        assert "L-aaaaaa" in pids, "(a) zwei Vorkommen ohne Zitat muss Kandidat sein"
        assert "L-bbbbbb" not in pids, "(zitierte Kennung darf nicht erscheinen)"
        assert "L-cccccc" not in pids, "(c) Grenzwert: ein Vorkommen darf kein Kandidat sein"
        print("  (a)+(b)+(c) Pruefstein-Auswahl inkl. Grenzwert: ok")

        fids = {k["id"] for k in faehigkeit}
        assert "L-dddddd" in fids, "Reihenfolge-Lehre unzitiert muss Kandidat sein"
        assert "L-eeeeee" not in fids, "pattern ohne 'Reihenfolge' darf kein Kandidat sein"
        print("  Faehigkeit-Auswahl (Reihenfolge-Schluesselwort): ok")

        # (d) mehr als drei Kandidaten -> drei plus Restzahl.
        viele = [
            (f"L-f0000{i}", "antipattern", 2 + i, f"Fehler F{i}.", f"Ursache F{i}.", f"Vermeide F{i}.")
            for i in range(5)
        ]
        conn.executemany("INSERT INTO lessons_learned VALUES (?,?,?,?,?,?)", viele)
        pruefstein2, _ = erhebe(conn, repo)
        assert len(pruefstein2) == 6, pruefstein2  # L-aaaaaa + 5 neue
        text = render(pruefstein2, [])
        assert "3 weitere Pruefstein-Kandidaten" in text, text
        gezeigt = text.count("### Auftragsentwurf")
        assert gezeigt == MAX_JE_KATEGORIE, gezeigt
        print("  (d) Deckelung auf drei plus Restzahl: ok")

        # (e) Auftragsentwurf enthaelt alle vier Teile, Fakten woertlich.
        entwurf = auftragsentwurf(
            {"id": "L-aaaaaa", "occurrences": 2, "description": "Fehler A passiert zweimal.",
             "root_cause": "Ursache A.", "prevention": "Vermeide A. Danach noch mehr."},
            "Pruefstein",
        )
        for teil in ("Fakten:", "Grenzen:", "Abnahme:", "Einsatz:"):
            assert teil in entwurf, f"{teil} fehlt im Auftragsentwurf"
        assert "Fehler A passiert zweimal." in entwurf, "Fakten nicht woertlich uebernommen"
        assert "Ursache A." in entwurf, "root_cause nicht woertlich uebernommen"
        assert entwurf.split("Einsatz: ")[1].strip() == "Vermeide A.", \
            "Einsatz muss der erste Satz aus prevention sein"
        print("  (e) Auftragsentwurf: vier Teile vorhanden, Fakten woertlich: ok")

        # Grenzfall gezitierte_ids: Kennung wird gefunden, egal wo im Text.
        ids = gezitierte_ids(repo)
        assert "L-bbbbbb" in ids
        assert "L-aaaaaa" not in ids
        print("  gezitierte_ids findet echte Zitate, keine Phantome: ok")

    print("Alle Selbsttests gruen.")


if __name__ == "__main__":
    main()
