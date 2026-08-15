#!/usr/bin/env python3
"""Melder: die Kantenberechnung steht still.

Anlass (Auftrag 81, 2026-08-13): `kern/kanten_aus_bedeutung.py` zieht
Kanten aus vorhandenen Embeddings -- aber niemand ruft es auf. Gemessen am
selben Tag: juengste `aehnlich_bedeutung`-Kante 2026-08-09T12:54:59, seither
0 von 105 neuen Knoten (12./13.08.) mit Kante, 307 von 2166 Knoten ganz ohne
jede Kante. Die Einbettungen selbst sind taggenau aktuell -- nur die Kanten
bleiben liegen, und das faellt nicht auf, weil eine veraltete Kantenmenge
genauso aussieht wie eine aktuelle.

Was dieser Melder prueft: die JUENGSTE `aehnlich_bedeutung`-Kante gegen den
JUENGSTEN sichtbaren Knoten -- als billiger VORFILTER. Ist die Kante aelter,
folgt eine zweite, echte Probe (Befund 2026-08-15, am gewachsenen Bestand
gemessen): der Zeitvergleich allein meldet naemlich AUCH dann, wenn der
Nachlauf (`haken/auszug_nachziehen.py` -> `automatischer_lauf()`) laengst
korrekt lief und schlicht nichts zu tun hatte, weil der neueste Knoten
keinen Nachbarn ueber der Schwelle 0.65 hat -- ein normaler, gewollter Fall
laut Modulkopf von `kern/kanten_aus_bedeutung.py`, keiner, den der Nachlauf
je heilen koennte. Am 2026-08-15 dreimal in Folge beobachtet: Nachlauf
manuell ausgefuehrt, 0 neue Kanten (korrekt, keine Kandidaten ueber der
Schwelle), Melder blieb trotzdem rot.

Die echte Probe ruft darum `kern/kanten_aus_bedeutung.knoten_ohne_kanten` und
`.finde_kandidaten` (Trockenlauf, kein Schreiben) NUR ueber die bereits
unverbundenen Knoten auf -- dieselbe Eingrenzung wie `automatischer_lauf()`.
Liefert das mindestens einen Kandidaten, haette der Nachlauf ihn anlegen
muessen und hat es nicht -- das ist Stillstand. Liefert es keinen, ist die
Kante zurecht aelter als der juengste Knoten, und der Melder schweigt.

Was er NICHT prueft: ob JEDER Knoten eine Kante hat (das waere ein anderer,
staerkerer Massstab und traefe fast immer zu -- Einzelknoten unter der
Schwelle 0.65 sind ein normaler, gewollter Fall, kein Stillstand). Die
Unverbunden-Zahl wird trotzdem mitgemeldet, weil sie das Ausmass zeigt, nicht
weil sie selbst der Ausloeser ist.

Aufruf:
    python3 melder/kantenstillstand.py            # meldet oder schweigt
    python3 melder/kantenstillstand.py --selftest
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
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(_w))
import speicher  # noqa: E402 -- Tuer statt einer eigenen DB-Verbindung (Grenze Auftrag 81)
import kanten_aus_bedeutung as kab  # noqa: E402 -- fuer die echte Probe, siehe Modulkopf

RELATION_TYPE = "aehnlich_bedeutung"


def _parse(ts: str | None) -> datetime | None:
    """ISO-Zeitstempel robust einlesen -- Knoten tragen lokale Offsets
    (+02:00), von diesem Modul erzeugte Kanten UTC (+00:00, mit
    Mikrosekunden). Ein Stringvergleich ueber zwei Offsets ist nur beim
    Datum selbst verlaesslich, nicht auf die Sekunde -- darum geparst und als
    aware datetime verglichen statt als Text."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def juengster_knoten(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT MAX(created_at) FROM knowledge_nodes WHERE zurueckgezogen = 0"
    ).fetchone()
    return row[0] if row else None


def juengste_kante(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT MAX(created_at) FROM knowledge_relations WHERE relation_type = ?",
        (RELATION_TYPE,),
    ).fetchone()
    return row[0] if row else None


def gesamt_knoten(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE zurueckgezogen = 0"
    ).fetchone()[0]


def unverbundene_knoten(conn: sqlite3.Connection) -> int:
    """Sichtbare Knoten ohne JEDE Kante -- gleich welcher relation_type,
    gleich ob Quelle oder Ziel."""
    return conn.execute(
        """
        SELECT COUNT(*) FROM knowledge_nodes n
        WHERE n.zurueckgezogen = 0
          AND n.path NOT IN (SELECT source_path FROM knowledge_relations)
          AND n.path NOT IN (SELECT target_path FROM knowledge_relations)
        """
    ).fetchone()[0]


def fehlende_kandidaten(conn: sqlite3.Connection) -> int:
    """Echte Probe (siehe Modulkopf): Trockenlauf von `finde_kandidaten` nur
    ueber die schon unverbundenen Knoten -- dieselbe Eingrenzung wie
    `automatischer_lauf()`. Ein unverbundener Knoten hat per Definition KEINE
    Kante, also ist jeder gefundene Kandidat zwangslaeufig noch nicht in der
    DB; ein `edge_exists`-Check danach waere ueberfluessige Arbeit."""
    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    unverbunden = kab.knoten_ohne_kanten(conn, paths)
    if not unverbunden:
        return 0
    nur_index = {i for i, p in enumerate(paths) if p in unverbunden}
    return len(kab.finde_kandidaten(paths, titles, vektoren, nur_index=nur_index))


def pruefen(conn: sqlite3.Connection) -> str | None:
    """None = kein Befund (Kante mindestens so neu wie der juengste Knoten,
    kein Bestand, oder -- nach der echten Probe -- schlicht kein Kandidat
    ueber der Schwelle uebrig). Sonst der Meldetext mit Zahlen."""
    kn_roh = juengster_knoten(conn)
    if kn_roh is None:
        return None
    kn = _parse(kn_roh)
    ka_roh = juengste_kante(conn)
    ka = _parse(ka_roh)

    if kn is not None and ka is not None and ka >= kn:
        return None

    fehlend = fehlende_kandidaten(conn)
    if fehlend == 0:
        return None

    return (
        "Kantenberechnung steht still: juengste "
        f"{RELATION_TYPE}-Kante {ka_roh or 'nie'}, juengster Knoten {kn_roh}. "
        f"{unverbundene_knoten(conn)} von {gesamt_knoten(conn)} Knoten ohne jede Kante, "
        f"davon {fehlend} mit einem fehlenden Kandidaten ueber der Schwelle."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        _selftest()
        return

    with speicher.lesen(args.db) as conn:
        befund = pruefen(conn)
    if befund:
        print(befund)


# ─── Selftest ─────────────────────────────────────────────────────────────
# ":memory:" statt einer echten Datei: der Naht-Wächter (tests/test_naht_ratsche.py)
# zaehlt Produktivdateien mit eigener sqlite3.connect-Verbindung und laesst
# ":memory:" bewusst aus -- eine Testkulisse ist keine Tuer zum Bestand. Ein
# echter Dateipfad wuerde hier nur denselben Zweck (Schema + Testzeilen fuer
# einen einzelnen pruefen()-Aufruf) mit einer zusaetzlichen, hier ueberfluessigen
# Verbindungsart erkaufen.

def _fixture_db() -> sqlite3.Connection:
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # kab.lade_knoten_vektoren liest per Spaltenname
    conn.executescript(schema)
    return conn


def _insert_node(conn: sqlite3.Connection, path: str, created_at: str) -> None:
    conn.execute(
        """
        INSERT INTO knowledge_nodes
        (id, path, parent_path, project_id, title, summary, source, anlass,
         norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund,
         created_at, updated_at)
        VALUES (?, ?, NULL, 'shared', ?, 'Testknoten', 'test', 'skript',
                'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung', ?, ?)
        """,
        (str(uuid.uuid4()), path, path, created_at, created_at, created_at),
    )


def _insert_edge(conn: sqlite3.Connection, a: str, b: str, created_at: str,
                  relation_type: str = RELATION_TYPE) -> None:
    conn.execute(
        """
        INSERT INTO knowledge_relations
        (id, source_path, target_path, relation_type, confidence, weight,
         evidence, source, creator, model, session, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0.9, 1.0, 'Testvorrichtung', 'test', 'test', NULL, NULL, ?, ?)
        """,
        (str(uuid.uuid4()), a, b, relation_type, created_at, created_at),
    )


def _insert_embedding(conn: sqlite3.Connection, path: str, vector: list[float]) -> None:
    """Fuer die echte Probe (`fehlende_kandidaten`) braucht ein Knoten ein
    Embedding -- ohne eins liefert `lade_knoten_vektoren` ihn gar nicht erst,
    und er kann nie als Kandidat auftauchen. `ref_id` = der Knoten selbst
    (per path aufgeloest), gleiche Form wie tests/test_kanten_aus_bedeutung.py."""
    from embeddings import pack_embedding  # noqa: E402 -- nur hier im Selftest gebraucht

    node_id = conn.execute(
        "SELECT id FROM knowledge_nodes WHERE path = ?", (path,)
    ).fetchone()[0]
    now = "2026-08-15T00:00:00+00:00"
    conn.execute(
        """
        INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at)
        VALUES ('node', ?, 'shared', ?, ?, ?, ?)
        """,
        (node_id, kab.EMBED_MODEL, len(vector), pack_embedding(vector), now),
    )


def _selftest() -> None:
    alt = "2026-08-09T12:54:59.995480+00:00"
    neu = "2026-08-13T08:27:35+02:00"  # lokaler Offset wie echte Knoten

    # A) Abnahme 1 -- heutiger Bestand: juengste Kante aelter als juengster
    #    Knoten, UND der unverbundene Knoten hat einen echten Kandidaten
    #    ueber der Schwelle (/c identisch zu /a) -> Melder schlaegt an.
    conn = _fixture_db()
    _insert_node(conn, "/a", alt)
    _insert_node(conn, "/b", neu)  # neuer als jede Kante
    _insert_node(conn, "/c", alt)  # ohne jede Kante
    _insert_edge(conn, "/a", "/b", alt)
    _insert_embedding(conn, "/a", [1.0, 0.0, 0.0])
    _insert_embedding(conn, "/b", [0.0, 1.0, 0.0])
    _insert_embedding(conn, "/c", [1.0, 0.0, 0.0])  # identisch zu /a, sim=1.0
    conn.commit()

    befund = pruefen(conn)
    assert befund is not None, "muss anschlagen: echter Kandidat (/c<->/a) fehlt"
    assert alt in befund and neu in befund, befund
    assert "1 von 3 Knoten ohne jede Kante" in befund, befund
    assert "1 mit einem fehlenden Kandidaten" in befund, befund
    conn.close()

    # A2) Gegenprobe zu A, der eigentliche Fund vom 2026-08-15: gleiche
    #     Zeitlage (Kante aelter als juengster Knoten), aber der unverbundene
    #     Knoten hat KEINEN Nachbarn ueber der Schwelle -- der Nachlauf lief
    #     korrekt und hatte nichts zu tun. Ein reiner Zeitvergleich haette
    #     hier faelschlich gemeldet (Befund am echten Bestand, 200 Knoten
    #     betroffen, 2026-08-15).
    conn = _fixture_db()
    _insert_node(conn, "/a", alt)
    _insert_node(conn, "/b", alt)
    _insert_node(conn, "/c", neu)  # neuer als jede Kante, aber ohne Nachbarn
    _insert_edge(conn, "/a", "/b", alt)
    _insert_embedding(conn, "/a", [1.0, 0.0, 0.0])
    _insert_embedding(conn, "/b", [0.0, 1.0, 0.0])
    _insert_embedding(conn, "/c", [0.0, 0.0, 1.0])  # orthogonal zu beiden, sim=0.0
    conn.commit()

    assert pruefen(conn) is None, (
        "darf NICHT anschlagen: /c ist unverbunden, aber ohne Kandidaten ueber "
        "der Schwelle -- kein Stillstand, nur eine korrekt leere Runde"
    )
    conn.close()

    # B) Abnahme 2, Negativfall -- vollstaendig verbundener/aktueller Bestand:
    #    Kante MINDESTENS so neu wie der juengste Knoten -> kein Befund, auch
    #    wenn (wie im Beispiel) noch ein Knoten ohne Kante bleibt.
    conn = _fixture_db()
    _insert_node(conn, "/a", alt)
    _insert_node(conn, "/b", alt)
    _insert_edge(conn, "/a", "/b", neu)  # Kante NACH dem juengsten Knoten
    conn.commit()

    assert pruefen(conn) is None, "vollstaendig aktueller Bestand darf nicht anschlagen"
    conn.close()

    # C) Grenzwert -- Kante exakt so neu wie der juengste Knoten: kein Befund
    #    (>=, nicht >). Reine Textstempel ohne Sub-Sekunden-Drift.
    conn = _fixture_db()
    gleich = "2026-08-13T08:27:35+00:00"
    _insert_node(conn, "/a", gleich)
    _insert_edge(conn, "/a", "/b", gleich)
    _insert_node(conn, "/b", gleich)
    conn.commit()

    assert pruefen(conn) is None, "Gleichstand ist kein Stillstand"
    conn.close()

    # D) Leerer Bestand -- kein Absturz, keine Meldung.
    conn = _fixture_db()
    assert pruefen(conn) is None
    conn.close()

    print("selftest: schlaegt bei veralteter Kante an, schweigt bei aktuellem "
          "Bestand und bei Gleichstand, kein Absturz bei leerem Bestand. OK")


if __name__ == "__main__":
    main()
