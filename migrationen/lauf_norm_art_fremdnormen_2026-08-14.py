#!/usr/bin/env python3
"""Setzt norm_art bei den drei Normen fremder Herkunft -- NA-Nachtrag zu
docs/PLAN_NORMACHSEN_2026-08-14.md.

WARUM NUR DREI UND NICHT 85. Der Melder sagt "85 von 85 Normen ohne Art
(100%)" und klingt damit nach einem grossen Rueckstand. Gemessen 2026-08-14
ist er drei Zeilen gross:

    Normen gesamt                                   85
    davon mit FREMDER Quelle (norm_art ist Pflicht)  3
    davon eigene Quelle (norm_art NULL zulaessig)   82

Der Grund steht in schema.sql beim Pflichttrigger
knowledge_nodes_norm_art_pflicht_bi: "NULL bleibt der Normalfall fuer eigenes
Wissen (Hausregel, Selbsterfahrung) und braucht KEINEN Aufwand; Pflicht wird
norm_art nur, wenn source auf eine Norm FREMDER Herkunft zeigt." Eine
Massenbefuellung der 82 waere also nicht Fleiss, sondern eine Behauptung ueber
Saetze, die gar keine Art tragen muessen -- und der Plan verbietet sie
ausdruecklich.

DIE DREI EINZELN, jede am Wortlaut entschieden statt nach Muster:

  2200cd61  "§ 26 Abs. 3 WEG kappt jede vereinbarte Vertragslaufzeit"
            -> sollen. Der Satz verbietet ("Abweichungen davon sind
            unzulaessig"). Ein Verbot ist im Wertebereich sein/sollen/duerfen
            die Negativform von sollen; eine eigene Art dafuer gibt es nicht
            und braucht es nicht -- die Spannungspruefung unterscheidet
            Gebot und Verbot ueber den Inhalt, nicht ueber die Art.

  e60034e3  "wer die Jahresabrechnung 2026 erstellt"
            -> sollen. "§ 28 Abs. 2 WEG VERPFLICHTET den Verwalter zur
            Jahresabrechnung" -- eine Pflicht, ohne Auslegungsspielraum.

  7a6b27e1  "GEG heisst seit 29.07.2026 GModG -- §§ 71 bis 73 gestrichen"
            -> sein. Das ist KEINE Vorschrift, sondern eine Aussage darueber,
            welches Recht gilt: ein Gesetz wurde umbenannt, Paragrafen
            wurden gestrichen. Der Knoten schreibt nichts vor, er berichtet,
            dass Pflichten WEGGEFALLEN sind. Dieselbe Sorte wie die beiden
            einzigen Knoten, die heute schon eine Art tragen (4361e92d
            UN-Nachhaltigkeitsziele, ad4bb80e EU-Taxonomie) -- beide 'sein',
            beide mit demselben Zusatz im Titel: "geltendes Recht, nicht
            unsere Wahl".

Die Zuordnung ist damit KEINE Mustererkennung ueber die Quelle. Waere sie es,
wuerde 7a6b27e1 falsch als 'sollen' landen, weil sein source ein BGBl-Zitat
ist wie bei den anderen beiden. Der Unterschied liegt im Satz, nicht in der
Fundstelle -- deshalb steht hier eine Liste und kein Regex.

Idempotent: die WHERE-Klausel trifft nur Zeilen, deren norm_art noch NULL ist.
Ein zweiter Lauf aendert nichts und meldet das.

Aufruf:  python3 migrationen/lauf_norm_art_fremdnormen_2026-08-14.py [--apply]
         python3 migrationen/lauf_norm_art_fremdnormen_2026-08-14.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import sqlite3  # noqa: E402
import speicher  # noqa: E402

# Kennung -> Art, je Zeile am Wortlaut entschieden (Begruendung im Modulkopf).
ZUORDNUNG = {
    "2200cd61": "sollen",
    "e60034e3": "sollen",
    "7a6b27e1": "sein",
}


def offene(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Die Kandidaten, die den Wert noch nicht tragen."""
    treffer = []
    for kid, art in ZUORDNUNG.items():
        row = conn.execute(
            "SELECT norm_art FROM knowledge_nodes WHERE id = ?", (kid,)).fetchone()
        if row is None:
            print(f"WARNUNG: Knoten {kid} existiert nicht (mehr) -- uebersprungen")
            continue
        if not row[0]:
            treffer.append((kid, art))
    return treffer


def main() -> int:
    anwenden = "--apply" in sys.argv
    with speicher.lesen() as conn:
        kandidaten = offene(conn)
    print(f"=== norm_art fuer Fremdnormen ({'APPLY' if anwenden else 'DRY-RUN (kein --apply)'}) ===")
    if not kandidaten:
        print("nichts offen -- alle drei tragen ihre Art bereits")
        return 0
    for kid, art in kandidaten:
        print(f"  {kid} -> {art}")
    if not anwenden:
        return 0
    with speicher.schreiben() as conn:
        for kid, art in kandidaten:
            conn.execute(
                "UPDATE knowledge_nodes SET norm_art = ? "
                "WHERE id = ? AND (norm_art IS NULL OR norm_art = '')", (art, kid))
    with speicher.lesen() as conn:
        rest = offene(conn)
    assert not rest, f"nach dem Lauf noch offen: {rest}"
    print(f"gesetzt: {len(kandidaten)}")
    return 0


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    # Ausgangslage wie in der Wirklichkeit herstellen: die drei echten Knoten
    # entstanden VOR dem Pflichttrigger. Ein Einfuegen ohne norm_art bei
    # fremder Quelle wird heute zu Recht abgewiesen (knowledge_nodes_
    # norm_art_pflicht_bi, BEFORE INSERT) -- also mit Art einfuegen und
    # danach leeren. Der Trigger ist absichtlich nur am INSERT, siehe
    # schema.sql: eine UPDATE-Fassung wuerde jede Altzeile zwingen, ihre Art
    # rueckwirkend zu beantworten.
    for kid, art in (("2200cd61", "sein"), ("e60034e3", "sollen")):
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, source, "
            "norm_rang, norm_art, gilt_ab, norm_entscheidung, norm_entschieden_von, "
            "norm_entschieden_am, norm_entschieden_grund, created_at, updated_at) "
            "VALUES (?,?,?,?,?,1,?, '2026-01-01', 'norm_unbefristet','gesetzgeber','2026-01-01T00:00:00Z',"
            "'Probe','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')",
            (kid, "/p/" + kid, "T", "S", "BGBl I 2026", art))
    conn.execute("UPDATE knowledge_nodes SET norm_art = NULL WHERE id = '2200cd61'")
    offen = offene(conn)
    assert [k for k, _ in offen] == ["2200cd61"], offen
    # Der dritte Knoten fehlt in der DB -- das muss gemeldet, nicht geworfen werden.
    assert "7a6b27e1" not in [k for k, _ in offen]
    print("selftest ok (3 Faelle): nur Leere gelten als offen, "
          "vorhandene Art bleibt, fehlender Knoten wirft nicht")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        raise SystemExit(main())
