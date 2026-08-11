#!/usr/bin/env python3
"""Richtet eine brainlehr-Instanz ein und BELEGT am Ende, dass sie antwortet.

Ohne Argumente: leere, regelbewehrte Datenbank plus die Selbstbeschreibung --
danach beantwortet die Instanz "was kannst du" aus dem eigenen Bestand, ohne
dass eine einzige fremde Zeile eingespielt wurde.

Der letzte Schritt ist kein Schmuck. Ein Einrichtungsskript, das "fertig"
meldet, ohne den Gegenstand zu betreten, belegt nichts (L-d8d970). Darum
fragt dieses Skript zum Schluss die frische Instanz und endet mit Fehlercode,
wenn sie schweigt.

    python3 schnellstart.py                     # Kern, ohne fremdes Wissen
    python3 schnellstart.py --bestand           # + mitgelieferter Beispielbestand
    python3 schnellstart.py --bestand --vektoren # + Bedeutungssuche (dauert)
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

import argparse
import os
import subprocess
import sys
from pathlib import Path

import ort  # noqa: E402 -- liefert DB, siehe haken/ort.py (L-6c6661)

HIER = Path(__file__).resolve().parent
DB = ort.DB
BESTAND = HIER / "auszug-offen" / "bestand.jsonl"

# Womit belegt wird, dass die Instanz ueber sich selbst Auskunft gibt.
# Bewusst die Frage eines Fremden, nicht ein Fachbegriff aus dem Bestand.
PROBEFRAGE = "was kannst du"


def _lauf(*teile: str, umgebung: dict | None = None) -> tuple[int, str]:
    """Ruft ein mitgeliefertes Werkzeug. Gibt Code und die letzte Zeile."""
    e = dict(os.environ)
    e["BEGOD_KNOWLEDGE_DB"] = str(DB)
    if umgebung:
        e.update(umgebung)
    p = subprocess.run([sys.executable, *teile], cwd=HIER, env=e,
                       capture_output=True, text=True)
    letzte = (p.stdout.strip().splitlines() or [""])[-1]
    if p.returncode != 0:
        letzte = (p.stderr.strip().splitlines() or [letzte])[-1]
    return p.returncode, letzte


def _schritt(nr: int, von: int, was: str) -> None:
    print(f"\n[{nr}/{von}] {was}", flush=True)


def _probe() -> int:
    """Fragt die frische Instanz. Rueckgabe: Zahl der Treffer."""
    os.environ["BEGOD_KNOWLEDGE_DB"] = str(DB)
    sys.path.insert(0, str(HIER))
    import knowledge_mcp_server as server  # erst hier, DB-Pfad muss stehen

    ergebnis = server.knowledge_search(PROBEFRAGE)
    treffer = ergebnis.get("results") or []
    for t in treffer[:3]:
        print(f"      - {t.get('title', '')[:64]}")
    return len(treffer)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--bestand", action="store_true",
                   help="den mitgelieferten Beispielbestand einspielen")
    p.add_argument("--vektoren", action="store_true",
                   help="Bedeutungssuche rechnen (lokal, dauert je nach Geraet Minuten)")
    a = p.parse_args()

    schritte = 2 + int(a.bestand) + int(a.vektoren) + 1
    nr = 0

    nr += 1
    _schritt(nr, schritte, "Datenbank anlegen")
    if DB.exists():
        print(f"      {DB.name} liegt bereits -- unangetastet")
    else:
        code, zeile = _lauf("brainlehr.py", "init", str(DB))
        if code != 0:
            print(f"      FEHLGESCHLAGEN: {zeile}")
            return 1
        print(f"      {zeile}")

    if a.bestand:
        nr += 1
        _schritt(nr, schritte, "Beispielbestand einspielen (muss vor allem anderen kommen -- brainlehr.py rein besteht auf einer leeren Datenbank)")
        if not BESTAND.exists():
            print(f"      uebersprungen: {BESTAND} fehlt")
        else:
            code, zeile = _lauf("brainlehr.py", "rein", str(BESTAND), "--db", str(DB))
            print(f"      {zeile}" if code == 0 else f"      FEHLGESCHLAGEN: {zeile}")
            if code != 0:
                return 1

    nr += 1
    _schritt(nr, schritte, "Selbstbeschreibung anlegen (brainlehr ueber brainlehr)")
    code, zeile = _lauf("melder/selbstbeschreibung.py", "--anlegen")
    if code != 0:
        print(f"      FEHLGESCHLAGEN: {zeile}")
        return 1
    print(f"      {zeile}")

    if a.vektoren:
        nr += 1
        _schritt(nr, schritte, "Bedeutungssuche rechnen -- das dauert")
        code, zeile = _lauf("kern/build_embeddings.py")
        print(f"      {zeile}" if code == 0 else f"      FEHLGESCHLAGEN: {zeile}")
        if code != 0:
            print("      Die Volltextsuche arbeitet auch ohne. Kein Abbruch.")

    nr += 1
    _schritt(nr, schritte, f"Gegenprobe: die frische Instanz nach {PROBEFRAGE!r} fragen")
    treffer = _probe()
    if treffer == 0:
        print(f"\n  ROT: die Instanz antwortet nicht auf {PROBEFRAGE!r}.")
        print("  Sie ist eingerichtet, aber stumm ueber sich selbst --")
        print("  das ist ein Fehler, keine Geschmacksfrage. Nicht weiterverwenden.")
        return 1

    print(f"      {treffer} Treffer -- die Instanz gibt ueber sich selbst Auskunft")

    print(f"""
FERTIG. Naechster Schritt: den Sprachmodell-Client anschliessen.

  Eintrag fuer die MCP-Konfiguration (Claude Desktop, Claude Code, ChatGPT):

    "brainlehr": {{
      "command": "{sys.executable}",
      "args": ["{HIER / 'knowledge_mcp_server.py'}"]
    }}

  Danach START_HIER.md an das Modell geben -- darin steht, was es mit
  diesem Speicher anfangen soll.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
