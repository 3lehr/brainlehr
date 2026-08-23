#!/usr/bin/env python3
"""Aufbewahrungsregel fuer die automatischen Datenbanksicherungen.

DER BEFUND, 2026-08-14: 312 Sicherungsdateien, zusammen 22 GB, entstanden in
drei Tagen -- und die Platte stand bei 100 Prozent Belegung mit 9,6 GB Rest.
Ursache ist keine Nachlaessigkeit an einer Stelle, sondern eine Luecke im
Bauplan: 14 Stellen legen eine Vollkopie an (allein zehn in
knowledge_mcp_server.py, dazu kern/build_embeddings.py, kern/normbestand.py,
kern/migrate_relations.py), und KEINE einzige raeumt auf. Jede fuer sich ist
richtig -- eine Sicherung vor einem Schemaeingriff ist gute Praxis. Zusammen
sind sie ein Leck.

WARUM HIER UND NICHT AN DEN 14 STELLEN: Eine Regel, die an jeder Schreibstelle
haengt, muss vierzehnmal richtig eingebaut werden und beim naechsten
Schreibpfad ein fuenfzehntes Mal. Eine Regel, die ueber das VERZEICHNIS laeuft,
wirkt auf alle -- auch auf die, die es noch nicht gibt. Sie ist deshalb
absichtlich nicht an das Anlegen gekoppelt, sondern an den Start.

WAS SIE NICHT TUT: Sie entscheidet nicht, ob eine Sicherung wertvoll ist. Sie
kennt nur Alter und Anzahl. Eine Sicherung, die jemand aufheben will, gehoert
umbenannt -- alles ohne das Muster `<db>.bak-*` wird nie angefasst. Das ist
die Rueckfallebene fuer den Menschen, und sie ist absichtlich so grob.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

import os
from pathlib import Path

# WO die automatischen Sicherungen liegen (BDW-E15, 2026-08-19).
#
# Bis heute bildeten zwoelf Stellen in knowledge_mcp_server.py den Pfad selbst
# als `DB_PATH.parent / f"{name}.bak-{stamp}"` -- Sicherung und Bestand im
# SELBEN Verzeichnis. Ein `rm <db>*`, ein falsch gezielter Aufraeumlauf oder
# ein geleertes Verzeichnis nimmt damit beides in einem Griff mit.
#
# Was diese Zeilen loesen und was NICHT: Sie trennen das VERZEICHNIS. Einen
# anderen DATENTRAEGER kann nur der Betreiber bestimmen -- dafuer ist die
# Umgebungsvariable da, und ohne sie wird nichts erraten. Offline ist damit
# weiterhin nicht erfuellt; das steht so in der Katalogzeile.
ORT_UMGEBUNG = "BRAINLEHR_SICHERUNGSORT"
ORDNERNAME = "sicherungen"


def sicherungsordner(db_pfad: Path) -> Path:
    """Wohin neue automatische Sicherungen gehen."""
    gesetzt = os.environ.get(ORT_UMGEBUNG, "").strip()
    return Path(gesetzt) if gesetzt else Path(db_pfad).parent / ORDNERNAME


def sicherungspfad(db_pfad: Path, stempel: str) -> Path:
    """Der vollstaendige Pfad EINER neuen Sicherung. Legt den Ordner an.

    Die zwoelf Schreibstellen rufen ausschliesslich das hier -- eine
    dreizehnte, die den Pfad wieder selbst bildet, ist damit ein sichtbarer
    Sonderweg statt einer stillen Wiederholung."""
    db_pfad = Path(db_pfad)
    ordner = sicherungsordner(db_pfad)
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner / f"{db_pfad.name}{MUSTER}{stempel}"


# Wieviele der juengsten automatischen Sicherungen bleiben liegen.
# Zehn, weil eine Sicherung genau einen Zweck hat: den Schritt zurueck, der
# gerade schiefging. Wer zwanzig Schritte zurueck will, will in Wahrheit ein
# Archiv, und ein Archiv gehoert nicht neben die Betriebsdatenbank.
BEHALTE = 10

# Nur DIESE Form wird aufgeraeumt. Von Hand vergebene Namen
# (`brainlehr.db.vor_utc_2026-08-14`, `.bak-...-normherkunft`) tragen einen
# Zweck im Namen und werden NIE angefasst -- Umbenennen ist damit der Weg,
# eine Sicherung dauerhaft zu behalten.
MUSTER = ".bak-"


def _automatisch(p: Path, db_name: str) -> bool:
    """Traegt die Datei den maschinell erzeugten Zeitstempelnamen?

    `<db>.bak-20260814T113559` ja, `<db>.bak-20260814T113746-normherkunft`
    NEIN -- der Zusatz hinter dem Zeitstempel ist die Handschrift eines
    Menschen, der wusste, wofuer er sichert.
    """
    if not p.name.startswith(db_name + MUSTER):
        return False
    rest = p.name[len(db_name) + len(MUSTER):]
    return len(rest) == 15 and rest[8] == "T" and rest.replace("T", "").isdigit()


# Fruehere Namen derselben Datenbank. Die Datei hiess bis 2026-08-11
# knowledge.db (siehe haken/ort.py); Sicherungen aus dieser Zeit tragen
# weiterhin den alten Namen.
#
# BEFUND 2026-08-19, der diese Zeile noetig machte: Im Verzeichnis lagen 318
# automatische Sicherungen -- 14 als `brainlehr.db.bak-*` (1,4 GB) und 304 als
# `knowledge.db.bak-*` (9,5 GB). `kandidaten()` filterte ausschliesslich auf
# den AKTUELLEN Namen und sah die 304 nie. Das Aufraeumen lief bei jedem
# Serverstart, war fuer das, was es sah, korrekt -- und konnte 96 Prozent
# seines Gegenstands strukturell nicht erreichen. Kein Fehlschlag, keine
# Meldung, und eine Platte, die sich unerklaerlich fuellt.
FRUEHERE_NAMEN = ("knowledge.db",)


def kandidaten(db_pfad: Path) -> list[Path]:
    """Automatische Sicherungen, juengste zuerst -- auch die unter frueheren
    Namen derselben Datenbank.

    Je Name getrennt sortiert und zusammengefuegt: `behalte` gilt pro Name,
    nicht insgesamt. Sonst wuerden bei einer Umbenennung die juengsten des
    alten Namens die des neuen verdraengen oder umgekehrt, je nachdem welcher
    Zeitstempel gerade hoeher liegt."""
    # BEIDE Orte, und diese Reihenfolge ist bindend: der neue Ordner existiert
    # seit 2026-08-19, das alte Verzeichnis traegt alles davor. Wer nur den
    # neuen liest, wiederholt den Befund vom selben Tag -- ein Aufraeumen, das
    # 96 Prozent seines Gegenstands strukturell nicht erreicht -- nur mit dem
    # Verzeichnis statt dem Namen als Ursache.
    orte = [db_pfad.parent, sicherungsordner(db_pfad)]
    alle = []
    gesehen = set()
    for ordner in orte:
        if not ordner.is_dir() or ordner in gesehen:
            continue
        gesehen.add(ordner)
        alle.extend(ordner.iterdir())
    if not alle:
        return []
    namen = (db_pfad.name, *FRUEHERE_NAMEN)
    treffer: list[Path] = []
    for name in namen:
        passend = [p for p in alle if _automatisch(p, name)]
        treffer.extend(sorted(passend, key=lambda p: p.name, reverse=True))
    return treffer


def aufraeumen(db_pfad: Path, behalte: int = BEHALTE) -> tuple[int, int]:
    """Loescht alle bis auf die `behalte` juengsten. Gibt (geloescht, bytes).

    Nie blockierend: eine Datei, die sich nicht loeschen laesst (fremder
    Halter, Rechte), wird uebersprungen statt zu werfen. Diese Funktion darf
    einen Serverstart unter keinen Umstaenden verhindern -- sie raeumt auf,
    sie ist nicht der Zweck.
    """
    # JE NAME schneiden, nicht global. `kandidaten()` liefert seit
    # 2026-08-19 auch die Sicherungen frueherer Datenbanknamen; ein globales
    # [behalte:] wuerde bei 10 zu behaltenden Dateien alle 280 des alten
    # Namens loeschen und nur die des neuen halten -- oder umgekehrt, je
    # nachdem welcher Zeitstempel gerade hoeher liegt. Der Docstring von
    # kandidaten() verspricht "je Name"; hier wird es eingeloest.
    alt: list[Path] = []
    for name in (db_pfad.name, *FRUEHERE_NAMEN):
        gleiche = [p for p in kandidaten(db_pfad) if p.name.startswith(name + MUSTER)]
        alt.extend(gleiche[behalte:])
    n = groesse = 0
    for p in alt:
        try:
            groesse += p.stat().st_size
            p.unlink()
            n += 1
        except OSError:
            continue
    return n, groesse


def aufraeumen_still(db_pfad) -> tuple[int, int]:
    """Wie aufraeumen(), aber verschluckt JEDEN Fehler und gibt (0, 0) zurueck.

    Fuer Aufrufer, deren eigentlicher Zweck ein anderer ist -- der MCP-Server
    ruft das beim Start. Ein Aufraeumfehler darf einen Serverstart unter
    keinen Umstaenden verhindern; er haette dieselbe Wirkung wie das Leck,
    gegen das er gebaut ist, nur schneller.
    """
    try:
        return aufraeumen(Path(db_pfad))
    except Exception:
        return (0, 0)


def tagessicherung(db_pfad: Path | None = None, behalte: int = BEHALTE) -> tuple[Path, int, int]:
    """Zieht EINE WAL-konsistente Kopie und raeumt danach auf.

    WARUM DAS ENTGEGEN DER ERSTEN EINSCHAETZUNG GEBAUT WURDE: E15 verlangt
    "automatisch". Bis heute entstand eine Sicherung nur ereignisgetrieben --
    beim Serverstart und vor Schemaeingriffen. Eine Woche ohne Serverstart war
    eine Woche ohne Sicherung.

    Der naheliegende Einwand war der Platz, und er hielt der Messung nicht
    stand: brainlehr.db ist 0,13 GB, mal BEHALTE=10 sind 1,3 GB auf einem
    Datentraeger mit 18 GB Rest. Das Leck von 2026-08-14 (22 GB in drei Tagen)
    entstand NICHT durch zu haeufige Sicherungen, sondern weil vierzehn
    Stellen anlegten und keine aufraeumte. Deshalb raeumt diese Funktion im
    selben Aufruf auf -- sie kann das Leck bauartbedingt nicht wiederholen.

    Gibt (pfad, geloescht, freigegebene_bytes) zurueck.
    """
    import sqlite3
    if db_pfad is None:
        import ort  # type: ignore
        db_pfad = Path(ort.DB)
    db_pfad = Path(db_pfad)
    if not db_pfad.exists():
        raise FileNotFoundError(f"{db_pfad} existiert nicht -- nichts zu sichern")
    # Der Stempel hat Sekundenaufloesung, und `_automatisch()` verlangt GENAU
    # 15 Zeichen -- ein Zusatz wie "-2" wuerde die Datei zur handbenannten
    # machen und damit vom Aufraeumen ausnehmen, also ein Leck bauen. Deshalb
    # bei Kollision auf die naechste freie Sekunde ausweichen statt anzuhaengen.
    # Im Tagesbetrieb tritt das nie ein; im Selbsttest, der elf Kopien in einer
    # Sekunde zieht, sofort -- und dort war es ein stilles Ueberschreiben.
    from datetime import datetime, timedelta, timezone
    jetzt = datetime.now(timezone.utc)
    for _ in range(3600):
        ziel = sicherungspfad(db_pfad, f"{jetzt:%Y%m%dT%H%M%S}")
        if not ziel.exists():
            break
        jetzt += timedelta(seconds=1)
    else:
        raise RuntimeError("keine freie Sekunde fuer den Sicherungsnamen gefunden")
    quelle = sqlite3.connect(f"file:{db_pfad}?mode=ro", uri=True)
    kopie = sqlite3.connect(str(ziel))
    try:
        quelle.backup(kopie)
    finally:
        kopie.close()
        quelle.close()
    n, b = aufraeumen(db_pfad, behalte=behalte)
    return ziel, n, b


def _selftest() -> None:
    import tempfile
    import ort
    # Der Dateiname kommt aus ort, nicht aus einer getippten Zeichenkette --
    # so prueft der Selbsttest gegen den ECHTEN Namen und bleibt richtig,
    # wenn die Datenbank einmal anders heisst (sie hiess bis 2026-08-11
    # knowledge.db). Beanstandet von tests/test_produktivcode_nutzt_ort.py.
    dbname = Path(ort.DB).name
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        db = d / dbname
        db.write_bytes(b"x")
        for i in range(15):
            (d / f"{dbname}.bak-2026081{i//10}T00000{i%10}").write_bytes(b"y" * 100)
        # Von Hand benannte bleiben, egal wie alt.
        (d / f"{dbname}.bak-20260801T000000-vor-umbau").write_bytes(b"z")
        (d / f"{dbname}.vor_utc_2026-08-14").write_bytes(b"z")
        (d / f"{dbname}-wal").write_bytes(b"z")

        assert len(kandidaten(db)) == 15, len(kandidaten(db))
        n, _ = aufraeumen(db, behalte=10)
        assert n == 5, n
        assert len(kandidaten(db)) == 10

        # NEGATIVFALL, der wichtigere: nichts ausser der Zeitstempelform
        # wurde angefasst. Ein Mensch, der eine Sicherung behalten will,
        # benennt sie um -- diese Zusicherung ist sein Verlass darauf.
        for name in (dbname, f"{dbname}.bak-20260801T000000-vor-umbau",
                     f"{dbname}.vor_utc_2026-08-14", f"{dbname}-wal"):
            assert (d / name).exists(), f"{name} haette nicht angefasst werden duerfen"

        # BEIDE ORTE (2026-08-19). Rot gegen den Stand davor: `kandidaten()`
        # las nur `db.parent` und haette die Sicherung im Unterordner nie
        # gesehen -- also 10 statt 11 gemeldet und sie nie aufgeraeumt.
        neu = sicherungspfad(db, "20260819T235959")
        neu.write_bytes(b"y" * 100)
        assert neu.parent == d / ORDNERNAME, neu
        assert len(kandidaten(db)) == 11, len(kandidaten(db))
        assert neu in kandidaten(db)
        # Und die Umgebungsvariable schlaegt den Vorgabeort.
        import os as _os
        _os.environ[ORT_UMGEBUNG] = str(d / "woanders")
        try:
            assert sicherungspfad(db, "20260819T235958").parent == d / "woanders"
        finally:
            del _os.environ[ORT_UMGEBUNG]
        neu.unlink()

        # TAGESSICHERUNG: echte Kopie, im getrennten Ordner, und sie raeumt
        # im selben Aufruf auf -- das ist der Unterschied zum Leck von
        # 2026-08-14, bei dem vierzehn Stellen anlegten und keine aufraeumte.
        import sqlite3
        echt = d / "echt.db"
        c = sqlite3.connect(str(echt))
        c.execute("create table t(x)")
        c.execute("insert into t values (42)")
        c.commit(); c.close()
        pfad, _, _ = tagessicherung(echt, behalte=10)
        assert pfad.parent == d / ORDNERNAME, pfad
        k = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
        assert k.execute("select x from t").fetchone()[0] == 42, "Kopie ist nicht lesbar"
        k.close()
        # Und sie deckelt sich selbst: elf Laeufe hinterlassen zehn Dateien.
        for _ in range(10):
            tagessicherung(echt, behalte=10)
        assert len(kandidaten(echt)) == 10, len(kandidaten(echt))

        # Grenzwert: genau `behalte` vorhanden -> nichts zu tun.
        n2, _ = aufraeumen(db, behalte=10)
        assert n2 == 0, n2
        # Und behalte=0 raeumt alles Automatische weg, sonst nichts.
        n3, _ = aufraeumen(db, behalte=0)
        assert n3 == 10 and db.exists()
        # aufraeumen_still schluckt auch einen kaputten Pfad.
        assert aufraeumen_still("/gibt/es/nicht/db") == (0, 0)
    print("selftest ok (10 Faelle): juengste bleiben, Handnamen bleiben, "
          "beide Orte gefunden, Umgebungsvariable schlaegt Vorgabeort, "
          "Tagessicherung lesbar und selbstdeckelnd, "
          "Grenzwert, behalte=0 und stiller Fehlerfall geprueft")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    elif "--tagessicherung" in sys.argv:
        pfad, n, b = tagessicherung()
        print(f"gesichert: {pfad} ({pfad.stat().st_size/1e9:.2f} GB); "
              f"{n} alte entfernt, {b/1e9:.2f} GB frei")
    else:
        import ort
        n, b = aufraeumen(Path(ort.DB))
        print(f"{n} automatische Sicherungen entfernt, {b/1e9:.1f} GB frei")
