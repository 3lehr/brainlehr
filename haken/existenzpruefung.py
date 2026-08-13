#!/usr/bin/env python3
"""existenzpruefung.py — sucht nach, wenn die ANTWORT eine Existenz verneint.

DIE LUECKE, die dieser Haken schliesst (Betreiber-Befund 2026-08-08): Der
Wissensabruf haengt am `UserPromptSubmit` — er feuert also auf die FRAGE des
Betreibers. Die eigene ANTWORT loest nichts aus. Wer darin schreibt „dafuer
haben wir wohl nicht genug Daten", hat die Datenbank nie gefragt, und
niemand merkt es.

Genau das ist am selben Tag zweimal passiert:
  * „Bei rund 2000 Protokollzeilen kann das Signal zu duenn sein" — geschrieben,
    ohne zu zaehlen. Es gab `runs/pruefkorpus_v3.json` und
    `ab_vergleich_abruf.py`, beide seit Tagen, beide genau dafuer gebaut.
  * Frueher am Tag drei Faehigkeiten als fehlend gemeldet, die alle drei
    existierten (L-b9d1f3).

Der Haken liest die letzte eigene Antwort, sucht darin nach VERNEINUNGEN von
Existenz, und fragt zu jeder gefundenen Stelle den Bestand. Findet er etwas,
sagt er es — ohne zu urteilen, ob die Verneinung falsch war.

WAS ER AUSDRUECKLICH NICHT TUT: die Antwort bewerten oder korrigieren. Ein
Treffer heisst „dazu gibt es etwas", nicht „du hast dich geirrt". Die
Unterscheidung ist wichtig, weil eine Verneinung oft richtig ist und ein
Melder, der bei jeder richtigen Aussage anschlaegt, nach drei Tagen
uebergangen wird.

STAND 2026-08-08T15:35 — erster Entwurf lieferte drei zufaellige Treffer
(bestand_fragen nahm nur das erste, laengensortierte Wort). Seither auf
`knowledge_search` (FTS, alle Begriffe) umgestellt und mit dem Fall aus
`runs/pruefkorpus_v3.json` gegengeprueft.

STAND 2026-08-13: verdrahtet als `Stop`-Hook in `.claude/settings.json`
(projekteigen, nicht in `~/.claude/settings.json` -- siehe
`docs/PLAN_VERDRAHTUNG_2026-08-13.md`). Selbsttest per
`python3 haken/existenzpruefung.py --selftest`, prueft beide Richtungen
gegen main() selbst (Verneinung mit Bestandstreffer meldet, gewoehnliche
Antwort schweigt).

IMMER exit 0. Kein Transcript / keine DB / kein Treffer -> still.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ort  # ein Ort fuer den Pfad

# Verneinungen von EXISTENZ, nicht von Sachverhalten. "das stimmt nicht" soll
# nicht anschlagen, "das gibt es nicht" schon. Eng gefasst und in der eigenen
# Sprache, weil die Antworten deutsch sind.
_VERNEINUNG = re.compile(
    r"(?:gibt es (?:noch )?(?:kein|nicht)|haben wir (?:noch )?(?:kein|nicht)|"
    r"existiert (?:noch )?nicht|fehlt(?: uns| noch)?|ist nicht vorhanden|"
    r"nicht genug (?:daten|belege|beispiele)|zu duenn|dafuer fehlt|"
    r"steht nichts|keine (?:daten|belege|messung|zahlen))",
    re.IGNORECASE)

# Woraus die Suchanfrage gebaut wird: die Inhaltswoerter im Satz der
# Verneinung. Fuellwoerter raus, sonst sucht man nach "wir" und "das".
_FUELLWORT = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "und", "oder", "aber", "wir", "uns", "ist", "sind", "war", "waren", "hat",
    "haben", "wird", "werden", "kann", "koennte", "noch", "nicht", "kein",
    "keine", "es", "gibt", "fuer", "mit", "von", "zu", "im", "in", "auf",
    "dafuer", "dazu", "damit", "sich", "auch", "nur", "schon", "sein", "als",
}


def verneinungen(text: str) -> list[str]:
    """Saetze, die eine Existenz verneinen. Ein Satz je Treffer, nicht doppelt."""
    gefunden = []
    for satz in re.split(r"(?<=[.!?])\s+|\n", text or ""):
        satz = satz.strip()
        if satz and _VERNEINUNG.search(satz) and satz not in gefunden:
            gefunden.append(satz)
    return gefunden


def suchbegriffe(satz: str, hoechstens: int = 4) -> str:
    """Inhaltswoerter des Satzes als Suchanfrage.

    Laengste zuerst: in einem deutschen Satz tragen die langen Woerter die
    Sache ("Protokollzeilen", "Wirkungssignal"), die kurzen die Grammatik."""
    woerter = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß_]{4,}", satz)
               if w.lower() not in _FUELLWORT]
    woerter.sort(key=len, reverse=True)
    return " ".join(woerter[:hoechstens])


def bestand_fragen(db: Path, anfrage: str, grenze: int = 3) -> list[tuple[str, str]]:
    """Fragt den Bestand — ueber die RICHTIGE Suche, nicht ueber eine eigene.

    Der erste Entwurf baute hier ein `LIKE` auf das ERSTE Wort der Anfrage.
    Nach der Laengensortierung war das oft ein Fuellwort, und der erste echte
    Lauf lieferte drei zufaellige Treffer aus fahrtenbuch, openlehr und der
    WEG-Verwalterwahl — zu einer Frage ueber Hooks.

    Der Fehler war nicht die schlechte Abfrage, sondern dass ich sie ueberhaupt
    geschrieben habe: knowledge_search() gibt es, mit FTS5, Bedeutungssuche und
    RRF-Fusion. Dieselbe Anfrage liefert dort die drei einschlaegigen Treffer.
    Genau die Fehlerklasse, gegen die dieser Haken gebaut ist — nicht
    nachgesehen, was schon da ist (L-b9d1f3).

    `db` bleibt in der Signatur, damit Tests gegen eine eigene Datei laufen
    koennen; ist sie gesetzt und nicht die Betriebsdatenbank, wird der einfache
    Weg genommen (die Suche des Servers haengt an seiner eigenen Pfadaufloesung)."""
    if not anfrage.strip():
        return []
    if db == ort.DB:
        try:
            sys.path.insert(0, str(ort.WURZEL))
            import knowledge_mcp_server as kms
            treffer = kms.knowledge_search(anfrage, max_results=grenze).get("results", [])
            return [(t.get("path") or t.get("id", ""),
                     t.get("title") or t.get("summary", "")) for t in treffer]
        except Exception:
            return []
    try:  # Testpfad: eigene Datei, kein Server
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as c:
            c.row_factory = sqlite3.Row
            treffer = []
            for wort in anfrage.split():
                rows = c.execute(
                    "SELECT path, title FROM knowledge_nodes "
                    "WHERE title LIKE ? OR summary LIKE ? LIMIT ?",
                    (f"%{wort}%", f"%{wort}%", grenze)).fetchall()
                treffer += [(r["path"], r["title"]) for r in rows]
            return list(dict.fromkeys(treffer))[:grenze]
    except sqlite3.Error:
        return []


def letzte_antwort(transcript: Path) -> str:
    """Text der letzten Assistant-Nachricht. Robust gegen Teilzeilen."""
    letzte = ""
    try:
        with transcript.open(encoding="utf-8", errors="replace") as f:
            for zeile in f:
                try:
                    d = json.loads(zeile)
                except Exception:
                    continue
                if d.get("type") != "assistant":
                    continue
                inhalt = (d.get("message") or {}).get("content") or []
                stuecke = [t.get("text", "") for t in inhalt
                           if isinstance(t, dict) and t.get("type") == "text"]
                if stuecke:
                    letzte = "\n".join(stuecke)
    except OSError:
        return ""
    return letzte


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    pfad = payload.get("transcript_path")
    if not pfad:
        return
    antwort = letzte_antwort(Path(pfad))
    if not antwort:
        return

    meldungen = []
    for satz in verneinungen(antwort)[:3]:  # drei genuegen, sonst wird es Laerm
        treffer = bestand_fragen(ort.DB, suchbegriffe(satz))
        if treffer:
            kurz = satz if len(satz) <= 90 else satz[:87] + "..."
            meldungen.append(f'  "{kurz}"')
            meldungen += [f"    -> {p} · {t[:70]}" for p, t in treffer]

    if meldungen:
        print("NACHGEFRAGT (existenzpruefung): Zu diesen Verneinungen in deiner "
              "Antwort steht etwas im Bestand. Ein Treffer heisst nicht, dass die "
              "Aussage falsch war — nur, dass sie ungeprueft war.")
        print("\n".join(meldungen))


def _selftest() -> int:
    """Beide Richtungen gegen main() selbst, nicht nur gegen die Bausteine.

    Zwingt main() ueber einen getauschten `bestand_fragen`-Namen auf eine
    eigene Testdatenbank -- ein direktes ort.DB-Ueberschreiben wirkt nicht,
    weil main() `bestand_fragen(ort.DB, ...)` aufruft und die Funktion selbst
    `db == ort.DB` prueft: der Vergleich waere immer wahr und liefe live
    gegen den Produktivserver statt gegen Testdaten."""
    import contextlib
    import io
    import tempfile

    global bestand_fragen
    ok = True
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        db = Path(td) / "selftest.db"  # td: Wegwerfverzeichnis, kein Bestand
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE knowledge_nodes (path TEXT, title TEXT, summary TEXT)")
        c.execute("INSERT INTO knowledge_nodes VALUES "
                  "('/mess/korpus','Pruefkorpus V3 fuer den Abrufvergleich','...')")
        c.commit()
        c.close()

        # Richtung 1: Verneinung, zu der die Testdatenbank etwas hat -> muss melden.
        t_treffer = tdp / "treffer.jsonl"
        t_treffer.write_text(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text":
                "Fuer den Pruefkorpus Abrufvergleich haben wir noch keine Messdaten."}]},
        }) + "\n", encoding="utf-8")

        # Richtung 2: gewoehnliche Antwort ohne Verneinung -> muss schweigen.
        t_still = tdp / "still.jsonl"
        t_still.write_text(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text":
                "Der Testlauf ist gruen, alles wie erwartet."}]},
        }) + "\n", encoding="utf-8")

        orig_bestand_fragen = bestand_fragen
        bestand_fragen = lambda _db, anfrage, grenze=3: orig_bestand_fragen(db, anfrage, grenze)
        alt_stdin = sys.stdin
        try:
            buf1 = io.StringIO()
            sys.stdin = io.StringIO(json.dumps({"transcript_path": str(t_treffer)}))
            with contextlib.redirect_stdout(buf1):
                main()
            ausgabe1 = buf1.getvalue()

            buf2 = io.StringIO()
            sys.stdin = io.StringIO(json.dumps({"transcript_path": str(t_still)}))
            with contextlib.redirect_stdout(buf2):
                main()
            ausgabe2 = buf2.getvalue()
        finally:
            bestand_fragen = orig_bestand_fragen
            sys.stdin = alt_stdin

    treffer_ok = "NACHGEFRAGT" in ausgabe1 and "Pruefkorpus" in ausgabe1
    still_ok = ausgabe2 == ""
    ok = treffer_ok and still_ok

    print(f"Richtung 1 (Verneinung mit Bestandstreffer, muss melden): "
          f"{'OK' if treffer_ok else 'FEHLER'}")
    print(ausgabe1 or "  (keine Ausgabe -- FEHLER)")
    print(f"Richtung 2 (gewoehnliche Antwort, muss schweigen): "
          f"{'OK' if still_ok else 'FEHLER'}")
    print(ausgabe2 or "  (keine Ausgabe -- korrekt)")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
