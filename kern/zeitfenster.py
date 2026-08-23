#!/usr/bin/env python3
"""zeitfenster.py -- Aufgabe 88 Schritt 1: eine Anfrage optional auf einen
ZEITRAUM einschraenken ("das wurde letzte Woche gemacht").

WAHL created_at GEGEN updated_at: "wann wurde das GEMACHT" fragt nach der
Entstehung, nicht der letzten Aenderung -- ein Knoten, der vor drei Monaten
angelegt und gestern nur redigiert wurde, ist nicht "letzte Woche gemacht"
worden. Gefiltert wird deshalb auf `created_at`. Das laesst automatisch
NICHTS durch, was aelter ist, aber ZEIGT auch Knoten, die seither weiter
bearbeitet wurden -- Bearbeitung nach der Anlage aendert nicht, wann etwas
entstand.

BAUFORM-PRUEFUNG (Auftrag verlangt SELECT DISTINCT vor jeder Vergleichslogik,
siehe L-ec167a -- der Bestand mischt bei Datumsfeldern oft volle Zeitstempel
mit reinen Datumsangaben): gemessen 2026-08-13 gegen den echten Bestand,
2183 von 2183 Zeilen in knowledge_nodes.created_at UND .updated_at sind exakt
25 Zeichen lang, Form 'YYYY-MM-DDTHH:MM:SS+ZZ:ZZ' (schema.sql-Vorgabewert
nutzt SQL-strftime mit dem Format '%Y-%m-%dT%H:%M:%S+01:00') -- keine Mischform in diesem Feld,
anders als bei gilt_ab/gilt_bis (Schritt 2, hier ausdruecklich nicht Teil des
Auftrags). Trotzdem vergleicht dieses Modul bewusst nur die ersten 10 Zeichen
(das Datum) und nicht den vollen Zeitstempel: von/bis kommen aus einer
Anfrage wie "letzte Woche" in Tagesgranularitaet ('2026-08-01'), nicht mit
Uhrzeit -- ein Vergleich des vollen Strings wuerde einen 'bis'-Tag an dessen
Uhrzeit 00:00:00 abschneiden statt ihn vollstaendig einzuschliessen. Diese
Kuerzung macht das Modul zusaetzlich robust, falls doch einmal eine
Mischform auftaucht (kurze Form waere dann ohnehin nur das Datum).

OPTIONAL, WICHTIGSTE EIGENSCHAFT: von=None und bis=None lassen die jeweilige
Grenze offen. Ruft niemand mit einem Zeitraum auf, verhaelt sich `treffer()`
exakt wie `anfrage_erweiterung.treffer()` -- der Abruf bei jeder Nachricht
aendert sein Vorgabeverhalten nicht.

NOCH NICHT VERDRAHTET (Schritt 1 endet hier, Auftragsgrenze): der laufende
Abrufpfad in knowledge_mcp_server.py (dort z. B. `_or_query()`) ist tabu.
Die spaetere Anschlussstelle waere dort, wo eine Anfrage bereits erweitert
wird (`anfrage_erweiterung.erweitere_anfrage`) -- ein optionales
`von`/`bis`-Paar aus der MCP-Anfrage durchgereicht an `treffer()` hier.

Aufruf:
    python3 kern/zeitfenster.py --selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import ausschreibekatalog as ak  # noqa: E402
import speicher  # noqa: E402

import anfrage_erweiterung as ae  # noqa: E402


def im_zeitraum(zeitstempel: str, von: str | None, bis: str | None) -> bool:
    """Datumsvergleich in Tagesgranularitaet (siehe Moduldoc). `von`/`bis`
    sind inklusive Grenzen ('letzte Woche' schliesst Montag UND Sonntag ein).
    None laesst die jeweilige Seite offen."""
    datum = zeitstempel[:10]
    if von is not None and datum < von[:10]:
        return False
    if bis is not None and datum > bis[:10]:
        return False
    return True


def treffer(
    anfrage: str,
    von: str | None = None,
    bis: str | None = None,
    db=None,
    katalog: dict[str, list[str]] | None = None,
) -> set[tuple[str, str]]:
    """Wie anfrage_erweiterung.treffer(anfrage): (typ, id) je Dokument mit
    Inhaltstreffer. Zusaetzlich, NUR wenn von/bis gesetzt sind, auf Knoten
    eingeschraenkt, deren created_at im Zeitraum liegt. Lehren fuehren hier
    noch kein eigenes Zeitfeld -- ohne Zeitraum bleiben sie unveraendert
    dabei, MIT Zeitraum werden sie (mangels Entscheidung, welches Feld bei
    Lehren "gemacht" beantwortet) aus der Treffermenge ausgeschlossen statt
    geraten."""
    inhaltstreffer = ae.treffer(anfrage, db=db, katalog=katalog)
    if von is None and bis is None:
        return inhaltstreffer

    knoten_ids = {id_ for typ, id_ in inhaltstreffer if typ == "knoten"}
    if not knoten_ids:
        return set()

    with speicher.lesen(db) as conn:
        platzhalter = ",".join("?" * len(knoten_ids))
        zeilen = conn.execute(
            f"SELECT id, created_at FROM knowledge_nodes WHERE id IN ({platzhalter})",
            tuple(knoten_ids),
        ).fetchall()

    return {
        ("knoten", id_)
        for id_, created_at in zeilen
        if im_zeitraum(created_at, von, bis)
    }


def _selftest() -> None:
    # 1) im_zeitraum: Grenzwerte inklusive.
    assert im_zeitraum("2026-08-05T10:00:00+01:00", "2026-08-01", "2026-08-07")
    assert im_zeitraum("2026-08-01T00:00:00+01:00", "2026-08-01", "2026-08-07")  # unterer Rand
    assert im_zeitraum("2026-08-07T23:59:59+01:00", "2026-08-01", "2026-08-07")  # oberer Rand
    assert not im_zeitraum("2026-07-31T23:59:59+01:00", "2026-08-01", "2026-08-07")
    assert not im_zeitraum("2026-08-08T00:00:00+01:00", "2026-08-01", "2026-08-07")
    assert im_zeitraum("2026-08-05T10:00:00+01:00", None, None)

    # 2) rot-vor-gruen gegen den echten Bestand: 'impl' ohne Zeitraum vs.
    #    mit einem Zeitraum, der garantiert nicht alles trifft (ein einziger
    #    Tag lange vor der ersten Anlage) -- Teilmenge, echt kleiner.
    ohne = treffer("impl")
    mit_engem_fenster = treffer("impl", von="1999-01-01", bis="1999-01-02")
    assert mit_engem_fenster <= ohne
    assert len(mit_engem_fenster) < len(ohne), (len(mit_engem_fenster), len(ohne))

    # 3) Negativfall: ein Zeitraum, der alles umfasst, aendert nichts.
    alles = treffer("impl", von="2000-01-01", bis="2100-01-01")
    assert alles == {t for t in ohne if t[0] == "knoten"}

    print("zeitfenster: alle Selbsttests gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(treffer(" ".join(sys.argv[1:]) or "impl"))
