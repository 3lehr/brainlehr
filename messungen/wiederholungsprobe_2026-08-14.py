#!/usr/bin/env python3
"""Haette der Abruf die WIEDERHOLUNG verhindert? -- der erste Aufbau mit einem
korpusunabhaengigen Goldstandard.

DIE FRAGE, und warum sie eine andere ist als bisher: Bisher wurde gemessen, ob
der Abruf zu einer gestellten Aufgabe etwas Passendes liefert. Der Wert des
Speichers ist aber nicht "findet er irgendwas", sondern "verhindert er, dass
derselbe Fehler ein zweites Mal passiert". Genau dafuer gibt es hier Daten,
die niemand fuer eine Messung gebaut hat.

DER GOLDSTANDARD: 61 Lehren tragen occurrences>=2, davon 35 mit ECHTEM
Zeitabstand zwischen first_seen und last_seen (1 bis 13+ Tage). Jeder dieser
35 Faelle ist ein dokumentierter Ausfall: die Lehre stand bereits im Speicher,
und der Fehler passierte trotzdem erneut. Die Zuordnung "das ist derselbe
Fehler" stammt aus einem same_as-Aufruf eines Menschen oder Agenten -- nicht
aus dem Abruf, den wir hier pruefen. Das macht sie unabhaengig.

WAS DIE VORGAENGERMESSUNG FALSCH MACHTE (Knoten 34ef6d8e, 2026-08-07): Dort
stand die Loesung woertlich im Prompt. Gemessen wurde damit nur, ob es hilft,
einem Modell die Antwort hinzuschreiben. Hier ist die Anfrage die SITUATION
des zweiten Vorfalls, nie die Loesung.

DREI LECKS, und nur zwei davon lassen sich schliessen:

  ZEITLECK -- geschlossen. Gewertet wird nur gegen Eintraege, die VOR dem
  Wiederholungsdatum existierten. Sonst misst man Zukunftswissen.

  LOESUNGSLECK -- geschlossen. Die Anfrage enthaelt weder die Lehrkennung noch
  den Loesungstext (resolution/prevention werden nicht mitgegeben).

  WORTLAUTLECK -- NICHT schliessbar, nur ausweisbar. Der Text der Wiederholung
  wurde NACH dem Vorfall geschrieben, moeglicherweise von jemandem, der die
  alte Lehre gerade gelesen hatte. Er teilt dann Vokabular mit ihr, und der
  Abruf hat es leichter als in der echten Lage. Die Messung ist dadurch
  OPTIMISTISCH verzerrt; ein schlechtes Ergebnis waere also besonders
  aussagekraeftig, ein gutes nur bedingt.

DIE ARME (das ist "die Konkurrenz"):
  brainlehr  der volle Weg, wie ihn eine Sitzung nimmt (query() des Hooks)
  bm25       nur Stichwortsuche ueber lessons_fts -- die naive Alternative
  zufall     zufaellige Lehren gleicher Anzahl, als Nullband

Der Zufallsarm ist der wichtigste Vergleich und fehlt in den bisherigen
Messungen: ohne ihn weiss man nicht, ob ein Treffer Leistung oder Grundrate
ist. Bei 905 Lehren und 5 Treffern liegt die Grundrate bei 0,55 Prozent.

Aufruf:  python3 messungen/wiederholungsprobe_2026-08-14.py [--schreibe DATEI]
         python3 messungen/wiederholungsprobe_2026-08-14.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder", "messungen")]

import json
import random
import re
import sqlite3

import speicher  # noqa: E402
import zeitmarke  # noqa: E402

TREFFERZAHL = 5  # so viele Lehren sieht eine Sitzung im Recall-Block


def faelle(conn: sqlite3.Connection) -> list[dict]:
    """Lehren, die sich WIEDERHOLT haben, mit echtem Zeitabstand."""
    aus = []
    for r in conn.execute(
        "SELECT id, description, first_seen, last_seen, occurrences "
        "FROM lessons_learned WHERE occurrences >= 2"
    ):
        if r["first_seen"][:10] >= r["last_seen"][:10]:
            continue  # am selben Tag -- die Lehre war noch keine Vorgeschichte
        aus.append({
            "lehre": r["id"], "text": r["description"],
            "erst": r["first_seen"], "wiederholung": r["last_seen"],
            "vorkommen": r["occurrences"],
        })
    return aus


def anfrage_aus(text: str, lehre_id: str) -> str:
    """Die Anfrage ist die SITUATION, nicht die Loesung.

    Entfernt die eigene Kennung und jede andere L-xxxxxx-Kennung -- sonst
    fuehrt der Text den Abruf an der Nase zum Ziel, und genau das war der
    Fehler der Messung vom 2026-08-07.
    """
    ohne = re.sub(r"\bL-[0-9a-f]{6}\b", " ", text)
    return re.sub(r"\s+", " ", ohne).strip()


def _vorher(conn: sqlite3.Connection, stichtag: str) -> set[str]:
    """Lehren, die es am Stichtag schon gab. Schliesst das Zeitleck."""
    return {r[0] for r in conn.execute(
        "SELECT id FROM lessons_learned WHERE first_seen < ?", (stichtag,))}


def arm_bm25(conn, anfrage: str, erlaubt: set[str], n: int) -> list[str]:
    """Nur Stichwortsuche. Die naive Alternative zu allem, was brainlehr baut."""
    worte = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß_]{4,}", anfrage)][:24]
    if not worte:
        return []
    ausdruck = " OR ".join(f'"{w}"' for w in worte)
    try:
        treffer = [r[0] for r in conn.execute(
            "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
            "WHERE lessons_fts MATCH ? ORDER BY bm25(lessons_fts) LIMIT 400", (ausdruck,))]
    except sqlite3.Error:
        return []
    return [t for t in treffer if t in erlaubt][:n]


def arm_brainlehr(anfrage: str, erlaubt: set[str], n: int) -> list[str]:
    """Der volle Weg, wie ihn eine echte Sitzung nimmt: keywords() zerlegt den
    Text, query() bewertet ueber bm25 UND Vektoren, kappt per Rauschteppich
    und sortiert nach trust_score/Scope.

    EINSCHRAENKUNG, die das Ergebnis OPTIMISTISCH macht und benannt gehoert:
    query() laeuft gegen den HEUTIGEN Bestand; das Zeitleck wird erst danach
    geschlossen, indem spaetere Lehren aus der Trefferliste geworfen werden.
    Damit ruecken Ziele nach oben, die in der echten Lage von juengeren
    Eintraegen verdraengt worden waeren. Der bm25-Arm hat denselben Vorteil
    (Filter nach der Bewertung), die Arme sind also untereinander fair.
    """
    import knowledge_recall_hook as hook
    kws = hook.keywords(anfrage)
    if not kws:
        return []
    try:
        _, lehren = hook.query(kws)
    except Exception:
        return []
    ids = [l["id"] for l in lehren if isinstance(l, dict) and l.get("id")]
    return [i for i in ids if i in erlaubt][:n]


def arm_zufall(erlaubt: set[str], n: int, wuerfel: random.Random) -> list[str]:
    """Nullband. Ohne ihn ist kein Treffer von der Grundrate zu unterscheiden."""
    pool = sorted(erlaubt)
    return wuerfel.sample(pool, min(n, len(pool)))


def lauf(n: int = TREFFERZAHL, saat: int = 20260814) -> dict:
    wuerfel = random.Random(saat)
    ergebnis = {"erhoben_am": zeitmarke.jetzt(), "trefferzahl": n, "faelle": []}
    with speicher.lesen() as conn:
        alle = faelle(conn)
        for f in alle:
            erlaubt = _vorher(conn, f["wiederholung"])
            erlaubt.discard(f["lehre"])  # die Zielzeile selbst zaehlt nicht als "vorher"
            erlaubt.add(f["lehre"])      # ... sie existierte aber, das ist der Punkt
            anfrage = anfrage_aus(f["text"], f["lehre"])
            b = arm_bm25(conn, anfrage, erlaubt, n)
            bl = arm_brainlehr(anfrage, erlaubt, n)
            z = arm_zufall(erlaubt, n, wuerfel)
            ergebnis["faelle"].append({
                "lehre": f["lehre"], "vorkommen": f["vorkommen"],
                "erst": f["erst"][:10], "wiederholung": f["wiederholung"][:10],
                "korpus_vorher": len(erlaubt),
                "brainlehr_treffer": f["lehre"] in bl,
                "brainlehr_rang": (bl.index(f["lehre"]) + 1) if f["lehre"] in bl else None,
                "brainlehr_lieferte": len(bl),
                "bm25_treffer": f["lehre"] in b,
                "bm25_rang": (b.index(f["lehre"]) + 1) if f["lehre"] in b else None,
                "zufall_treffer": f["lehre"] in z,
            })
    n_f = len(ergebnis["faelle"]) or 1
    ergebnis["zusammenfassung"] = {
        "faelle": len(ergebnis["faelle"]),
        "brainlehr_trefferquote": round(sum(c["brainlehr_treffer"] for c in ergebnis["faelle"]) / n_f, 3),
        "brainlehr_schwieg": sum(1 for c in ergebnis["faelle"] if c["brainlehr_lieferte"] == 0),
        "bm25_trefferquote": round(sum(c["bm25_treffer"] for c in ergebnis["faelle"]) / n_f, 3),
        "zufall_trefferquote": round(sum(c["zufall_treffer"] for c in ergebnis["faelle"]) / n_f, 3),
    }
    return ergebnis


def _selftest() -> None:
    # anfrage_aus entfernt JEDE Lehrkennung, nicht nur die eigene -- eine
    # fremde Kennung im Text waere ein genauso guter Wegweiser.
    a = anfrage_aus("Wie L-abc123 zeigt, siehe auch L-def456: Fehler X", "L-abc123")
    assert "L-abc123" not in a and "L-def456" not in a, a
    assert "Fehler X" in a

    # Nullband: bei kleinem Pool zieht es nicht mehr, als da ist.
    z = arm_zufall({"L-1", "L-2"}, 5, random.Random(1))
    assert len(z) == 2, z

    # Zeitleck: _vorher darf nur Aelteres liefern.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE lessons_learned (id TEXT, description TEXT, "
                 "first_seen TEXT, last_seen TEXT, occurrences INTEGER)")
    conn.execute("INSERT INTO lessons_learned VALUES ('L-alt','a','2026-08-01','2026-08-01',1)")
    conn.execute("INSERT INTO lessons_learned VALUES ('L-neu','b','2026-08-20','2026-08-20',1)")
    v = _vorher(conn, "2026-08-10")
    assert v == {"L-alt"}, v

    # faelle(): gleicher Tag zaehlt NICHT -- die Lehre war dann keine Vorgeschichte.
    conn.execute("INSERT INTO lessons_learned VALUES ('L-gleich','c','2026-08-05','2026-08-05',3)")
    conn.execute("INSERT INTO lessons_learned VALUES ('L-echt','d','2026-08-05','2026-08-09',2)")
    ids = {f["lehre"] for f in faelle(conn)}
    assert ids == {"L-echt"}, ids
    print("selftest ok (4 Faelle): Kennungen gestrippt, Nullband gedeckelt, "
          "Zeitleck geschlossen, Gleichtagsfaelle ausgeschlossen")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        erg = lauf()
        print(json.dumps(erg["zusammenfassung"], ensure_ascii=False, indent=2))
        if "--schreibe" in sys.argv:
            ziel = _Path(sys.argv[sys.argv.index("--schreibe") + 1])
            ziel.write_text(json.dumps(erg, ensure_ascii=False, indent=2), encoding="utf-8")
            print("geschrieben:", ziel)
