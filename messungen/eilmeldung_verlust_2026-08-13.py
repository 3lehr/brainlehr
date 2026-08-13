#!/usr/bin/env python3
"""Messauftrag 2026-08-13: Wo geht die Eilmeldung verloren?

Kein Reparaturskript -- liest nur, ruft eilmeldung_hook.py mit einem
nachgestellten Payload auf und meldet, was beobachtbar ist. Schreibt nichts
ausser der eigenen Ausgabe (Aufrufer leitet nach runs/ um).

Belege, siehe Befund im selben Verzeichnis / runs/eilmeldung_verlust_2026-08-13.json:
- Zustandsdatei /tmp/claude-eilmeldung-d695fd29-c21d-48.json (STATE_DIR="/tmp",
  sid = ersten 16 alnum/-/_ Zeichen der Sitzungskennung) zeigte vor jedem Test
  calls=5739, 10 unquittierte "dringend"-Meldungen, alle escalated=True.
- hub/laufzeit/agent-register.jsonl: 1095 Ereignisse fuer Sitzung d695fd29 --
  bestaetigt "hunderte Werkzeugaufrufe".
- Manueller Aufruf von eilmeldung_hook.py mit echtem Payload (session_id =
  volle Sitzungskennung) lieferte KEINE Ausgabe, weil next_due_call (5747..5833)
  noch nicht erreicht war -- korrektes Backoff-Verhalten, kein Fehler.
- Testsitzung "testreplay-999" (fabriziert, keine Beruehrung der echten
  Zustandsdatei): erster Aufruf lieferte sofort alle sechs frischen
  "dringend"-Texte plus Quittierhinweis auf stdout -- der Haken FUNKTIONIERT.
- Entscheidender Test: echte Zustandsdatei kopiert (Backup), next_due_call
  aller 10 Meldungen testweise auf 0 gesetzt, danach ein GANZ NORMALER
  Werkzeugaufruf (Bash "echo probe-marker...") ueber den Harness ausgefuehrt --
  NICHT manuell gepiped. Die Zustandsdatei zeigte danach delivered+1 fuer alle
  10 Meldungen (Haken hat also gefeuert UND print() ausgefuehrt), aber im
  Werkzeug-Ergebnis dieses Aufrufs erschien KEIN Zeichen der Meldungen.
  Zustandsdatei danach aus dem Backup wiederhergestellt.

Ergebnis: (b) trifft zu -- der Haken laeuft, schreibt korrekt, druckt auf
stdout, aber die stdout-Ausgabe eines PostToolUse-Hooks (matcher: alle
Werkzeuge) wird vom Klienten in diesem Kanal NICHT in den Faden eingespielt.
(a) trifft NICHT zu -- der Haken bricht nicht ab, laeuft nachweislich mit.
(c) trifft NICHT zu -- keine Meldung ist faelschlich als zugestellt markiert;
alle 10 haben acked=False, delivered waechst nur, weil der Haken sie fuer
"gesehen" haelt (das ist seine Definition von delivered, nicht von acked).

Diese Datei ist NUR die Dokumentation der Messschritte, kein Test-Framework.
Ausfuehrbar (python3 eilmeldung_verlust_2026-08-13.py) zeigt die wichtigsten
Schritte erneut, nicht-destruktiv (eigene Test-Sitzungskennung, kein Zugriff
auf die echte Zustandsdatei).
"""
import json
import os
import subprocess
import sys

HOOK = "/Volumes/daten/Begod2026/hub/scripts/eilmeldung_hook.py"


def replay(session_id: str) -> tuple[str, str, int]:
    payload = json.dumps({"session_id": session_id, "tool_name": "Bash",
                           "tool_input": {}, "tool_response": {}})
    p = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    return p.stdout, p.stderr, p.returncode


def main() -> None:
    sid = "messauftrag-selbsttest-eilmeldung"
    state_path = f"/tmp/claude-eilmeldung-{sid}.json"
    try:
        os.remove(state_path)
    except FileNotFoundError:
        pass

    out1, err1, rc1 = replay(sid)
    print("Erster Aufruf (neue Testsitzung, sollte faellige dringend-Zeilen liefern):")
    print(f"  exit={rc1} stderr={err1!r}")
    print(f"  stdout hat {len(out1.splitlines())} Zeile(n)" if out1 else "  stdout LEER")

    out2, err2, rc2 = replay(sid)
    print("Zweiter Aufruf (Backoff greift, sollte leer sein):")
    print(f"  exit={rc2} stdout hat {len(out2.splitlines())} Zeile(n)")

    try:
        os.remove(state_path)
    except FileNotFoundError:
        pass

    assert rc1 == 0 and rc2 == 0, "Haken darf nie mit Fehlercode enden (Ausfallregel im Skriptkopf)"
    assert out1.strip() != "", "erster Aufruf einer neuen Sitzung muss faellige Meldungen zeigen, sonst ist der Haken kaputt"
    print("Selbsttest gruen: Haken produziert Ausgabe, wenn etwas faellig ist.")


if __name__ == "__main__":
    main()
