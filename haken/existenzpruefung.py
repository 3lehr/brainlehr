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

STAND 2026-08-08T15:35 — GEBAUT, GEPRUEFT, NICHT VERDRAHTET.

Der erste echte Lauf gegen dieses Gespraech zeigt, dass die Erkennung der
Verneinung TRAEGT (sie fand "Der Hook, den du meinst, fehlt tatsaechlich"),
die SUCHE danach aber unbrauchbar ist: `bestand_fragen` nimmt nur das erste
Wort der Anfrage, und nach der Laengensortierung ist das oft ein Fuellwort
wie "tatsaechlich". Ergebnis waren drei zufaellige Treffer aus fahrtenbuch,
openlehr und der WEG-Verwalterwahl -- zu einer Frage ueber Hooks.

Ein Melder mit dieser Trefferqualitaet wird nach drei Tagen ueberlesen, und
dann schadet er mehr als er nutzt: er erzeugt das Gefuehl, geprueft zu haben.
Deshalb steht er hier, ist getestet, und ist NICHT in settings.json
eingetragen. Was fehlt, bevor er das wird:
  * Suche ueber ALLE Begriffe statt nur des ersten (FTS statt LIKE auf Wort 1)
  * Mindestguete: ein Treffer zaehlt erst ab einer Uebereinstimmung, die ueber
    ein einzelnes Wort hinausgeht
  * Gegenprobe an einem Fall, dessen richtige Antwort bekannt ist -- etwa der
    Satz ueber die duennen Protokolldaten, zu dem `runs/pruefkorpus_v3.json`
    die richtige Fundstelle waere

IMMER exit 0. Kein Transcript / keine DB / kein Treffer -> still.
"""
from __future__ import annotations

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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
