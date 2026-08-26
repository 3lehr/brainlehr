#!/usr/bin/env python3
"""kettenerklaerung.py -- erklaerte Brueche der Auditkette ueber access_log
(Auftrag 2026-08-06, Anschluss an knowledge_lint.py::find_broken_chain()
und knowledge_mcp_server.py::compute_ketten_hash()).

WARUM ES DAS GIBT: eine befugte Umschreibung von Feldern, die in den
ketten_hash einfliessen (Beispiel: die Zeitzonen-Rueckrechnung 2026-08-06,
Commit 684251b6ecb910f2c7ae55451726a1e6702d0d6a, schrieb 2661 Zeitstempel
um), bricht die Kette an genau der umgeschriebenen Zeile -- erwuenscht, das
ist die Kette, die tut, wofuer sie gebaut ist. Ohne ein Verfahren fuer die
BEFUGTE Umschreibung sieht jede kuenftige Migration wie Manipulation aus.

DER KERN, DER DIESES MODUL VON EINEM "STUMM NEU RECHNEN" UNTERSCHEIDET:
create_explanation() aendert NIE den gespeicherten access_log.ketten_hash --
das waere ein Siegel, das den Bruch wegmacht, und das kann jeder Angreifer
genauso. Der Bruch bleibt sichtbar. Was hinzukommt, ist eine danebenliegende
Zeile in chain_explanations, die ihn erklaert (wer/wann/warum/Commit) und
zwei Hash-Werte mitfuehrt: vorher_hash (was tatsaechlich in access_log
steht) und nachher_hash (was aus den heutigen Feldern berechnet wuerde).
find_broken_chain() (knowledge_lint.py) erkennt einen Bruch als erklaert nur,
wenn BEIDE Werte noch zum aktuellen Zustand passen -- eine Erklaerung mit
falschem vorher_hash wird nicht anerkannt (Abnahme Punkt b).

SELBSTSCHUTZ DES ERKLAERUNGSEINTRAGS -- die Frage aus dem Auftrag, ehrlich
beantwortet: INNERHALB dieser Datenbank kann ein Erklaerungseintrag NICHT
vor nachtraeglicher Erfindung geschuetzt werden. Wer Schreibrechte auf die
DB-Datei hat, kann eine Zeile in chain_explanations frei einfuegen oder
aendern -- exakt dieselbe Grenze, die schon fuer access_log.ketten_hash
gilt (siehe dessen Spaltenkommentar in schema.sql: "wer Schreibrechte hat,
kann die Kette neu rechnen"). Eine zweite Tabelle in derselben Datei loest
das strukturell nicht.
Schutz entsteht nur AUSSERHALB der Datenbank -- und genau dafuer existiert
bereits ankerverfahren.py: create_explanation() baut optional (Parameter
`anker`, Voreinstellung None = kein Anker) einen Beleg ueber
SHA-256(access_log_id|vorher_hash|nachher_hash|grund|commit_hash|erstellt_am)
per ankerverfahren.versuche_anker() -- trocken (kein Netz) per Vorgabe,
gleiche Grenze wie dort. Erst ein tatsaechlich VERSANDTER RFC-3161-Beleg
(senden=True gegen eine externe TSA) oder eine Gegenzeichnung mit einem
Schluessel ausserhalb dieser DB macht eine spaetere Aenderung von grund/
vorher_hash/nachher_hash sichtbar: der neu berechnete Hash passt dann nicht
mehr zum extern verankerten Beleg. Ohne externen Anker (anker_beleg NULL)
ist ein Erklaerungseintrag intern nachvollziehbar (er nennt wer/wann/warum
und wird gegen den tatsaechlichen Zustand geprueft), aber nicht faelschungssicher
-- das wird hier benannt, nicht verschwiegen.

Was hier NICHT versucht wird: die 1226 Altzeilen ohne ketten_hash (Zeitraum
vor migrate_auditkette.py) nachtraeglich zu verketten. Das waere genau die
Faelschung, gegen die die Kette schuetzt (Auftrag Punkt 4) -- sie bleiben
ungedeckt und werden von find_broken_chain() weiterhin getrennt ausgewiesen.
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

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from knowledge_mcp_server import compute_ketten_hash, now_iso  # noqa: E402
import ankerverfahren  # noqa: E402


class KeinBruchError(ValueError):
    """Kein Bruch an dieser access_log_id gefunden -- eine Erklaerung fuer
    eine heile Zeile waere selbst eine Faelschung (Abnahme Punkt b:
    Erklaerungen ohne passenden Vorher-Zustand werden NICHT anerkannt)."""


def _bruch_an(conn: sqlite3.Connection, access_log_id: int) -> tuple[str, str]:
    """(gespeichert, erwartet) fuer genau eine access_log-Zeile -- gleiche
    Formel wie knowledge_lint.find_broken_chain(), hier auf eine einzelne id
    beschraenkt statt die ganze Strecke zu lesen."""
    row = conn.execute(
        "SELECT id, node_path, action, query, project_id, actor, model, session, "
        "status, timestamp, zeilen_hash, ketten_hash FROM access_log WHERE id = ?",
        (access_log_id,),
    ).fetchone()
    if row is None:
        raise KeinBruchError(f"access_log.id={access_log_id} existiert nicht")
    if row["ketten_hash"] is None:
        raise KeinBruchError(
            f"access_log.id={access_log_id} liegt im ungedeckten Zeitraum "
            "(kein ketten_hash) -- kein Bruch, nichts zu erklaeren"
        )
    prev = conn.execute(
        # Same predecessor rule as knowledge_lint.find_broken_chain(): legacy
        # rows without a chain hash are an uncovered interval, not a reset.
        "SELECT ketten_hash FROM access_log WHERE id < ? AND ketten_hash IS NOT NULL "
        "ORDER BY id DESC LIMIT 1",
        (access_log_id,),
    ).fetchone()
    prev_hash = prev["ketten_hash"] if prev else None
    erwartet = compute_ketten_hash(
        prev_hash, node_path=row["node_path"], action=row["action"], query=row["query"],
        project_id=row["project_id"], actor=row["actor"], model=row["model"],
        session=row["session"], status=row["status"], timestamp=row["timestamp"],
        zeilen_hash=row["zeilen_hash"],
    )
    return row["ketten_hash"], erwartet


def create_explanation(
    conn: sqlite3.Connection,
    access_log_id: int,
    grund: str,
    *,
    commit_hash: str | None = None,
    actor: str | None = None,
    now: str | None = None,
    anker: str | None = None,
    **anker_kwargs: object,
) -> dict:
    """Legt eine Erklaerung fuer den Bruch an access_log_id an. Wirft
    KeinBruchError, wenn dort (nach heutigem Stand) gar kein Bruch vorliegt
    -- das ist die Gegenprobe, die eine erfundene Erklaerung fuer eine heile
    Zeile verhindert. `anker`: None (Vorgabe) baut keinen externen Beleg,
    "rfc3161"/"gegenzeichnung" reicht an ankerverfahren.versuche_anker()
    durch (trocken per Vorgabe dort, siehe Modul-Docstring)."""
    if not grund.strip():
        raise ValueError("grund darf nicht leer sein")
    # The explicit writer transaction closes the read-then-insert race: two
    # processes can ask about the same historic break, but only one persists
    # its explanation.  Existing duplicate legacy rows remain visible.
    conn.execute("BEGIN IMMEDIATE")
    try:
        gespeichert, erwartet = _bruch_an(conn, access_log_id)
        if gespeichert == erwartet:
            raise KeinBruchError(
                f"access_log.id={access_log_id} ist heil (gespeichert==erwartet) -- "
                "nichts zu erklaeren"
            )
        existing = conn.execute(
            """SELECT id, grund, commit_hash, vorher_hash, nachher_hash,
                      erstellt_am, erstellt_von, anker_beleg
                 FROM chain_explanations
                 WHERE access_log_id = ? AND vorher_hash = ? AND nachher_hash = ?
                 ORDER BY id LIMIT 1""",
            (access_log_id, gespeichert, erwartet),
        ).fetchone()
        if existing is not None:
            conn.commit()
            return {**dict(existing), "access_log_id": access_log_id, "status": "already_recorded"}

        erstellt_am = now or now_iso()
        anker_beleg = None
        if anker is not None:
            nachricht = f"{access_log_id}|{gespeichert}|{erwartet}|{grund}|{commit_hash}|{erstellt_am}"
            wurzel = hashlib.sha256(nachricht.encode("utf-8")).hexdigest()
            bereich = {"von": access_log_id, "bis": access_log_id}
            beleg = ankerverfahren.versuche_anker(anker, wurzel, bereich, erstellt_am, **anker_kwargs)
            anker_beleg = json.dumps(beleg, ensure_ascii=False)

        cursor = conn.execute(
            """INSERT INTO chain_explanations
               (access_log_id, grund, commit_hash, vorher_hash, nachher_hash,
                erstellt_am, erstellt_von, anker_beleg)
               VALUES (?,?,?,?,?,?,?,?)""",
            (access_log_id, grund, commit_hash, gespeichert, erwartet,
             erstellt_am, actor, anker_beleg),
        )
        conn.commit()
        return {
            "id": int(cursor.lastrowid), "status": "recorded",
            "access_log_id": access_log_id, "grund": grund,
            "commit_hash": commit_hash, "vorher_hash": gespeichert,
            "nachher_hash": erwartet, "erstellt_am": erstellt_am,
            "erstellt_von": actor, "anker_beleg": anker_beleg,
        }
    except BaseException:
        conn.rollback()
        raise


def explanations_by_id(conn: sqlite3.Connection) -> dict[int, list[dict]]:
    """Alle Erklaerungen, gruppiert nach access_log_id -- Rohdaten, keine
    Gueltigkeitspruefung hier (die macht knowledge_lint.find_broken_chain()
    gegen den TATSAECHLICHEN heutigen Bruch, nicht gegen diese Tabelle allein
    -- eine Tabelle kann von sich aus nicht wissen, ob sie noch stimmt)."""
    rows = conn.execute(
        "SELECT id, access_log_id, grund, commit_hash, vorher_hash, nachher_hash, "
        "erstellt_am, erstellt_von, anker_beleg FROM chain_explanations ORDER BY id"
    ).fetchall()
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["access_log_id"], []).append(dict(r))
    return out


def explains(erklaerung: dict, gespeichert: str, erwartet: str) -> bool:
    """Traegt diese Erklaerung den AKTUELLEN Bruch (gespeichert vs.
    erwartet)? Nur dann gilt der Bruch als erklaert -- eine Erklaerung mit
    veraltetem/falschem vorher_hash deckt nichts (Abnahme Punkt b)."""
    return erklaerung["vorher_hash"] == gespeichert and erklaerung["nachher_hash"] == erwartet


# ─── Selbsttest ─────────────────────────────────────────────────────────

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge_test.db"
        schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript(schema)
        conn.commit()

        # Kette aufbauen: zwei saubere Zeilen ueber die echte Formel.
        from knowledge_mcp_server import log_access
        log_access(conn, "/x/0", "read", query="q0")
        log_access(conn, "/x/1", "read", query="q1")
        tampered_id = conn.execute("SELECT id FROM access_log ORDER BY id LIMIT 1").fetchone()[0]

        # Kein Bruch vorhanden -> create_explanation() muss ablehnen.
        try:
            create_explanation(conn, tampered_id, "erfunden")
            raise AssertionError("haette ohne echten Bruch werfen muessen")
        except KeinBruchError:
            pass

        # Befugte Umschreibung simulieren: query aendern, ketten_hash NICHT
        # nachrechnen (exakt wie migrate_auditkette-artige Migrationen es tun
        # duerften, wenn sie ketten_hash unangetastet lassen).
        conn.execute("UPDATE access_log SET query = 'q0-umgeschrieben' WHERE id = ?", (tampered_id,))
        conn.commit()

        eintrag = create_explanation(
            conn, tampered_id, "Testmigration: Feld umgeschrieben, Zeitzonen-Beispiel",
            commit_hash="deadbeef",
        )
        assert eintrag["vorher_hash"] != eintrag["nachher_hash"]

        erklaerungen = explanations_by_id(conn)
        assert tampered_id in erklaerungen
        gespeichert, erwartet = _bruch_an(conn, tampered_id)
        assert explains(erklaerungen[tampered_id][0], gespeichert, erwartet)

        # Gegenprobe: eine Erklaerung mit falschem vorher_hash deckt den
        # Bruch NICHT.
        falsche = dict(erklaerungen[tampered_id][0])
        falsche["vorher_hash"] = "0" * 64
        assert not explains(falsche, gespeichert, erwartet)

        conn.close()
        print("kettenerklaerung --selftest: alle Faelle bestanden")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__.splitlines()[0])
