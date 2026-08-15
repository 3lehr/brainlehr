"""Jeder gebaute Haken haengt auch an einem Ereignis.

Aufgabe 98. Der Befund, der diese Datei noetig macht, ist an einem Tag dreimal
aufgetreten und heisst jedes Mal gleich: gebaut, laufend, nicht verdrahtet.

  haken/worktree_identitaet.py   gebaut 2026-08-13, zweimal repariert,
                                 Selbsttest gruen -- und in ~/.claude/
                                 settings.json null Treffer bis 2026-08-14.
  haken/ui_guard.py              seit 2026-07-30 nie verdrahtet (gemessen im
                                 Regelgriff-Lauf).
  haken/mcp_veraltet.py          verdrahtet, aber an UserPromptSubmit -- im
                                 Selbstlauf gibt es keine Prompts, also
                                 blind, wenn niemand zusieht (L-1228cf).

DER UNTERSCHIED ZWISCHEN DEN DREI IST DER GANZE PUNKT: Der erste war ein
vergessener Handgriff, der zweite eine Absicht ohne Ausfuehrung, der dritte
eine falsche Wahl des Ereignisses. Nur der erste faellt hier auf -- der Test
prueft die EXISTENZ der Verdrahtung, nicht ihre Tauglichkeit. Das steht hier,
damit niemand aus einem gruenen Lauf schliesst, die Haken wirkten.

BEWUSST KEIN VOLLSTAENDIGKEITSANSPRUCH: Nicht jede Datei unter haken/ gehoert
an ein Ereignis. Bibliotheken und Hilfsmodule sind ausgenommen -- erkennbar
daran, dass sie kein stdin lesen. Die Unterscheidung laeuft ueber ein Merkmal
des Codes, nicht ueber eine gepflegte Liste; eine Liste veraltet mit dem
naechsten Haken.
"""
from __future__ import annotations

import subprocess
import sys
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w

EINSTELLUNGEN = _Path.home() / ".claude" / "settings.json"
# Repo-eigene Einstellungen zaehlen mit: haken/stash_guard_hook.py steht
# bewusst NICHT in der globalen Datei (Eintraege verschwinden dort, L-083b95),
# sondern in .claude/settings.json dieses Repos.
EINSTELLUNGEN_REPO = WURZEL / ".claude" / "settings.json"


def _haken_dateien() -> list[_Path]:
    """Dateien, die sich wie ein Haken verhalten: sie lesen stdin.

    Das ist das Merkmal, an dem ein Haken sich von einer Bibliothek
    unterscheidet -- der Klient reicht sein Ereignis als JSON auf stdin
    herein. Wer stdin nicht liest, kann kein Haken sein.
    """
    treffer = []
    for f in sorted((WURZEL / "haken").glob("*.py")):
        text = f.read_text(encoding="utf-8")
        if "sys.stdin" in text or "stdin.read" in text:
            treffer.append(f)
    return treffer


def _verdrahtet() -> str:
    inhalt = ""
    if EINSTELLUNGEN.exists():
        inhalt += EINSTELLUNGEN.read_text(encoding="utf-8")
    if EINSTELLUNGEN_REPO.exists():
        inhalt += EINSTELLUNGEN_REPO.read_text(encoding="utf-8")
    return inhalt


def _mittelbar_verdrahtete(haken_liste: list[_Path], inhalt: str) -> set[str]:
    """Wer von einem direkt verdrahteten Haken beim Namen aufgerufen wird,
    gilt selbst als verdrahtet. Als eigene Funktion, damit die Gegenprobe sie
    synthetisch pruefen kann statt an echten Dateinamen zu haengen, die mit
    der Zeit wegwandern (siehe Gegenprobe unten)."""
    mittelbar = set()
    for f in haken_liste:
        if f.name not in inhalt:
            continue
        text = f.read_text(encoding="utf-8")
        for anderer in haken_liste:
            if anderer.stem in text and anderer.name != f.name:
                mittelbar.add(anderer.name)
    return mittelbar


def test_jeder_haken_haengt_an_einem_ereignis():
    """Die Ratsche. Sie prueft Existenz, nicht Wirksamkeit -- siehe Modulkopf."""
    if not EINSTELLUNGEN.exists() and not EINSTELLUNGEN_REPO.exists():
        return  # Fremde Maschine ohne Klient-Einstellungen: kein Befund.
    inhalt = _verdrahtet()
    # Verdrahtet ist auch, wer von einem verdrahteten Haken AUFGERUFEN wird
    # -- siehe _mittelbar_verdrahtete. Ohne diese zweite Stufe meldet die
    # Ratsche einen Haken als tot, der arbeitet -- und ein Fehlalarm an
    # dieser Stelle ist besonders teuer, weil er genau die Meldung entwertet,
    # um die es hier geht.
    haken_liste = _haken_dateien()
    mittelbar = _mittelbar_verdrahtete(haken_liste, inhalt)
    ohne = [f.name for f in haken_liste
            if f.name not in inhalt and f.name not in mittelbar]
    assert not ohne, (
        f"{len(ohne)} Haken sind gebaut, aber an kein Ereignis gehaengt: "
        + ", ".join(ohne)
        + " -- ein Mechanismus, der nirgends haengt, zaehlt als keiner. "
        "Entweder verdrahten oder als Bibliothek kennzeichnen (kein stdin).")


def test_mittelbar_verdrahtete_gelten_als_verdrahtet(tmp_path):
    """Gegenprobe zur zweiten Stufe: sie darf nicht ALLES durchwinken.

    Synthetisch statt am echten Beispiel haken/existenzpruefung.py: das war
    bis heute nur MITTELBAR verdrahtet (Aufrufer antwort_abruf.py), seit
    Commit 24c24848 steht es aber auch DIREKT im Stop-Hook der repo-eigenen
    .claude/settings.json -- die jetzt zusaetzlich gelesen wird (Ratsche
    erweitert wegen stash_guard_hook.py, das nur dort steht). Ein echtes
    Dateibeispiel wandert mit der Zeit weg; die Gegenprobe baut sich ihr
    eigenes, damit sie das nicht mehr kann.
    """
    a = tmp_path / "a_direkt.py"
    a.write_text("sys.stdin.read()\nimport b_indirekt\n", encoding="utf-8")
    b = tmp_path / "b_indirekt.py"
    b.write_text("sys.stdin.read()\n", encoding="utf-8")
    c_erfunden = tmp_path / "c_erfunden.py"
    c_erfunden.write_text("sys.stdin.read()\n", encoding="utf-8")
    inhalt = "hooks command python3 a_direkt.py"

    mittelbar = _mittelbar_verdrahtete([a, b, c_erfunden], inhalt)
    assert "b_indirekt.py" in mittelbar, (
        "b wird von a (direkt verdrahtet) beim Namen aufgerufen -- muss als "
        "mittelbar verdrahtet gelten")
    assert "c_erfunden.py" not in mittelbar, (
        "c kommt in keinem Aufrufer vor -- ein erfundener Name darf nicht "
        "durchgehen")


def test_die_erkennung_unterscheidet_haken_von_bibliothek():
    """Gegenprobe: ohne sie koennte der Test darueber gruen sein, weil er
    NICHTS als Haken erkennt."""
    erkannt = {f.name for f in _haken_dateien()}
    assert len(erkannt) >= 5, f"zu wenige Haken erkannt ({len(erkannt)}) -- Erkennung pruefen"
    assert "knowledge_recall_hook.py" in erkannt


def test_worktree_haken_liefert_immer_genau_eine_zeile():
    """WorktreeCreate hat den schaerfsten Vertrag aller Ereignisse: stdout IST
    der Pfad, und jeder Exit ungleich 0 verhindert die Anlage komplett.

    Am 2026-08-13 zweimal gebrochen -- erst ein belegter Pfad (das
    Sammelverzeichnis), dann gar keine Ausgabe. Beide Male konnte keine neue
    Sitzung mehr starten. Deshalb hier beide Faelle als Probe, samt dem
    unguenstigsten: fehlender Name.
    """
    haken = WURZEL / "haken" / "worktree_identitaet.py"
    for eingabe in ('{"base_directory":"/tmp/x","worktree_name":"n"}',
                    '{"base_directory":"/tmp/x"}',
                    '{}',
                    'kein json'):
        lauf = subprocess.run([sys.executable, str(haken)], input=eingabe,
                              capture_output=True, text=True, timeout=30)
        assert lauf.returncode == 0, f"Exit {lauf.returncode} bei {eingabe!r} -- blockiert die Anlage"
        zeilen = [z for z in lauf.stdout.splitlines() if z.strip()]
        assert len(zeilen) == 1, f"{len(zeilen)} Zeilen bei {eingabe!r}: {lauf.stdout!r}"
        assert not zeilen[0].rstrip("/").endswith("worktrees"), (
            f"Sammelverzeichnis als Pfad bei {eingabe!r}: {zeilen[0]!r} -- git lehnt das ab")
