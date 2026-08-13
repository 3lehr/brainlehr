#!/usr/bin/env python3
"""anfrage_erweiterung.py -- Aufgabe 65 Schritt 2: den Ausschreibekatalog
(kern/ausschreibekatalog.py) auf die ANFRAGE anwenden, nie auf den
gespeicherten Text.

WARUM NICHT knowledge_mcp_server.py._or_query() DIREKT GEAENDERT: das waere
die naheliegende Integrationsstelle ("den Abrufpfad an der Stelle, an der die
Anfrage zerlegt wird", Plan docs/PLAN_AUSSCHREIBEKATALOG_2026-08-13.md), aber
diese Datei ist laut Auftragsgrenzen tabu -- ein zweiter Agent haelt sie im
selben Baum. Diese Datei liefert die reine Erweiterungsfunktion UND einen
eigenen, wortgrenzenbasierten Treffer-Zaehler zum Beleg (rot-vor-gruen ohne
die tabu Datei anzufassen). Die tatsaechliche Verdrahtung in _or_query() ist
eine spaetere, einzeilige Ergaenzung (`anfrage = " ".join(erweitere_anfrage
(anfrage))` vor dem bestehenden `_or_query(anfrage)`-Aufruf) -- ABWEICHUNG
gemeldet, nicht heimlich nachgeholt.

DIE GRENZE, DIE NICHT VERHANDELBAR IST: `erweitere_anfrage()` liest nur und
schreibt nirgends. Sie ERGAENZT die Wortliste der Anfrage um die lange Form,
wo die Kurzform im Katalog steht -- sie ERSETZT nichts, die Kurzform bleibt
selbst Teil der Anfrage. Der gespeicherte Text (knowledge_nodes,
lessons_learned) wird von keiner Funktion hier je beschrieben (siehe
kern/speicher.lesen(), mode=ro -- ein Schreibversuch scheitert dort sofort).
Grund: `L-d8c5fb` (siehe kern/ausschreibekatalog.py-Docstring) -- eine
still aufgeloeste Abkuerzung im QUELLFELD wanderte in sieben abgeleitete
Fundstellen, zwei davon oeffentlich.

Aufruf:
    python3 kern/anfrage_erweiterung.py --selftest
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import ausschreibekatalog as ak  # noqa: E402
import speicher  # noqa: E402

_WORT = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


def erweitere_anfrage(anfrage: str, katalog: dict[str, str] | None = None) -> list[str]:
    """Anfrage-Woerter, ERGAENZT um die lange Form je Katalog-Kurzform --
    nichts wird ersetzt oder entfernt. `katalog=None` liest den aktuellen
    Vorschlag aus ausschreibekatalog.katalog() (Bestand, read-only)."""
    if katalog is None:
        katalog = ak.katalog()
    begriffe = _WORT.findall(anfrage.lower())
    ergaenzt = list(begriffe)
    for wort in begriffe:
        lang = katalog.get(wort)
        if lang and lang not in ergaenzt:
            ergaenzt.append(lang)
    return ergaenzt


def _dokumente(conn) -> list[tuple[str, str, str]]:
    knoten = conn.execute(
        "SELECT id, COALESCE(title,'')||' '||COALESCE(summary,'')||' '||COALESCE(content,'') "
        "FROM knowledge_nodes"
    ).fetchall()
    lehren = conn.execute(
        "SELECT id, COALESCE(description,'')||' '||COALESCE(root_cause,'')||' '"
        "||COALESCE(resolution,'')||' '||COALESCE(prevention,'') FROM lessons_learned"
    ).fetchall()
    return [("knoten", r[0], r[1]) for r in knoten] + [("lehre", r[0], r[1]) for r in lehren]


def treffer(anfrage: str, db=None, katalog: dict[str, str] | None = None) -> set[tuple[str, str]]:
    """(typ, id) je Dokument, das MINDESTENS einen erweiterten Anfragebegriff
    als eigenes Wort enthaelt -- der Beleg fuer rot-vor-gruen: mit `katalog={}`
    (keine Erweiterung) simuliert das die heutige Kurzform-Suche, mit dem
    echten Katalog die erweiterte."""
    begriffe = erweitere_anfrage(anfrage, katalog)
    muster = [ak._wortgrenze(b) for b in begriffe]
    with speicher.lesen(db) as conn:
        dokumente = _dokumente(conn)
    return {
        (typ, id_)
        for typ, id_, text in dokumente
        if any(muster_einzeln.search(text) for muster_einzeln in muster)
    }


def _selftest() -> None:
    # 1) Ergaenzt, ersetzt nicht: die Kurzform bleibt in der Wortliste.
    ergaenzt = erweitere_anfrage("impl gesucht", katalog={"impl": "implementation"})
    assert "impl" in ergaenzt and "implementation" in ergaenzt, ergaenzt

    # 2) Ohne Katalogtreffer bleibt die Anfrage unveraendert (bis auf Kleinschreibung).
    unveraendert = erweitere_anfrage("xyz123", katalog={"impl": "implementation"})
    assert unveraendert == ["xyz123"], unveraendert

    # 3) Rot vor gruen an 'impl', gegen den echten Bestand: ohne Katalog
    #    (leeres Woerterbuch) findet die Anfrage nur die woertliche Kurzform,
    #    mit dem echten Katalog mehr Dokumente -- die lange Form dazu.
    vorher = treffer("impl", katalog={})
    nachher = treffer("impl")  # nutzt ausschreibekatalog.katalog() live
    assert len(nachher) > len(vorher), (len(vorher), len(nachher))
    print(f"impl: vorher {len(vorher)} Dokumente, nachher {len(nachher)}")

    # 4) Negativfall: 'db' verschlechtert sich nicht (Katalog nimmt 'db' laut
    #    ausschreibekatalog nicht auf, also identische Treffermenge).
    vorher_db = treffer("db", katalog={})
    nachher_db = treffer("db")
    assert nachher_db >= vorher_db, "db darf sich nie verschlechtern"
    assert len(nachher_db) == len(vorher_db), "db sollte unveraendert bleiben (nicht im Katalog)"

    print("anfrage_erweiterung: alle Selbsttests gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(erweitere_anfrage(" ".join(sys.argv[1:]) or "impl"))
