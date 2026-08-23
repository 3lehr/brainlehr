"""trennung.py -- Mandant und Kreis werden ERZWUNGEN (Auftrag B3,
docs/PLAN_GESAMTBAU_2026-08-21.md §2; BDW-E03, BDW-E06, BDW-E22, BDW-E23).

B1 hat die Spalten `mandant` und `kreis` sowie die Tabelle `geltung_je_kreis`
angelegt. Eine Spalte trennt nichts -- sie beschreibt nur. Hier steht die
Durchsetzung, und zwar an EINER Stelle: ein SQL-Fragment, das jeder Leseweg
in seine WHERE-Klausel haengt.

DIE BAUFORM IST NICHT NEU, SIE IST ABGESCHRIEBEN. knowledge_mcp_server.py
macht dasselbe seit dem 2026-08-11 fuer die Freigabe: `_NICHT_GESPERRT_SQL`
ist ein Textfragment, das in JEDER Teilabfrage steht -- Trefferliste,
Nachladeliste, Embedding-Erlaubnisliste, children_count, Kantenliste. Genau
deshalb taucht ein gesperrter Knoten "weder auf noch in children_count".
Eine zweite Bauform daneben zu stellen waere die Wiederholung des Fehlers,
den die Kantenliste am 2026-08-20 offenbart hat: die sichtbare Haelfte der
Sperre wirkte, die unsichtbare nicht, und es fiel niemandem auf.

WARUM EIN TEXTFRAGMENT UND KEIN PARAMETER: Die betroffenen Abfragen werden im
Server als f-Strings zusammengesetzt und tragen bereits stellungsgebundene
Parameter (fts_query, scope). Ein zusaetzlicher Parameter muesste an jeder
Aufrufstelle an der richtigen Position eingefuegt werden -- eine Fehlerquelle
pro Stelle. Die Werte werden darum als SQL-Literale eingesetzt, und `_lit()`
ist die einzige Stelle, die das tut (Hochkomma verdoppelt, NUL abgewiesen).

DIE ZAEHLUNG IST DER EIGENTLICHE PUNKT (BDW-E22). Der Hausmeister muss die
Regel nicht lesen; es genuegt, dass er eine VERAENDERUNG bemerkt -- gestern
drei Treffer, heute zwei. Dagegen hilft keine Rechtepruefung, weil nichts
Verbotenes gelesen wurde: es wurde nur gezaehlt. Deshalb gehoert das Fragment
nicht nur an die Abfrage, die Zeilen LIEFERT, sondern an jede, die eine ZAHL
bildet.

LEER HEISST ALLE. `kreis = ''` ist die weiteste Einstellung, nicht die
engste (siehe Spaltenkommentar in schema.sql). Der gesamte Bestand steht auf
`mandant='lokal', kreis=''` -- er bleibt damit fuer jeden Aufrufer des
Mandanten 'lokal' vollstaendig sichtbar, auch fuer den unbeglaubigten. Das
ist Absicht und nicht Nachlaessigkeit: "KEIN ABWEISEN OHNE AUSWEIS" ist eine
bestehende Entscheidung von kern/ausweis.py, und dieser Auftrag kippt sie
nicht nebenbei mit.
"""
from __future__ import annotations

import sqlite3

import ausweis

# Vorgabe der Spalte (schema.sql, Betreiberwort 2026-08-21) -- und damit auch
# der Mandant jedes Aufrufers, der keinen eigenen traegt.
VORGABE_MANDANT = "lokal"

# Kreis, den JEDER sieht. Nicht None und nicht NULL: eine NOT-NULL-Spalte mit
# konstantem DEFAULT ist die einzige Bauform, die kern/schema_nachzug.py in
# eine gewachsene Datenbank nachziehen kann.
KREIS_ALLE = ""


def _lit(wert: str) -> str:
    """Ein SQLite-Textliteral. Einzige Stelle im Haus, die einen Mandanten-
    oder Kreisnamen in SQL einsetzt."""
    wert = str(wert)
    if "\x00" in wert:
        raise ValueError("Mandant/Kreis darf kein NUL-Zeichen enthalten")
    return "'" + wert.replace("'", "''") + "'"


def mandant_von(ausw) -> str:
    return getattr(ausw, "mandant", None) or VORGABE_MANDANT


def kreise_von(ausw) -> tuple[str, ...]:
    return tuple(getattr(ausw, "kreise", ()) or ())


def sichtbar_sql(ausw=None, alias: str = "") -> str:
    """Das Fragment fuer die WHERE-Klausel. `alias` ist der Tabellenpraefix
    einschliesslich Punkt ('n.', 's.', ''), weil dieselbe Bedingung in
    Abfragen mit und ohne JOIN steht."""
    if ausw is None:
        ausw = ausweis.loese_auf()
    a = alias
    kreise = (KREIS_ALLE, *kreise_von(ausw))
    liste = ", ".join(_lit(k) for k in dict.fromkeys(kreise))
    return f"{a}mandant = {_lit(mandant_von(ausw))} AND {a}kreis IN ({liste})"


def sichtbar_sql_wenn_spalte(conn: sqlite3.Connection, ausw=None, alias: str = "",
                             tabelle: str = "knowledge_nodes") -> str:
    """Wie sichtbar_sql(), aber '1' auf einer Datenbank OHNE die Spalten.

    Nur fuer Aufrufer, die ihre Verbindung NUR LESEND oeffnen und die
    fehlende Spalte darum nicht nachziehen koennen (pflege/export_offen.py).
    Ueber knowledge_mcp_server.get_db() ist der Fall unmoeglich -- dort
    laeuft ensure_schema vorher.

    Eine Datenbank vor B1 hat genau einen Mandanten, weil es den Begriff
    dort nicht gab. '1' ist deshalb die richtige Antwort und nicht die
    bequeme: es gibt nichts zu trennen.
    """
    spalten = {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}
    if not {"mandant", "kreis"} <= spalten:
        return "1"
    return sichtbar_sql(ausw, alias)


def sichtbar(ausw, mandant: str | None, kreis: str | None) -> bool:
    """Dieselbe Entscheidung als Zeilenpruefung. Muss mit sichtbar_sql()
    denselben Wert liefern -- SQL-Filter und Row-Check sind zwei Wege zu
    derselben Aussage, wie bei _ist_gesperrt/_NICHT_GESPERRT_SQL."""
    mandant = VORGABE_MANDANT if mandant is None else mandant
    kreis = KREIS_ALLE if kreis is None else kreis
    return (mandant == mandant_von(ausw)
            and (kreis == KREIS_ALLE or kreis in kreise_von(ausw)))


# ── BDW-E03: wirksames Recht ist die SCHNITTMENGE ────────────────────────
#
# "Rolle ∩ Objekt ∩ Zweck", und Mandant verengt zusaetzlich. Die Achsen
# werden NICHT neu erfunden -- jede liest die Tabelle, die es schon gibt:
#
#   Rolle × Objekt -> kern/ausweis.py::ROLLEN (wissen:/lehre:/kante:lesen)
#   Rolle × Zweck  -> knowledge_mcp_server.py::_KNOWLEDGE_READ_PROJEKTION
#                     bzw. _KNOWLEDGE_READ_VOLLZUGRIFF
#   Mandant        -> diese Datei
#
# Das ist die Blaupause aus dem Auftrag: `raumplaner` hatte schon einen engen
# Zugang je Datensatz, nur verdrahtet statt als Achse. Sie bleibt stehen und
# ist hier die Zweckachse; hinzu kommen Objekt und Mandant.
#
# Die Tabellen werden ABSICHTLICH spaet importiert und nicht kopiert:
# melder/pruefer.py und mehrere Tests biegen sie zur Laufzeit um. Eine Kopie
# hier waere eine zweite Wahrheit, die beim naechsten Eintrag auseinanderlaeuft.

OBJEKTE = ("knoten", "lehre", "kante")
OBJEKT_MODUL = {"knoten": "wissen", "lehre": "lehre", "kante": "kante"}

# Zwecke, die im Haus vorkommen. 'allgemein' ist der unbeschraenkte interne
# Zugang (kein Serving-Zweck); die uebrigen stammen aus der Projektionstabelle.
ZWECK_ALLGEMEIN = "allgemein"
ZWECKE = (ZWECK_ALLGEMEIN, "raumplanung", "wartung")


def wirksames_recht(ausw, *, objekt: str, zweck: str, mandant: str) -> bool:
    """Vorgabe ist DENY. Jede der vier Achsen kann allein verweigern; keine
    kann erweitern, was eine andere verweigert -- das ist der Unterschied
    zwischen einer Schnittmenge und einer Liste von Ausnahmen."""
    if mandant != mandant_von(ausw):
        return False
    modul = OBJEKT_MODUL.get(objekt)
    if modul is None:
        return False
    if ausweis.bezug_fuer(ausw, f"{modul}:lesen") is None:
        return False
    import knowledge_mcp_server as _server        # spaet, siehe oben
    if _server._KNOWLEDGE_READ_VOLLZUGRIFF.intersection(ausw.rollen):
        return zweck == ZWECK_ALLGEMEIN
    return any(zweck == z for rolle in ausw.rollen
               for z, _feld in _server._KNOWLEDGE_READ_PROJEKTION.get(rolle, ()))


# ── BDW-E23: Geltung je Kreis ────────────────────────────────────────────

def geltung(conn: sqlite3.Connection, art: str, ids, kreise) -> dict:
    """{eintrag_id: (gilt_ab, gilt_bis)} fuer die Kreise des Aufrufers.

    Wer HIER keinen Eintrag hat, steht nicht im Ergebnis und behaelt damit
    die Spaltenvorgabe (knowledge_nodes.gilt_ab/gilt_bis) -- so steht es im
    Tabellenkommentar in schema.sql, und so ist es auch die einzige Lesart,
    die den Bestand nicht rueckwirkend umdeutet.

    EINE Abfrage fuer alle Kennungen, nicht eine je Zeile: eine Suche mit 50
    Treffern wuerde sonst 50 Abfragen stellen, und die Geltung ist eine
    Anzeigefrage.
    """
    ids = [i for i in dict.fromkeys(ids) if i]
    kreise = [k for k in dict.fromkeys(kreise) if k]
    if not ids or not kreise:
        return {}
    p_ids = ",".join("?" * len(ids))
    p_kr = ",".join("?" * len(kreise))
    try:
        zeilen = conn.execute(
            f"SELECT eintrag_id, gilt_ab, gilt_bis FROM geltung_je_kreis "
            f"WHERE eintrag_art = ? AND eintrag_id IN ({p_ids}) AND kreis IN ({p_kr}) "
            # ponytail: bei mehreren passenden Kreisen gewinnt der alphabetisch
            # erste -- deterministisch statt zufaellig. Wer eine Vorrangregel
            # zwischen Kreisen braucht (engster gewinnt, juengster gewinnt),
            # baut sie hier ein; heute traegt kein Ausweis mehr als einen.
            f"ORDER BY kreis DESC",
            (art, *ids, *kreise)).fetchall()
    except sqlite3.OperationalError:
        return {}                     # Datenbank ohne die Tabelle (vor B1)
    return {z[0]: (z[1], z[2]) for z in zeilen}


def demo() -> None:
    """Kleinster Lauf, der fehlschlaegt, wenn die Logik bricht."""
    a = ausweis.Ausweis(name="x", rollen=("leser",), beglaubigt=True,
                        mandant="lokal", kreise=("vorstand",))
    assert sichtbar(a, "lokal", "")
    assert sichtbar(a, "lokal", "vorstand")
    assert not sichtbar(a, "lokal", "aufsicht")
    assert not sichtbar(a, "fremd", "")
    frag = sichtbar_sql(a, "n.")
    assert frag == "n.mandant = 'lokal' AND n.kreis IN ('', 'vorstand')", frag
    # Hochkomma im Namen darf die Klausel nicht sprengen.
    b = ausweis.Ausweis(name="y", rollen=(), beglaubigt=False, mandant="o'brien")
    assert sichtbar_sql(b) == "mandant = 'o''brien' AND kreis IN ('')"
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (mandant TEXT, kreis TEXT)")
    conn.executemany("INSERT INTO t VALUES (?,?)",
                     [("lokal", ""), ("lokal", "vorstand"), ("lokal", "aufsicht"),
                      ("fremd", "")])
    assert conn.execute(f"SELECT COUNT(*) FROM t WHERE {sichtbar_sql(a)}").fetchone()[0] == 2
    assert conn.execute(f"SELECT COUNT(*) FROM t WHERE {sichtbar_sql(b)}").fetchone()[0] == 0
    print("trennung: demo ok")


if __name__ == "__main__":
    demo()
