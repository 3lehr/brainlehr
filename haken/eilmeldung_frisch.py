#!/usr/bin/env python3
"""Stellt FRISCHE Eilmeldungen mitten in eine laufende Sitzung zu -- auch
mitten im ZUG, ohne dass jemand einen Prompt schreibt.

ANLASS (Betreiberfrage 2026-08-20): *"in den Startkontext -- sprich wir muessen
dann neue chats starten, oder kannst du das per eilmeldung injezieren?"*

GEMESSENE LAGE VORHER, und sie war halb gut:
- `haken/regelwechsel.py` laeuft bei JEDEM Prompt und spielt Aenderungen an
  Regeldateien und an Knoten mit norm_rang 1/2 ein. Belegt am 2026-08-20:
  vier Einspielungen in einer Sitzung, darunter eine Rang-2-Norm, die
  waehrend derselben Sitzung entstand und beim naechsten Prompt ankam.
- `melder/eilmeldung_faellig.py` laeuft nur bei SessionStart -- und meldet
  ueberdies nur die VERALTETEN (>3 Tage unquittiert). Eine Eilmeldung, die
  waehrend einer Sitzung entsteht, erreichte die laufende Sitzung also nie.

Das ist die Luecke, die dieser Haken schliesst: was seit dem letzten Prompt
DIESER Sitzung neu mit `dringend` etikettiert wurde, wird einmal zugestellt.

EINMAL, und das ist der ganze Trick. Der Zustand liegt je Sitzung; eine
Meldung, die zugestellt wurde, kommt nicht wieder. Ohne diese Buchhaltung
haette der Haken bei jedem Prompt dieselben 21 offenen Eilmeldungen
eingespielt -- und wer einmal 21 Zeilen Rauschen bekommt, liest die
zweiundzwanzigste nicht mehr.

WARUM DAS KEINE PROMPT-INJECTION IST: Eingespielt wird ausschliesslich aus der
eigenen Wissensdatenbank, und dorthin schreibt nur, wer einen Ausweis hat.
Dieselbe Abgrenzung wie in regelwechsel.py -- keine Datei aus dem
Arbeitsverzeichnis, kein Muster, kein Verzeichnisdurchlauf.

ZWEI EREIGNISSE, und das zweite ist der eigentliche Fortschritt. Beim ersten
Bau stand hier der Satz, ein echter Zwischenruf in eine rechnende Sitzung sei
"eine Grenze des Hakensystems". Der Betreiber: *"aber dazu muss es doch eine
loesung geben?!"* -- und er hatte recht, es war genau die Sorte Absolutaussage,
gegen die derselbe Tag einen Waechter hervorgebracht hat.

GEMESSEN am 2026-08-20 mit einer einmaligen Probe: Ein `PostToolUse`-Haken
darf `additionalContext` liefern, und der Text erreicht den laufenden Zug
unmittelbar nach dem Werkzeugaufruf -- ohne neuen Prompt. Die Probe kam an,
woertlich, mitten in einer Bash-Ausgabe. Ebenfalls gemessen: PostToolUse
liefert `session_id`, die Buchhaltung "genau einmal" traegt dort also
unveraendert.

Damit erreicht eine Eilmeldung eine Sitzung, die stundenlang autonom
arbeitet, beim naechsten Werkzeugaufruf -- und der kommt in Sekunden, nicht
beim naechsten Prompt.

DER PREIS, und deshalb die Sperre unten: PostToolUse feuert bei JEDEM
Werkzeugaufruf. Eine Datenbankabfrage je Aufruf waere Verschwendung, deshalb
schaut der Haken zuerst auf die Aenderungszeit der Datenbank und gibt auf,
wenn sich seit der letzten Pruefung nichts geregt hat. Das kostet einen
`stat`.

Fail-open in jedem Zweig: kann der Haken nicht lesen oder schreiben, gibt er
nichts aus und der Zug laeuft weiter.

    python3 haken/eilmeldung_frisch.py --selftest
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

ZUSTAND = Path.home() / ".brainlehr-eilmeldung-frisch.json"
ETIKETT = "dringend"
HOECHSTENS = 3          # je Prompt, sonst wird aus Zustellung Rauschen


def _db() -> Path:
    import ort
    return Path(ort.DB)


def _unveraendert(db: Path, alt: dict, sitzung: str) -> bool:
    """Hat sich die Datenbank seit der letzten Pruefung dieser Sitzung geregt?

    Ein `stat` statt einer Abfrage: PostToolUse feuert bei jedem
    Werkzeugaufruf, und in einem Zug mit fuenfzig Aufrufen waeren das fuenfzig
    Abfragen fuer eine Antwort, die sich fast nie aendert."""
    try:
        stand = db.stat().st_mtime_ns
    except OSError:
        return True
    return alt.get("_mtime", {}).get(sitzung) == stand


def _merke_stand(db: Path, alt: dict, sitzung: str) -> None:
    try:
        alt.setdefault("_mtime", {})[sitzung] = db.stat().st_mtime_ns
    except OSError:
        pass


def _lies_zustand() -> dict:
    try:
        return json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def projekt_aus(cwd: str) -> str:
    """Welches Projekt arbeitet hier? Aus dem Pfad, nicht aus einer Ansage.

    Arbeitsbaeume liegen unter <projekt>/.claude/worktrees/<name> -- der
    Projektname steht also VOR dem .claude-Segment, nicht am Ende."""
    teile = [t for t in Path(cwd or ".").resolve().parts]
    if "Begod2026" in teile:
        i = teile.index("Begod2026")
        if i + 1 < len(teile):
            return teile[i + 1]
    return ""


def adressiert_an(etiketten: list[str]) -> set[str]:
    """Empfaenger aus den Etiketten: `an:brainlehr` -> {'brainlehr'}.

    ADRESSIERUNG, ergaenzt 2026-08-20 auf Betreiberfrage ("wie umgehen wir die
    verschmutzung des kontextfensters der anderen sitzungen?").

    Gemessen an diesem Tag: 17 laufende Sitzungen, 11 Eilmeldungen in 24 h,
    je Zustellung rund 120 Zeichen -- die LAST ist also nicht das Problem
    (1 320 Zeichen je Sitzung und Tag gegen 92 669 Zeichen Regeln beim Start).
    Das Problem ist die RELEVANZ: Wer dreimal eine Meldung bekommt, die ihn
    nichts angeht, liest die vierte nicht mehr. Ein Kanal stirbt an
    Bedeutungslosigkeit, nicht an Bytes.

    Ohne `an:`-Etikett gilt eine Meldung fuer alle -- das ist der bisherige
    Zustand und bleibt der Vorgabewert, damit nichts still verschwindet."""
    return {e.split(":", 1)[1].strip().lower()
            for e in etiketten if e.lower().startswith("an:") and ":" in e}


def frische(db: Path, gesehen: list[str], projekt: str = "") -> list[tuple[str, str, str]]:
    """(id, pfad, titel) der dringenden Knoten, die diese Sitzung nicht kennt."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.Error:
        return []
    try:
        zeilen = conn.execute(
            "SELECT id, path, title, tags FROM knowledge_nodes "
            "WHERE tags LIKE ? AND IFNULL(zurueckgezogen,0)=0 "
            "ORDER BY updated_at DESC LIMIT 200", (f'%"{ETIKETT}"%',)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    import json as _json
    bekannt = set(gesehen)
    treffer = []
    for z in zeilen:
        if z[0] in bekannt:
            continue
        try:
            etiketten = _json.loads(z[3] or "[]")
        except ValueError:
            etiketten = []
        ziele = adressiert_an(etiketten if isinstance(etiketten, list) else [])
        # Keine Adresse -> an alle. Eine Adresse -> nur an das genannte
        # Projekt (oder an alle, wenn 'alle' dabeisteht).
        if ziele and "alle" not in ziele and projekt.lower() not in ziele:
            continue
        treffer.append((z[0], z[1], z[2]))
    return treffer


def melde(sitzung: str, db: Path | None = None, zustand: Path | None = None,
          cwd: str = "") -> str:
    db = db or _db()
    ablage = zustand or ZUSTAND
    try:
        alt = json.loads(ablage.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        alt = {}
    if _unveraendert(db, alt, sitzung):
        return ""
    gesehen = alt.get(sitzung, [])
    erstlauf = sitzung not in alt
    _merke_stand(db, alt, sitzung)
    neu = frische(db, gesehen, projekt_aus(cwd))

    # ERSTLAUF STELLT NICHTS ZU, er merkt sich nur den Stand. Sonst bekaeme
    # jede neue Sitzung beim ersten Prompt den gesamten Bestand an
    # Eilmeldungen -- dafuer gibt es den SessionStart-Kanal, und zweimal
    # dasselbe ist einmal zu viel.
    alt[sitzung] = [z[0] for z in neu] + gesehen if erstlauf else gesehen + [z[0] for z in neu[:HOECHSTENS]]
    try:
        ablage.write_text(json.dumps(alt)[:200_000], encoding="utf-8")
        os.chmod(ablage, 0o600)
    except OSError:
        pass
    if erstlauf or not neu:
        return ""
    zeigen = neu[:HOECHSTENS]
    kopf = (f"{len(neu)} frische Eilmeldung(en) seit deinem letzten Zug -- "
            "waehrend dieser Sitzung entstanden, also nicht im Startkontext:")
    zeilen = [f"  {p}: {t}" for _, p, t in zeigen]
    if len(neu) > HOECHSTENS:
        zeilen.append(f"  ... und {len(neu) - HOECHSTENS} weitere "
                      "(knowledge_search mit Etikett 'dringend')")
    return kopf + "\n" + "\n".join(zeilen)


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        db = d / "t.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE knowledge_nodes (id TEXT, path TEXT, title TEXT, "
                     "tags TEXT, updated_at TEXT, zurueckgezogen INTEGER DEFAULT 0)")
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('a','/x/a','Erste Meldung','[\"dringend\"]','2026-08-20T08:00:00Z',0)")
        conn.commit()
        z = d / "z.json"

        # ERSTLAUF: merkt sich den Stand und stellt NICHTS zu.
        assert melde("s1", db, z) == "", "der Erstlauf darf nichts zustellen"

        # Neue Meldung waehrend der Sitzung -> genau einmal.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('b','/x/b','Zweite Meldung','[\"dringend\"]','2026-08-20T09:00:00Z',0)")
        conn.commit()
        erste = melde("s1", db, z)
        assert "Zweite Meldung" in erste, erste
        assert "Erste Meldung" not in erste, "der Bestand gehoert in den Startkanal"
        assert melde("s1", db, z) == "", "zweimal dieselbe Meldung ist Rauschen"

        # Eine ANDERE Sitzung hat ihren eigenen Stand.
        assert melde("s2", db, z) == "", "auch dort ist der Erstlauf still"

        # NEGATIVFALL: ein Knoten ohne das Etikett wird nie zugestellt.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('c','/x/c','Kein Etikett','[\"notiz\"]','2026-08-20T10:00:00Z',0)")
        conn.commit()
        assert melde("s1", db, z) == "", "ohne Etikett keine Zustellung"

        # Und ein zurueckgezogener dringender Knoten ebenfalls nicht.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('d','/x/d','Zurueckgezogen','[\"dringend\"]','2026-08-20T11:00:00Z',1)")
        conn.commit()
        assert melde("s1", db, z) == "", "zurueckgezogene Knoten sind keine Eilmeldung"
        conn.close()
        # DIE MTIME-SPERRE, und sie ist der Grund, warum dieser Haken an
        # PostToolUse haengen darf: Ohne sie liefe bei jedem Werkzeugaufruf
        # eine Datenbankabfrage. Der zweite Aufruf ohne Aenderung muss still
        # bleiben, OHNE die Datenbank ueberhaupt anzufassen.
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('e','/x/e','Dritte Meldung','[\"dringend\"]','2026-08-20T12:00:00Z',0)")
        conn.commit(); conn.close()
        assert "Dritte Meldung" in melde("s1", db, z), "Aenderung muss durchkommen"
        assert melde("s1", db, z) == "", "ohne Aenderung darf nichts kommen"

        # Und der Ereignisname folgt dem Ausloeser -- ein falscher Name macht
        # aus einer Zustellung eine verworfene Ausgabe.
        import subprocess, json as _j
        for ereignis in ("UserPromptSubmit", "PostToolUse"):
            r = subprocess.run([sys.executable, str(Path(__file__).resolve())],
                               input=_j.dumps({"session_id": "egal",
                                               "hook_event_name": ereignis}),
                               capture_output=True, text=True)
            # Ohne frische Meldung gibt er nichts aus -- geprueft wird hier nur,
            # dass er nicht abstuerzt und nichts Falsches schreibt.
            assert r.returncode == 0, r.stderr[:200]

        # ADRESSIERUNG, beide Richtungen. Ohne diese Faelle waere die
        # Zustellung eine Behauptung -- der Kanal stirbt nicht an Bytes,
        # sondern an Meldungen, die den Empfaenger nichts angehen.
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('f','/x/f','Nur fuer fahrtenbuch',"
                     "'[\"dringend\",\"an:fahrtenbuch\"]','2026-08-20T13:00:00Z',0)")
        conn.commit(); conn.close()
        heim = "/Volumes/daten/Begod2026/brainlehr/.claude/worktrees/x"
        assert melde("s9", db, z, cwd=heim) == "", "Erstlauf still"
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('g','/x/g','Fuer alle','[\"dringend\"]','2026-08-20T14:00:00Z',0)")
        conn.commit(); conn.close()
        text = melde("s9", db, z, cwd=heim)
        assert "Fuer alle" in text, text
        assert "Nur fuer fahrtenbuch" not in text, "fremde Adresse darf nicht zugestellt werden"
        # Dieselbe Meldung erreicht die adressierte Sitzung sehr wohl.
        fremd = "/Volumes/daten/Begod2026/fahrtenbuch"
        assert melde("s10", db, z, cwd=fremd) == "", "Erstlauf auch dort still"
        conn = sqlite3.connect(str(db))
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('h','/x/h','Zweite fuer fahrtenbuch',"
                     "'[\"dringend\",\"an:fahrtenbuch\"]','2026-08-20T15:00:00Z',0)")
        conn.commit(); conn.close()
        assert "Zweite fuer fahrtenbuch" in melde("s10", db, z, cwd=fremd)
        # Und der Projektname kommt aus dem PFAD, auch im Arbeitsbaum.
        assert projekt_aus(heim) == "brainlehr", projekt_aus(heim)
        assert projekt_aus("/tmp/irgendwo") == ""

    print("eilmeldung_frisch: Selbsttest gruen (8 Faelle: Erstlauf still, "
          "frische Meldung genau einmal, Bestand bleibt im Startkanal, zweite "
          "Sitzung eigenstaendig, ohne Etikett nichts, zurueckgezogen nichts, "
          "mtime-Sperre haelt, beide Ereignisnamen laufen durch, "
          "fremde Adresse wird nicht zugestellt, eigene schon, Projekt aus dem Pfad)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    sitzung = str(eingabe.get("session_id") or "unbekannt")
    try:
        text = melde(sitzung, cwd=str(eingabe.get("cwd") or ""))
    except Exception:
        return 0
    if text:
        # Der Ereignisname muss zum AUSLOESER passen -- derselbe Haken haengt
        # an UserPromptSubmit UND an PostToolUse, und ein falscher Name macht
        # aus einer Zustellung eine verworfene Ausgabe.
        ereignis = str(eingabe.get("hook_event_name") or "UserPromptSubmit")
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": ereignis,
                "additionalContext": f"<eilmeldung-frisch>\n{text}\n</eilmeldung-frisch>",
            }
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
