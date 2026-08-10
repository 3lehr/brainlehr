#!/usr/bin/env python3
"""doctor — sucht, was still kaputt ist.

    python3 doctor.py

Die Auswahl der Proben ist nicht ausgedacht: jede hat am 2026-08-08 einen
echten Befund gehabt, und jeder davon war vorher unsichtbar. Das ist der
Massstab fuer alles, was hier spaeter dazukommt -- eine Probe, die noch nie
etwas gefunden hat und auch nicht sagen kann, was sie faende, gehoert nicht
hierher.

    Regelgleichheit      Erstanlage trug 2 Trigger, 6 Tabellen, 2 Spalten
                         weniger als der Betrieb -- darunter die Herkunfts-
                         schranke. Ein Klon bekam brainlehr ohne die Regel,
                         die brainlehr ist.
    Tote Pfade           Konfigurationen zeigen auf Dateien, die es nicht
                         mehr gibt. Hooks enden auf "|| true" und fallen
                         darum LAUTLOS aus.
    Schreibbarkeit       Ein abgewiesenes Update liess eine Transaktion
                         offen; die Datenbank war fuer jeden Schreiber
                         gesperrt, bis der Prozess starb.
    Verwaiste Funktionen Definiert, nirgends gerufen. Toter Code, den
                         niemand vermisst und jeder mitliest.
    Bestandshygiene      Knoten ohne Vektor, abgelaufene Normen, Lehren
                         ohne Pruefstelle.

Rueckgabewert 0 = nichts gefunden, 1 = Befunde. Damit taugt es als Tor.
"""
from __future__ import annotations

import sys as _sys
import json
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

import ast
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

WURZEL = _w
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))
import ort  # noqa: E402  -- EINE Stelle entscheidet, wo der Verbund liegt

BEFUNDE: list[tuple[str, str]] = []


def befund(bereich: str, text: str) -> None:
    BEFUNDE.append((bereich, text))


def abschnitt(name: str) -> None:
    print(f"\n— {name}")


# ---------------------------------------------------------------- Regeln

def probe_regelgleichheit() -> None:
    abschnitt("Regelgleichheit: Erstanlage gegen Betrieb")
    import knowledge_mcp_server as kms
    betrieb_pfad = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "knowledge.db"))
    if not betrieb_pfad.exists():
        print("  keine Betriebsdatenbank an diesem Ort — uebersprungen")
        return
    import tempfile
    neu = sqlite3.connect(str(Path(tempfile.mkdtemp()) / "neu.db"))
    kms.ensure_schema(neu)
    betrieb = sqlite3.connect(f"file:{betrieb_pfad}?mode=ro", uri=True)

    def bild(c):
        d = {}
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if t.startswith(("lost_and_found", "mycel_")) or "_fts" in t:
                continue
            d[t] = {r[1] for r in c.execute(f"PRAGMA table_info({t})")}
        return d

    def trigger(c):
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}

    b, n = bild(betrieb), bild(neu)
    fehlt_t = sorted(set(b) - set(n))
    fehlt_s = {t: sorted(b[t] - n[t]) for t in set(b) & set(n) if b[t] - n[t]}
    fehlt_tr = sorted(trigger(betrieb) - trigger(neu))
    for x in fehlt_t:
        befund("regeln", f"Tabelle fehlt einer Erstanlage: {x}")
    for t, sp in fehlt_s.items():
        befund("regeln", f"Spalten fehlen einer Erstanlage: {t}.{', '.join(sp)}")
    for x in fehlt_tr:
        befund("regeln", f"Trigger fehlt einer Erstanlage: {x}")
    print(f"  Trigger {len(trigger(neu))} neu / {len(trigger(betrieb))} Betrieb · "
          f"Tabellen {len(n)} / {len(b)}"
          + ("  ok" if not (fehlt_t or fehlt_s or fehlt_tr) else "  ABWEICHUNG"))
    neu.close()
    betrieb.close()


# ----------------------------------------------------------- tote Pfade

KONFIGURATIONEN = (
    Path.home() / ".claude" / "settings.json",
    Path.home() / ".claude.json",
)


def probe_tote_pfade() -> None:
    abschnitt("Tote Pfade in Konfigurationen")
    muster = re.compile(r"(/[\w./-]+\.(?:py|sh|sql))")
    geprueft = tot = 0
    for datei in KONFIGURATIONEN:
        if not datei.exists():
            continue
        text = datei.read_text(encoding="utf-8", errors="replace")
        for pfad in sorted(set(muster.findall(text))):
            # Nur Pfade des eigenen Verbunds pruefen; fremde Eintraege in
            # derselben Konfigurationsdatei gehen uns nichts an.
            if str(ort.VERBUND) not in pfad:
                continue
            geprueft += 1
            if not Path(pfad).exists():
                tot += 1
                befund("pfade", f"{datei.name} nennt {pfad} — existiert nicht")
    print(f"  {geprueft} Pfade geprueft, {tot} tot"
          + ("" if tot else "  ok"))
    if tot:
        print("  (Hooks enden auf '|| true' und fallen lautlos aus — ein toter"
              " Pfad meldet sich nie von selbst)")


# ------------------------------------------------------- Schreibbarkeit

def probe_schreibbarkeit() -> None:
    abschnitt("Schreibbarkeit der Datenbank")
    db = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "knowledge.db"))
    if not db.exists():
        print("  keine Datenbank — uebersprungen")
        return
    t = time.time()
    c = sqlite3.connect(str(db), timeout=5)
    c.execute("PRAGMA busy_timeout=5000")
    try:
        c.execute("CREATE TABLE IF NOT EXISTS _doctor_probe (x)")
        c.commit()
        c.execute("DROP TABLE _doctor_probe")
        c.commit()
        print(f"  schreibbar nach {time.time() - t:.1f}s  ok")
    except sqlite3.OperationalError as e:
        befund("sperre", f"nicht schreibbar ({e}) — haelt ein Prozess eine offene "
                         f"Transaktion? Erst die EIGENEN pruefen: lsof {db}")
    finally:
        c.close()
    unversehrt = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    if unversehrt.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        befund("unversehrtheit", "PRAGMA integrity_check schlaegt an")
    unversehrt.close()


# -------------------------------------------------- verwaiste Funktionen

def probe_verwaiste_funktionen() -> None:
    abschnitt("Verwaiste Funktionen (definiert, nirgends gerufen)")
    dateien = [p for p in WURZEL.rglob("*.py")
               if ".git" not in p.parts and "__pycache__" not in p.parts]
    definiert: dict[str, Path] = {}
    benutzt: set[str] = set()
    for p in dateien:
        try:
            baum = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            befund("syntax", f"{p.relative_to(WURZEL)} laesst sich nicht lesen")
            continue
        in_klasse = {n for k in ast.walk(baum) if isinstance(k, ast.ClassDef)
                     for n in ast.walk(k) if isinstance(n, ast.FunctionDef)}
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.FunctionDef) and knoten not in in_klasse:
                # Methoden, Test- und Sonderfunktionen zaehlen nicht: sie werden
                # vom Rahmenwerk gerufen, nicht vom Code.
                if not knoten.name.startswith(("test_", "_", "main")):
                    definiert.setdefault(knoten.name, p)
            elif isinstance(knoten, ast.Name):
                benutzt.add(knoten.id)
            elif isinstance(knoten, ast.Attribute):
                benutzt.add(knoten.attr)
    # Namen, die nur in Zeichenketten stehen (Werkzeugtabellen, Hook-Namen),
    # gelten als benutzt -- sonst meldet der Doktor jede MCP-Werkzeugfunktion.
    volltext = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in dateien)
    verwaist = sorted(n for n, p in definiert.items()
                      if n not in benutzt and f'"{n}"' not in volltext
                      and f"'{n}'" not in volltext)
    for n in verwaist:
        befund("toter-code", f"{definiert[n].relative_to(WURZEL)}: {n}() wird nirgends gerufen")
    print(f"  {len(definiert)} oeffentliche Funktionen, {len(verwaist)} verwaist"
          + ("" if verwaist else "  ok"))


# ---------------------------------------------------- Bestandshygiene

def probe_bestand() -> None:
    abschnitt("Bestandshygiene")
    db = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "knowledge.db"))
    if not db.exists():
        print("  keine Datenbank — uebersprungen")
        return
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    eins = lambda s: c.execute(s).fetchone()[0]  # noqa: E731
    # knowledge_embeddings zeigt ueber (kind, ref_id) auf Knoten UND Lehren --
    # nicht ueber eine node_id. Ein Fan-out je Projekt ist Absicht, deshalb
    # wird auf Existenz geprueft und nicht gezaehlt.
    ohne_vektor = eins("""SELECT count(*) FROM knowledge_nodes n
                          WHERE coalesce(n.zurueckgezogen,0)=0
                            AND NOT EXISTS (SELECT 1 FROM knowledge_embeddings e
                                            WHERE e.kind='node' AND e.ref_id = n.id)""")
    abgelaufen = eins("SELECT count(*) FROM knowledge_nodes "
                      "WHERE gilt_bis IS NOT NULL AND gilt_bis < date('now')")
    offen = eins("SELECT count(*) FROM knowledge_nodes "
                 "WHERE norm_entscheidung='offen' AND norm_rang IS NOT NULL")
    gesamt = eins("SELECT count(*) FROM knowledge_nodes")
    print(f"  {gesamt} Knoten · {ohne_vektor} ohne Vektor · {abgelaufen} abgelaufen · "
          f"{offen} mit Rang aber unentschieden")
    if ohne_vektor:
        befund("bestand", f"{ohne_vektor} Knoten ohne Vektor — build_embeddings.py laeuft "
                          f"nicht mehr durch oder ist nach einem Umzug faellig")
    if abgelaufen:
        befund("bestand", f"{abgelaufen} Norm(en) sind abgelaufen und stehen weiter im Bestand")
    if offen:
        befund("bestand", f"{offen} Knoten tragen einen Rang, aber keine Entscheidung")
    c.close()


def probe_melder_ohne_ausloeser() -> None:
    """Kann jeder verdrahtete Melder ueberhaupt feuern?

    Anlass 2026-08-10: sichtbarkeit.py meldete Lese- UND Schreibvorgaenge,
    sein Haken hatte aber nur die Schreibwerkzeuge im Matcher stehen. Der
    Melder war fehlerfrei, lief nie, und niemand sah es -- der Aufruf endet
    auf '2>/dev/null || true'. Vier Stunden Suche an der falschen Stelle
    (Verdichtung? Arbeitsbaum? Anmeldung?), waehrend die Ursache in einer
    Zeile Konfiguration stand.

    Diese Probe vergleicht, WAS ein Melder anzeigen will, mit dem, WORAUF er
    gestartet wird. Sie ist die einzige Stelle, an der eine Luecke zwischen
    beiden sichtbar wird -- ein Melder ohne Ausloeser sieht in jedem Test
    gesund aus, weil an ihm selbst nichts fehlt.
    """
    abschnitt("Melder ohne Ausloeser")
    import re

    einstellungen = Path.home() / ".claude" / "settings.json"
    if not einstellungen.exists():
        print("  keine ~/.claude/settings.json  uebersprungen")
        return

    try:
        daten = json.loads(einstellungen.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        befund("melder", f"~/.claude/settings.json ist kein gueltiges JSON: {e}")
        return

    # Aktionsname im Protokoll -> Werkzeugname am MCP-Server. Nur die, bei
    # denen beide auseinanderfallen; alles andere heisst gleich.
    WERKZEUG = {"add": "knowledge_add", "update": "knowledge_update",
                "lesson": "lesson_record", "search": "knowledge_search",
                "read": "knowledge_read", "browse": "knowledge_browse"}

    geprueft = 0
    # Nur Haltepunkte, die ueberhaupt auf Werkzeuge matchen. SessionStart
    # und Stop tragen einen Anlass-Matcher ("compact") oder gar keinen --
    # dort ist ein fehlender Werkzeugname kein Mangel, sondern die Bauform.
    for haltepunkt, gruppen in daten.get("hooks", {}).items():
        if haltepunkt not in ("PreToolUse", "PostToolUse"):
            continue
        for gruppe in gruppen:
            matcher = gruppe.get("matcher") or ""
            for h in gruppe.get("hooks", []):
                befehl = str(h.get("command", ""))
                treffer = re.search(r"([a-z_0-9]+)\.py\b", befehl)
                if not treffer or "sichtbarkeit" not in befehl:
                    continue
                quelle = next((q for q in WURZEL.rglob(f"{treffer.group(1)}.py")
                               if ".claude" not in q.parts), None)
                if quelle is None:
                    continue
                geprueft += 1
                text = quelle.read_text(encoding="utf-8")
                gemeldet: set[str] = set()
                for feld in ("LESE_AKTIONEN", "SCHREIB_AKTIONEN"):
                    block = re.search(feld + r"\s*=\s*\{(.*?)\}", text, re.S)
                    if block:
                        gemeldet |= set(re.findall(r'"([a-z_]+)"', block.group(1)))
                fehlend = sorted(
                    w for a in gemeldet
                    if (w := WERKZEUG.get(a, a)) not in matcher)
                if fehlend:
                    befund("melder", f"{quelle.name} meldet {len(fehlend)} Vorgangsart(en), "
                           f"auf die sein {haltepunkt}-Haken nie startet: "
                           f"{', '.join(fehlend[:6])}")
                else:
                    print(f"  {quelle.name}: Matcher deckt alles ab, was er meldet  ok")

    if not geprueft:
        print("  kein verdrahteter Melder gefunden  uebersprungen")


def main() -> int:
    print("doctor — brainlehr")
    print(f"Ort: {WURZEL}")
    for probe in (probe_regelgleichheit, probe_tote_pfade, probe_schreibbarkeit,
                  probe_verwaiste_funktionen, probe_bestand,
                  probe_melder_ohne_ausloeser):
        try:
            probe()
        except Exception as e:  # eine kaputte Probe darf den Rest nicht verhindern
            befund("doctor", f"{probe.__name__} selbst gescheitert: {e}")

    print()
    if not BEFUNDE:
        print("Keine Befunde.")
        return 0
    print(f"{len(BEFUNDE)} Befund(e):")
    for bereich, text in BEFUNDE:
        print(f"  [{bereich}] {text}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
