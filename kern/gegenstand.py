#!/usr/bin/env python3
"""Ein Gegenstand hat eine bedeutungslose ID; sein Name ist ein Attribut mit
Geltungszeitraum.

ANLASS. Am 2026-08-18 fragte eine Sitzung, was gegen die Umbenennung von
'atelier' in 'lehrAtelier' spreche, und fuehrte als Argument an, das sei "die
zweite Umbenennung in fuenf Tagen" -- aus dem Gedaechtnis, mit falsch
zitierter ADR-Kennung. Gemessen war es die DRITTE Namensform desselben
Gegenstands: BrainlehrApp -> Atelier (2026-08-14, c6c82863) -> LehrAtelier
(2026-08-18, 7db10b10). Beides stand in `git log --diff-filter=R`, zwei
Sekunden entfernt. Der Betreiber darauf: "und wenn wir fuer solche sachen
immer eine feste id anlegen? so wie wir es bei personen namen gemacht haben?"

DAS PROBLEM IST NICHT, DASS IDS FEHLEN -- ES IST, DASS VERWEISE AUF DEN NAMEN
ZEIGEN. Die Wissensknoten haben beides: `id TEXT PRIMARY KEY` (stabil) und
`path TEXT UNIQUE` (der Name). Verwiesen wird durchgehend auf den Namen:
kanten.source_path/target_path, lessons_learned.node_path, access_log.node_path,
planentscheidung.node_path -- alle mit FOREIGN KEY auf knowledge_nodes(path).
ON UPDATE CASCADE faengt das INNERHALB der Datenbank. Jede Kennung, die einmal
nach aussen gegangen ist -- in eine ADR, einen Commit, einen Startprompt, eine
Nachricht an eine andere Sitzung -- zeigt nach einer Umbenennung ins Leere.
Dieselbe Verwechslung hat am selben Tag eine ganze Abrufmessung entwertet: das
Messskript verglich `id` gegen `path`, 20 von 45 Faellen konnten nie treffen,
und das Ergebnis sah nicht kaputt aus, sondern plausibel schlecht (L-0e0ab6).

DIE REGEL: Ein Name ist nie ein Schluessel. Was ein Ding IST, haengt an einer
bedeutungslosen ID; wie es HEISST, ist eine Zeile mit von--bis. Bedeutungslos
ist Bedingung, nicht Geschmack -- eine sprechende ID ('atelier-001') ist wieder
ein Name und wird beim naechsten Mal genauso falsch.

WAS DAS KANN, das git nicht kann: `aufloesen()` beantwortet auch den ALTEN
Namen. Wer 'Atelier' sucht, findet den Gegenstand, der heute anders heisst,
samt Zeitraum -- ohne zu wissen, dass er umbenannt wurde. Genau das ist die
Frage, die niemand stellt, weil niemand weiss, dass er sie stellen muesste.

Zeit wird IMMER hereingereicht (`ts`), nie im Kern geholt -- sonst ist eine
Namenskette nicht nachstellbar (Walkthrough-Doktrin).

Aufruf:
    python3 gegenstand.py --selftest
    python3 gegenstand.py --aus-git <repo>   # Umbenennungen aus git vorschlagen
"""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gegenstaende (
    id         TEXT PRIMARY KEY,   -- bedeutungslos, absichtlich: siehe Modulkopf
    art        TEXT NOT NULL,      -- anwendung | verzeichnis | dienst | buendel | zweig | domaene | ...
    angelegt   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gegenstand_namen (
    gegenstand_id TEXT NOT NULL,
    name          TEXT NOT NULL,
    art_des_namens TEXT NOT NULL DEFAULT 'ruf',  -- ruf | pfad | buendelkennung | anzeige
    gilt_ab       TEXT NOT NULL,
    gilt_bis      TEXT,                          -- NULL = gilt heute
    beleg         TEXT NOT NULL,                 -- Commit, ADR, Betreibersatz
    PRIMARY KEY (gegenstand_id, name, art_des_namens, gilt_ab),
    FOREIGN KEY (gegenstand_id) REFERENCES gegenstaende(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gegenstand_namen_name
    ON gegenstand_namen(name);

-- Die Bindung eines Eintrags an einen Gegenstand.
--
-- WARUM NICHT knowledge_relations (nachgesehen, schema.sql:1073-1095, bevor
-- hier eine Zeile entstand): beide Fremdschluessel dieser Tabelle zeigen auf
-- knowledge_nodes(path). Ein Gegenstand ist kein Knoten und bekommt auch
-- keinen -- ein Gegenstand mit Pfad haette wieder einen Namen als Schluessel,
-- also genau das, was ADR-028 abschafft. Drei Spalten plus Beleg sind
-- billiger als ein Knoten je Person.
--
-- node_path traegt ON UPDATE CASCADE wie die uebrigen *_path-Verweise: der
-- Pfad ist der Name des Knotens, und Namen wandern.
CREATE TABLE IF NOT EXISTS gegenstand_bezug (
    node_path     TEXT NOT NULL,
    gegenstand_id TEXT NOT NULL,
    rolle         TEXT NOT NULL DEFAULT 'betrifft',  -- betrifft | verfasst_von | gerichtet_an | ...
    beleg         TEXT NOT NULL,
    seit          TEXT NOT NULL,
    PRIMARY KEY (node_path, gegenstand_id, rolle),
    FOREIGN KEY (gegenstand_id) REFERENCES gegenstaende(id) ON DELETE CASCADE,
    FOREIGN KEY (node_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gegenstand_bezug_gegenstand
    ON gegenstand_bezug(gegenstand_id);
"""


class UnbekannterName(LookupError):
    """Der Name ist nie vergeben worden. Kein Ausweichen auf Aehnliches."""


class MehrdeutigerName(LookupError):
    """Mehrere Gegenstaende tragen diesen Namen -- ein Name ist kein Schluessel.

    Dieser Fehler ist der Zweck des Moduls, nicht sein Versagen: drei Sprints
    heissen S12, und die richtige Antwort darauf ist eine Auskunft ueber drei
    Kandidaten, keine Auswahl."""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(TABLE_SQL)


def _neue_id(art: str, name: str, beleg: str, ts: str) -> str:
    """Bedeutungslos nach aussen, aber deterministisch aus dem Anlass gebildet --
    damit derselbe Selbsttest zweimal dasselbe liefert. Wer die ID liest, kann
    aus ihr nichts ableiten, und das ist der Zweck.

    Der BELEG gehoert in den Anlass, seit die Plankennungen erfasst werden:
    zwei Plaene desselben Tages duerfen dieselbe Kennung vergeben, und ohne
    den Beleg faellt der zweite Gegenstand still mit dem ersten zusammen --
    ein INSERT OR IGNORE, das aussieht wie ein gelungener Lauf."""
    return hashlib.sha1(f"{art}|{name}|{beleg}|{ts}".encode()).hexdigest()[:8]


def anlegen(conn: sqlite3.Connection, art: str, name: str, *, beleg: str, ts: str,
            art_des_namens: str = "ruf") -> str:
    if not art or not name or not beleg or not ts:
        raise ValueError("art, name, beleg und ts sind Pflicht -- ein Name ohne Beleg ist eine Behauptung")
    gid = _neue_id(art, name, beleg, ts)
    conn.execute("INSERT OR IGNORE INTO gegenstaende (id, art, angelegt) VALUES (?,?,?)", (gid, art, ts))
    conn.execute(
        "INSERT OR IGNORE INTO gegenstand_namen (gegenstand_id, name, art_des_namens, gilt_ab, gilt_bis, beleg)"
        " VALUES (?,?,?,?,NULL,?)", (gid, name, art_des_namens, ts, beleg))
    return gid


def umbenennen(conn: sqlite3.Connection, gid: str, neuer_name: str, *, beleg: str, ts: str,
               art_des_namens: str = "ruf") -> None:
    """Schliesst den laufenden Namen und oeffnet den neuen. Der alte bleibt
    stehen -- eine Umbenennung loescht keine Vergangenheit, sie beendet eine
    Geltung."""
    if not conn.execute("SELECT 1 FROM gegenstaende WHERE id=?", (gid,)).fetchone():
        raise ValueError(f"unbekannter Gegenstand {gid!r}")
    if not beleg or not ts:
        raise ValueError("beleg und ts sind Pflicht")
    conn.execute(
        "UPDATE gegenstand_namen SET gilt_bis=? WHERE gegenstand_id=? AND art_des_namens=? AND gilt_bis IS NULL",
        (ts, gid, art_des_namens))
    conn.execute(
        "INSERT OR IGNORE INTO gegenstand_namen (gegenstand_id, name, art_des_namens, gilt_ab, gilt_bis, beleg)"
        " VALUES (?,?,?,?,NULL,?)", (gid, neuer_name, art_des_namens, ts, beleg))


def benennen(conn: sqlite3.Connection, gid: str, name: str, *, art_des_namens: str,
             beleg: str, ts: str) -> None:
    """Eine WEITERE Namensart an einen bestehenden Gegenstand haengen (Buendel-
    kennung, Pfad, Anzeigename). Nicht mit anlegen() verwechseln -- das erzeugt
    einen neuen Gegenstand, und genau dieser Fehler ist beim Bau hier passiert:
    die Buendelkennung bekam eine eigene ID und stand danach als zweites Ding
    im Register."""
    if not conn.execute("SELECT 1 FROM gegenstaende WHERE id=?", (gid,)).fetchone():
        raise ValueError(f"unbekannter Gegenstand {gid!r}")
    if not name or not beleg or not ts:
        raise ValueError("name, beleg und ts sind Pflicht")
    conn.execute(
        "INSERT OR IGNORE INTO gegenstand_namen (gegenstand_id, name, art_des_namens, gilt_ab, gilt_bis, beleg)"
        " VALUES (?,?,?,?,NULL,?)", (gid, name, art_des_namens, ts, beleg))


def namen(conn: sqlite3.Connection, gid: str) -> list[dict]:
    return [dict(zip(("name", "art_des_namens", "gilt_ab", "gilt_bis", "beleg"), r))
            for r in conn.execute(
                "SELECT name, art_des_namens, gilt_ab, gilt_bis, beleg FROM gegenstand_namen"
                " WHERE gegenstand_id=? ORDER BY gilt_ab, art_des_namens", (gid,))]


def _gilt_bei(gilt_ab: str, gilt_bis: str | None, ts: str) -> bool:
    """gilt_ab eingeschlossen, gilt_bis ausgeschlossen.

    Sonst gehoert der Wechseltag beiden Namen, und genau am Wechseltag stellt
    jemand die Frage. Verglichen wird als Zeichenkette -- ISO-8601 mit gleicher
    Zone sortiert richtig.
    ponytail: Zeichenkettenvergleich, echte Zeitrechnung erst wenn ein Bestand
    mit gemischten Zonen entsteht."""
    return gilt_ab <= ts and (gilt_bis is None or ts < gilt_bis)


def aufloesen(conn: sqlite3.Connection, name: str, ts: str | None = None) -> list[dict]:
    """Der Kern des Moduls: findet den Gegenstand auch ueber einen Namen, den er
    NICHT MEHR traegt. Antwortet mit dem heutigen Namen und dem Zeitraum, in dem
    der gesuchte galt -- die Auskunft, die sonst nur ein Mensch mit gutem
    Gedaechtnis geben kann.

    MIT `ts` wird auf die Gegenstaende eingeschraenkt, die den Namen ZU DIESEM
    ZEITPUNKT trugen. Das ist keine Bequemlichkeit: `S1` meinte am 2026-08-09
    'Reifegrad messen' und am 2026-08-20 'Aufgriffsquote messen'. Ohne
    Zeitpunkt sind das zwei Kandidaten und bleiben es -- diese Funktion waehlt
    NIE einen aus."""
    treffer = []
    for gid, art, sorte, gilt_ab, gilt_bis in conn.execute(
            "SELECT n.gegenstand_id, g.art, n.art_des_namens, n.gilt_ab, n.gilt_bis"
            " FROM gegenstand_namen n JOIN gegenstaende g ON g.id = n.gegenstand_id"
            " WHERE n.name = ?", (name,)):
        if ts is not None and not _gilt_bei(gilt_ab, gilt_bis, ts):
            continue
        # Die Namensart MUSS mitlaufen: ein Gegenstand traegt gleichzeitig einen
        # Rufnamen, eine Buendelkennung und einen Pfad, jeden mit eigener
        # Geltung. Ohne diese Bedingung liefert "heisst heute" irgendeinen der
        # offenen Namen -- beim Bau hier prompt die Buendelkennung als Antwort
        # auf die Frage nach dem Rufnamen.
        heute = conn.execute(
            "SELECT name FROM gegenstand_namen WHERE gegenstand_id=? AND art_des_namens=?"
            " AND gilt_bis IS NULL ORDER BY gilt_ab DESC LIMIT 1", (gid, sorte)).fetchone()
        ruf = conn.execute(
            "SELECT name FROM gegenstand_namen WHERE gegenstand_id=? AND art_des_namens='ruf'"
            " AND gilt_bis IS NULL ORDER BY gilt_ab DESC LIMIT 1", (gid,)).fetchone()
        treffer.append({
            "id": gid, "art": art, "art_des_namens": sorte,
            "heisst_heute": heute[0] if heute else None,
            "ruf_heute": ruf[0] if ruf else None,
            "gesuchter_name_galt": gilt_ab,
            "bis": gilt_bis,
            "noch_gueltig": gilt_bis is None,
        })
    return treffer


def aufloesen_eindeutig(conn: sqlite3.Connection, name: str, ts: str | None = None) -> dict:
    """Fuer Aufrufer, die GENAU EINEN Gegenstand brauchen -- und bei
    Mehrdeutigkeit ausdruecklich scheitern statt den ersten zu nehmen.

    Diese Funktion existiert, damit `aufloesen(...)[0]` nirgends im Haus
    steht. Der stille Griff auf den ersten Treffer ist die Fehlerklasse, gegen
    die ADR-028 geschrieben wurde: er sieht nie kaputt aus, sondern plausibel."""
    kandidaten = aufloesen(conn, name, ts=ts)
    if not kandidaten:
        raise UnbekannterName(f"{name!r} ist nie vergeben worden"
                              + (f" (Stand {ts})" if ts else ""))
    if len(kandidaten) > 1:
        raise MehrdeutigerName(
            f"{name!r} bezeichnet {len(kandidaten)} Gegenstaende"
            + (f" zum Zeitpunkt {ts}" if ts else " -- ein Zeitpunkt wuerde helfen")
            + ": " + ", ".join(f"{k['id']} ({k['art']}, seit {k['gesuchter_name_galt']})"
                               for k in kandidaten))
    return kandidaten[0]


def bezug_setzen(conn: sqlite3.Connection, node_path: str, gid: str, *,
                 beleg: str, ts: str, rolle: str = "betrifft") -> None:
    """Einen Wissensknoten auf einen Gegenstand beziehen -- ueber die KENNUNG.

    Eine Umbenennung des Gegenstands laesst diesen Bezug unberuehrt, weil er
    nicht am Namen haengt. Das ist der ganze Unterschied zu einem Namen im
    Fliesstext."""
    if not conn.execute("SELECT 1 FROM gegenstaende WHERE id=?", (gid,)).fetchone():
        raise ValueError(f"unbekannter Gegenstand {gid!r} -- ein Bezug auf nichts ist keiner")
    if not node_path or not beleg or not ts:
        raise ValueError("node_path, beleg und ts sind Pflicht")
    conn.execute("INSERT OR IGNORE INTO gegenstand_bezug"
                 " (node_path, gegenstand_id, rolle, beleg, seit) VALUES (?,?,?,?,?)",
                 (node_path, gid, rolle, beleg, ts))


def aktueller_name(conn: sqlite3.Connection, gid: str, art_des_namens: str = "ruf") -> str | None:
    """Der heute gueltige Name einer Namensart -- dieselbe Abfrage, die in
    aufloesen()/bezuege_des_knotens() schon zweimal inline steht, hier fuer
    Aufrufer, die nur die ID haben (z.B. eine Rueckrichtung wie
    forderung_vorgang.zustaendiger_von())."""
    r = conn.execute(
        "SELECT name FROM gegenstand_namen WHERE gegenstand_id=? AND art_des_namens=?"
        " AND gilt_bis IS NULL ORDER BY gilt_ab DESC LIMIT 1", (gid, art_des_namens)).fetchone()
    return r[0] if r else None


def bezuege_des_knotens(conn: sqlite3.Connection, node_path: str) -> list[dict]:
    """Welche Gegenstaende betrifft dieser Eintrag? Leere Liste heisst
    'keiner gebunden' und wird als solche ausgewiesen, nicht geraten."""
    return [dict(zip(("gegenstand_id", "rolle", "beleg", "seit", "art", "ruf_heute"), r))
            for r in conn.execute(
                "SELECT b.gegenstand_id, b.rolle, b.beleg, b.seit, g.art,"
                " (SELECT name FROM gegenstand_namen WHERE gegenstand_id=g.id"
                "  AND art_des_namens='ruf' AND gilt_bis IS NULL ORDER BY gilt_ab DESC LIMIT 1)"
                " FROM gegenstand_bezug b JOIN gegenstaende g ON g.id=b.gegenstand_id"
                " WHERE b.node_path=? ORDER BY b.rolle, b.seit", (node_path,))]


def knoten_des_gegenstands(conn: sqlite3.Connection, gid: str) -> list[dict]:
    """Die Gegenrichtung: was ist ueber diesen Gegenstand abgelegt?"""
    return [dict(zip(("node_path", "rolle", "beleg", "seit"), r))
            for r in conn.execute(
                "SELECT node_path, rolle, beleg, seit FROM gegenstand_bezug"
                " WHERE gegenstand_id=? ORDER BY seit, node_path", (gid,))]


def aus_git(repo: str, seit: str = "2026-08-01") -> list[tuple[str, str, str]]:
    """Umbenennungen aus der Versionsverwaltung -- (commit, alt, neu).

    git kennt die vollstaendige Kette und pflegt sie ohne Zutun; sie ist nur
    nie jemand gefragt worden. Das ist der Erstbestand dieses Registers, keine
    laufende Quelle: was hier landet, wird EINMAL uebernommen und danach beim
    Umbenennen mitgeschrieben."""
    aus = subprocess.run(
        ["git", "-C", repo, "log", f"--since={seit}", "--diff-filter=R",
         "--name-status", "--format=%H"],
        capture_output=True, text=True, timeout=60).stdout
    commit, funde = "", []
    for zeile in aus.splitlines():
        if zeile and " " not in zeile and "\t" not in zeile:
            commit = zeile[:8]
        elif zeile.startswith("R"):
            teile = zeile.split("\t")
            if len(teile) >= 3:
                funde.append((commit, teile[1], teile[2]))
    return funde


def _selftest() -> int:
    conn = sqlite3.connect(":memory:")
    ensure_schema(conn)

    # Die echte Kette dieses Repos, mit ihren echten Belegen.
    gid = anlegen(conn, "anwendung", "BrainlehrApp",
                  beleg="Erstanlage", ts="2026-08-01T00:00:00+0200")
    umbenennen(conn, gid, "Atelier", beleg="ADR-008, Commit c6c82863", ts="2026-08-14T00:00:00+0200")
    umbenennen(conn, gid, "LehrAtelier", beleg="ADR-027, Commit 7db10b10", ts="2026-08-18T22:00:00+0200")

    # Das Kernversprechen: der ALTE Name fuehrt zum Gegenstand.
    t = aufloesen(conn, "Atelier")
    assert len(t) == 1, t
    assert t[0]["heisst_heute"] == "LehrAtelier", t
    assert t[0]["noch_gueltig"] is False, t
    assert t[0]["bis"] == "2026-08-18T22:00:00+0200", t

    # Auch der aelteste Name, den heute niemand mehr im Kopf hat.
    assert aufloesen(conn, "BrainlehrApp")[0]["heisst_heute"] == "LehrAtelier"

    # Der heutige Name ist gueltig, nicht beendet.
    assert aufloesen(conn, "LehrAtelier")[0]["noch_gueltig"] is True

    # Die Kette ist vollstaendig und traegt ihre Belege -- drei Namen, kein Verlust.
    kette = namen(conn, gid)
    assert [k["name"] for k in kette] == ["BrainlehrApp", "Atelier", "LehrAtelier"], kette
    assert all(k["beleg"] for k in kette), kette

    # Negativfall: ein nie vergebener Name erfindet nichts.
    assert aufloesen(conn, "Werkbank") == []

    # Zweite Namensart am selben Gegenstand stoert die erste nicht -- die
    # Buendelkennung hat ihre eigene Geltung (sie wechselte am selben Tag mit).
    benennen(conn, gid, "de.brainlehr.atelier", art_des_namens="buendelkennung",
             beleg="Info.plist", ts="2026-08-14T00:00:00+0200")
    umbenennen(conn, gid, "de.brainlehr.lehratelier", beleg="ADR-027",
               ts="2026-08-18T22:00:00+0200", art_des_namens="buendelkennung")
    assert [k["name"] for k in namen(conn, gid) if k["art_des_namens"] == "ruf"] == \
        ["BrainlehrApp", "Atelier", "LehrAtelier"], "Buendelkennung hat die Rufnamen veraendert"
    # Die alte Buendelkennung fuehrt zum selben Gegenstand -- und beantwortet
    # BEIDE Fragen getrennt: wie die Kennung heute lautet und wie das Ding heisst.
    b = aufloesen(conn, "de.brainlehr.atelier")
    assert len(b) == 1, b
    assert b[0]["id"] == gid, "Buendelkennung haengt an einem zweiten Gegenstand"
    assert b[0]["heisst_heute"] == "de.brainlehr.lehratelier", b
    assert b[0]["ruf_heute"] == "LehrAtelier", b
    # Und die Gegenprobe: der Rufname liefert weiter den Rufnamen, nicht die Kennung.
    assert aufloesen(conn, "Atelier")[0]["heisst_heute"] == "LehrAtelier"

    # Beleg ist Pflicht -- ein Name ohne Beleg ist eine Behauptung.
    for schlecht in ({"art": "", "name": "x"}, {"art": "app", "name": ""}):
        try:
            anlegen(conn, schlecht["art"], schlecht["name"], beleg="b", ts="2026-08-18T00:00:00+0200")
        except ValueError:
            pass
        else:
            raise AssertionError(f"haette abgewiesen werden muessen: {schlecht}")

    print("gegenstand: Selbsttest gruen (3-Namen-Kette, alter Name aufloesbar, "
          "Negativfall leer, Beleg erzwungen)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if "--aus-git" in sys.argv:
        repo = sys.argv[sys.argv.index("--aus-git") + 1]
        for commit, alt, neu in aus_git(repo):
            print(f"{commit}  {alt}  ->  {neu}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
