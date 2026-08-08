#!/usr/bin/env python3
"""
knowledge_capture_hook.py — Auto-Capture-Trigger (Stop-Hook, systemweit).

Feuert 1× pro Session, sobald die Session >=3 Edits/Writes hatte (Zähler von
session_edit_tick.py). Zwingt Claude via `decision:block`, die /learn-Fähigkeit
aufzurufen — die entscheidet anhand ihrer Kriterien, was aus dieser Session
dauerhaft in die Knowledge-DB gehört, und schreibt es (lesson_record für
Fehler/Gotchas, knowledge_add für Fakten/Entscheidungen). Dieselbe DB, aus der
der Recall-Hook wieder liest.

Ein Hook kann keine Skill selbst starten; er kann nur das Modell zur Fortsetzung
zwingen und in `reason` den Skill-Aufruf anweisen. Die Entscheidungslogik lebt
damit in EINER Datei (hub/.claude/commands/learn.md), nicht hier.

Design (Ponytail):
- 1×/Session via .harvested-Marker -> kein Nag.
- Endlosschutz: stop_hook_active-Guard + Marker (nach dem erzwungenen Lauf
  blockt der nächste Stop nicht mehr).
- Zu aggressiv? -> `_DECISION_BLOCK = False` unten macht daraus einen reinen
  Reminder (kapert den Turn nicht mehr).

Zwei Fragen statt einer (2026-08-07): Bestand vorher schief — 243 antipattern/
97 error gegen nur 79 pattern (Verhaeltnis ~3,4:1 zu Fehlschlaegen), Grund:
die alte _INSTRUCTION fragte nur nach Fehlern/Gotchas. Nach Hermes-Agent-
Vorbild (Faehigkeiten aus GELUNGENEN Laeufen) jetzt zusaetzlich Frage 2 nach
nicht-offensichtlichem Erfolg. Gegen das erwartete Ausweichen aufs Leichtere
(Erfolg beschreiben ist bequemer als eigene Fehler eingestehen): Frage 1
bleibt vollstaendig, unverkuerzt und ZUERST; Frage 2 ist explizit als
ZUSAETZLICH markiert ("zusaetzlich, nicht statt"), mit einer Sperrklausel
gegen erfundene Pattern (nur eintragen, wenn eines der drei Kriterien wirklich
zutrifft). Baseline zum Vergleich (Messung im Auftrag, 2026-08-07T00:45):
gesamt pattern 79 / antipattern 243 = 0,33; heute pattern 13 / antipattern 35
= 0,37. Bleibt das Verhaeltnis dort, hat die zweite Frage nichts bewirkt.

Nachschaerfung selben Tags: Frage 2 nannte "mehrschrittige Aufgabe" nur als
eines von drei gleichwertigen Beispielen — eine Antwort konnte den Erfolg
nennen, ohne Schrittfolge oder Voraussetzung zu sagen, und war dann eine
Beobachtung, keine wiederholbare Anleitung. Text verlangt jetzt woertlich
REIHENFOLGE der Schritte UND VORAUSSETZUNG, unter der das Verfahren griff.
Laenge 1190 -> 1182 Zeichen (Obergrenze 1190 eingehalten, an anderer Stelle
gekuerzt).

IMMER exit 0.
"""
import json
import os
import sys

# True: erzwingt den /learn-Aufruf (Skill entscheidet). False: nur Klartext-Reminder.
_DECISION_BLOCK = True

_INSTRUCTION = (
    "Diese Session hatte substanzielle Änderungen. Rufe jetzt die /learn-Fähigkeit "
    "auf (Skill-Tool, skill: \"learn\") und beantworte BEIDE Fragen — nicht nur die "
    "leichtere:\n"
    "1) FEHLSCHLAG (zuerst, vollständig): welche Fehler/Gotchas/Antipatterns aus "
    "SELBST GEMACHTEN Fehlern dieser Session gehören dauerhaft in die Knowledge-DB?\n"
    "2) ERFOLG (zusätzlich, nicht statt Frage 1): welches Verfahren hat funktioniert "
    "— nicht offensichtlich, nach mehreren Schritten oder einer Korrektur des "
    "Betreibers? Nenne REIHENFOLGE der Schritte UND VORAUSSETZUNG, unter der es griff "
    "— ohne beides nur Beobachtung, keine Anleitung. Nur eintragen, wenn eines "
    "vorlag — kein Pattern erfinden, wenn die Session nichts Nennenswertes bot.\n"
    "Prüfe auf Duplikate, schreibe via lesson_record/knowledge_add. Trifft auf keine "
    "der beiden Fragen etwas zu, hält die Fähigkeit das fest und du stoppst — kein "
    "Zwang, etwas zu erfinden.\n"
    "Aktualisiere außerdem die STAND.md jeder in dieser Session bearbeiteten App "
    "(apps/<x>/STAND.md bzw. Worktree-Root bei Ein-App-Worktrees): Datei "
    "ÜBERSCHREIBEN, max 10 Zeilen, Format siehe hub/CLAUDE.md §STAND. Welche Apps "
    "bearbeitet wurden, lässt sich ggf. aus `git status --porcelain` ableiten."
)

TMP = "/tmp"
MIN_EDITS = 3


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    # Endlosschutz: wenn dieser Stop schon von einem Hook fortgesetzt wurde, raus.
    if payload.get("stop_hook_active"):
        return
    sid = payload.get("session_id") or "unknown"
    sid = "".join(c for c in sid if c.isalnum() or c in "-_")[:64]
    dirty = os.path.join(TMP, f"claude_know_{sid}.dirty")
    harvested = os.path.join(TMP, f"claude_know_{sid}.harvested")

    if os.path.exists(harvested):
        return
    edits = 0
    try:
        with open(dirty) as f:
            edits = int(f.read().strip() or "0")
    except Exception:
        return
    if edits < MIN_EDITS:
        return

    try:
        open(harvested, "w").close()
    except Exception:
        pass

    if _DECISION_BLOCK:
        # Stop-Hook-Protokoll: block -> Modell macht weiter und befolgt `reason`.
        print(json.dumps({"decision": "block", "reason": _INSTRUCTION}))
    else:
        print(f"<knowledge-capture-reminder>\n{_INSTRUCTION}\n</knowledge-capture-reminder>")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
