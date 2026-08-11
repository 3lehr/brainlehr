#!/usr/bin/env python3
"""Auditanker — Merkle-Baum ueber die verkettete Strecke von access_log
(Auftrag 2026-08-06, Anschluss an die Auditkette aus knowledge_mcp_server.py::
log_access()/compute_ketten_hash() und knowledge_lint.py::find_broken_chain()).

Zwei Faehigkeiten:
  1. Merkle-Baum ueber die ketten_hash-Werte der Zeilen AB DEM KETTENANFANG
     (Zeilen mit ketten_hash IS NOT NULL) -- die 1223 Altzeilen ohne Hash
     (ungedeckter Zeitraum) gehoeren nicht in den Baum. Wurzel wird bei
     jedem Aufruf NEU aus dem Bestand berechnet, nie gespeichert -- eine
     zweite Ablage koennte gegenueber der DB auseinanderlaufen.
  2. Anker fuer aussen: `wurzel` gibt die aktuelle Wurzel + Bereich +
     Zeitstempel in einer Commit-Nachricht-tauglichen Form aus; `pruefe`
     rechnet eine frueher ausgegebene Wurzel gegen den heutigen Bestand
     im selben Bereich nach.

Wiederverwendet statt neu gebaut:
  - knowledge_lint.get_ro_conn()   (mode=ro-Verbindung, identisches Muster)
  - knowledge_mcp_server.now_iso() (Zeitstempelformat)
  Die Hashkettenformel selbst (compute_ketten_hash) wird HIER NICHT
  gebraucht -- der Merkle-Baum vertraut den gespeicherten ketten_hash-
  Werten als Blaetter; ob die Kette selbst intakt ist, prueft weiterhin
  ausschliesslich knowledge_lint.find_broken_chain(). Zwei getrennte
  Fragen: "ist die Kette unverfaelscht" (Lint) vs. "kann ich eine
  einzelne Zeile beweisen, ohne den ganzen Bestand zu lesen" (dieser
  Baum).

Ungerade Knotenzahl auf einer Ebene: der letzte Knoten wird dupliziert
(Bitcoin-Merkle-Konvention) -- FESTGELEGT, damit die Wurzel unabhaengig
nachrechenbar bleibt. Bei genau einem Blatt ist die "Wurzel" das Blatt
selbst (keine Hash-Runde noetig, ein einzelner Wert braucht keinen Baum).
Zwei Kinder werden zu SHA-256(links_hex + rechts_hex) verknuepft (Hex-
Strings direkt aneinandergehaengt, dann als UTF-8 gehasht) -- kein
Domain-Separation-Praefix zwischen Blatt- und Knoten-Hashes; das ist eine
bekannte, hier bewusst nicht geschlossene theoretische Luecke (zweite
Blattpaar-Kombination koennte mit einem inneren Knoten kollidieren, wenn
ein Angreifer Blattinhalte waehlen koennte) -- ketten_hash-Werte sind
aber nicht angreiferkontrolliert (SHA-256 ueber Systemfelder), daher hier
nicht sicherheitsrelevant.

GRENZE (ausdruecklich, nicht ueberspielt): der Anker ist eine Commit-
Nachricht, KEINE Signatur. Ein gepushter, unsignierter Commit beweist nur,
dass sich der Bestand seit damals nicht mehr veraendert hat (Anker gegen
versehentliche/nachtraegliche Aenderung) -- er beweist NICHT, WER den
Anker gesetzt hat. `git log --format=%G?` liefert fuer diesen Bestand `N`
(kein GPG-Signing eingerichtet). Das zu schliessen ist eine Entscheidung
des Betreibers ueber seine eigenen Schluessel, keine Codeaenderung hier.
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
import hashlib
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from knowledge_lint import get_ro_conn  # noqa: E402
from knowledge_mcp_server import now_iso  # noqa: E402

DB_PATH = SHARED_KNOWLEDGE / "brainlehr.db"


class LeereStreckeError(ValueError):
    """Keine verketteten Zeilen im angefragten Bereich -- kein Absturz,
    keine erfundene Wurzel, siehe Abnahme-Punkt 1/Punkt 2 im Auftrag."""


def _hash_pair(left: str, right: str) -> str:
    return hashlib.sha256((left + right).encode("utf-8")).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    """Wurzel ueber `leaves`, ohne die Liste zu veraendern. Ein Blatt ->
    das Blatt selbst. Ungerade Ebene -> letzter Knoten wird dupliziert."""
    if not leaves:
        raise LeereStreckeError("keine Blaetter -- leere Strecke, keine Wurzel berechenbar")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_proof(leaves: list[str], index: int) -> list[dict]:
    """Mitgliedschaftsnachweis fuer leaves[index]: Liste von
    {"hash": <Geschwisterhash>, "position": "left"|"right"} von unten
    nach oben. "position" ist die Seite, auf der der Geschwisterknoten
    beim Verknuepfen steht."""
    if not leaves:
        raise LeereStreckeError("keine Blaetter -- leere Strecke, kein Nachweis moeglich")
    if not 0 <= index < len(leaves):
        raise IndexError(f"index {index} ausserhalb 0..{len(leaves) - 1}")
    proof: list[dict] = []
    level = list(leaves)
    idx = index
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        if idx % 2 == 0:
            proof.append({"hash": level[idx + 1], "position": "right"})
        else:
            proof.append({"hash": level[idx - 1], "position": "left"})
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def verify_proof(leaf_hash: str, proof: list[dict], root: str) -> bool:
    """Gegenrichtung zu merkle_proof: aus Blatt + Nachweis die Wurzel
    nachrechnen, ohne die uebrigen Blaetter zu kennen."""
    current = leaf_hash
    for step in proof:
        if step["position"] == "left":
            current = _hash_pair(step["hash"], current)
        else:
            current = _hash_pair(current, step["hash"])
    return current == root


# ─── Bestand lesen ──────────────────────────────────────────────────────

def _chained_rows(conn: sqlite3.Connection, von: int | None, bis: int | None) -> list[sqlite3.Row]:
    """Zeilen ab dem Kettenanfang (ketten_hash IS NOT NULL), aufsteigend
    nach id. Der ungedeckte Zeitraum (Altzeilen ohne Hash) fliesst nie ein."""
    query = "SELECT id, ketten_hash FROM access_log WHERE ketten_hash IS NOT NULL"
    params: list[int] = []
    if von is not None:
        query += " AND id >= ?"
        params.append(von)
    if bis is not None:
        query += " AND id <= ?"
        params.append(bis)
    query += " ORDER BY id"
    return conn.execute(query, params).fetchall()


def wurzel_fuer_bereich(db_path: Path, von: int | None = None, bis: int | None = None) -> dict:
    """Wurzel + Bereich fuer die aktuell verkettete Strecke (optional auf
    [von, bis] eingeschraenkt). Wirft LeereStreckeError, wenn nichts uebrig
    bleibt -- Aufrufer entscheidet, wie das gemeldet wird."""
    conn = get_ro_conn(db_path)
    try:
        rows = _chained_rows(conn, von, bis)
    finally:
        conn.close()
    if not rows:
        raise LeereStreckeError(
            "keine verketteten Zeilen im angefragten Bereich (ungedeckter "
            "Zeitraum ausgenommen)"
        )
    leaves = [r["ketten_hash"] for r in rows]
    return {
        "root": merkle_root(leaves),
        "von": rows[0]["id"],
        "bis": rows[-1]["id"],
        "n": len(rows),
    }


def format_anchor(info: dict, timestamp: str) -> str:
    """Commit-Nachricht-taugliche Form. Kein Signatur-Nachweis -- siehe
    Modul-Docstring."""
    return (
        f"Auditanker: Merkle-Wurzel {info['root']}\n"
        f"Bereich: access_log.id {info['von']}-{info['bis']} "
        f"({info['n']} verkettete Zeilen)\n"
        f"Zeitstempel: {timestamp}\n"
        f"(unsigniert -- Anker gegen versehentliche Aenderung, beweist "
        f"nicht WER ihn setzte)"
    )


# ─── Selbsttest ─────────────────────────────────────────────────────────

def _selftest() -> None:
    # 1 Blatt: Wurzel ist das Blatt selbst.
    assert merkle_root(["a"]) == "a"

    # 2 Blaetter: von Hand nachgerechnet.
    expected_2 = hashlib.sha256("ab".encode()).hexdigest()
    assert merkle_root(["a", "b"]) == expected_2

    # 3 Blaetter: ungerade Regel greift (letztes Blatt dupliziert).
    p1 = hashlib.sha256("ab".encode()).hexdigest()
    p2 = hashlib.sha256("cc".encode()).hexdigest()
    expected_3 = hashlib.sha256((p1 + p2).encode()).hexdigest()
    assert merkle_root(["a", "b", "c"]) == expected_3

    # 4 Blaetter: explizit von Hand nachgerechnet (Auftrag verlangt
    # mindestens einen Fall ohne Ruecksicht auf die eigene Funktion).
    q1 = hashlib.sha256("ab".encode()).hexdigest()
    q2 = hashlib.sha256("cd".encode()).hexdigest()
    expected_4 = hashlib.sha256((q1 + q2).encode()).hexdigest()
    root_4 = merkle_root(["a", "b", "c", "d"])
    assert root_4 == expected_4, f"{root_4} != {expected_4}"

    # Mitgliedschaftsnachweis fuer jedes Blatt eines 4-Blatt-Baums.
    leaves4 = ["a", "b", "c", "d"]
    for i, leaf in enumerate(leaves4):
        proof = merkle_proof(leaves4, i)
        assert verify_proof(leaf, proof, root_4), f"Nachweis fuer Blatt {i} scheiterte"

    # Gegenprobe 1: manipuliertes Blatt mit altem Nachweis ergibt NICHT die Wurzel.
    proof0 = merkle_proof(leaves4, 0)
    assert not verify_proof("MANIPULIERT", proof0, root_4)

    # Gegenprobe 2: gueltiger Nachweis eines ANDEREN Blattes passt nicht.
    proof1 = merkle_proof(leaves4, 1)
    assert not verify_proof(leaves4[0], proof1, root_4)

    # Leere Strecke: saubere Meldung, kein Absturz, keine erfundene Wurzel.
    try:
        merkle_root([])
        raise AssertionError("merkle_root([]) haette werfen muessen")
    except LeereStreckeError:
        pass

    print("auditanker --selftest: alle Faelle bestanden")


# ─── CLI ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    sub = parser.add_subparsers(dest="cmd")

    p_wurzel = sub.add_parser("wurzel", help="aktuelle Merkle-Wurzel als Anker ausgeben")
    p_wurzel.add_argument("--von", type=int, default=None)
    p_wurzel.add_argument("--bis", type=int, default=None)

    p_pruefe = sub.add_parser("pruefe", help="frueher ausgegebene Wurzel gegen heutigen Bestand pruefen")
    p_pruefe.add_argument("wurzel_hex")
    p_pruefe.add_argument("--von", type=int, required=True)
    p_pruefe.add_argument("--bis", type=int, required=True)

    args = parser.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    if args.cmd == "wurzel":
        try:
            info = wurzel_fuer_bereich(args.db, args.von, args.bis)
        except LeereStreckeError as e:
            print(f"kein Anker moeglich: {e}")
            return 1
        print(format_anchor(info, now_iso()))
        return 0

    if args.cmd == "pruefe":
        try:
            info = wurzel_fuer_bereich(args.db, args.von, args.bis)
        except LeereStreckeError as e:
            print(f"kein Vergleich moeglich: {e}")
            return 1
        passt = info["root"] == args.wurzel_hex
        print(f"Bereich {info['von']}-{info['bis']} ({info['n']} Zeilen): "
              f"{'passt' if passt else 'PASST NICHT'}")
        return 0 if passt else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
