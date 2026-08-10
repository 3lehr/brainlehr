#!/usr/bin/env python3
"""Jeder Lese- und Schreibvorgang am Speicher wird eine Zeile im Gespraech.

Anlass (S2, docs/PLAN_DESTILLE_2026-08-09.md): Der Abruf ist sichtbar
(<knowledge-recall>), jeder SCHREIBVORGANG war es nicht. Daraus die Lehre
L-706807: ein Agent meldete "gespeichert", die Herkunftsschranke hatte
abgewiesen (status='rejected', query='source_fehlt'), niemand sah es --
weil zwischen dem tatsaechlichen Ergebnis und dem, was im Chat stand, nur
die Selbstauskunft des Agenten lag.

QUELLE ist access_log, nicht eine zweite Buchfuehrung (Betreiber-Vorgabe):
jeder Schreibpfad (knowledge_add/_update/lesson_record/annahme_erfassen/...)
schreibt dort bereits status IN ('started','completed','rejected','failed')
UND, bei einer Ablehnung, den kurzen Grund im Feld query (z.B.
'source_fehlt') -- lesbarer und stabiler als der volle Fehlertext, den der
MCP-Aufruf sonst zurueckgibt.

KENNUNG: bei den meisten Aktionen steht sie schon direkt im Protokoll
(node_path bei add/update/relation_*/freigeben/zurueckziehen; query traegt
die relation_id bzw. lesson_id bei relation_add/lesson_update/lesson_delete,
und 'annahme_id -> status' bei annahme_entscheiden). Zwei Ausnahmen legen
die ID nicht mit ab, weil beim ERSTEN Anlegen einer Lehre/Annahme nur ihr
TEXT geloggt wird (query=description bzw. query=annahme): dort wird die ID
per Text-Abgleich aus lessons_learned/annahmen nachgeschlagen. Schlaegt der
Abgleich fehl (z.B. zwei identische Texte), faellt die Kennung auf den
gekuerzten Text zurueck -- schlechter lesbar, aber nie erfunden.

FEHLKLASSE dieses Melders: unsichtbarer Schreibvorgang (L-706807) -- ein
Agent behauptet ein Ergebnis, das mit dem Protokoll nicht uebereinstimmt,
und niemand widerspricht.
PREIS EINES FEHLALARMS: gering. Die Zeile stammt direkt aus einer bereits
committeten access_log-Zeile -- sie kann eine falsche/gekuerzte Kennung
zeigen (Textabgleich misslingt), aber nie einen Vorgang behaupten, der
nicht stattfand.

Aufruf:
    python3 sichtbarkeit.py --seit 0          # alle Zeilen ab id>0
    python3 sichtbarkeit.py --hook            # fuer PostToolUse: Marke je Sitzung
    python3 sichtbarkeit.py --selftest
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
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))  # diese Datei liegt IN der Wurzel: eine Ebene, nicht zwei
import ort  # noqa: E402

# Aktionen, die einen SCHREIBVORGANG bedeuten -- nicht browse/read/search/
# relation_list, und nicht die annahme-Liste (gleiche Aktion 'annahme',
# aber query='liste:...' statt eines Textes/einer ID, siehe annahme_liste()
# in knowledge_mcp_server.py).
SCHREIB_AKTIONEN = {
    "add", "update", "lesson", "lesson_update", "lesson_delete",
    "annahme", "relation_add", "relation_update", "relation_remove",
    "freigeben", "zurueckziehen",
}

# Lesen wurde bis 2026-08-10 gar nicht gemeldet -- der Melder kannte nur
# Schreibvorgaenge. Fuer jemanden, der brainlehr zum ersten Mal benutzt, ist
# aber gerade das Nachschlagen die sichtbare Leistung: zu sehen, WELCHER
# Knoten die Antwort getragen hat, statt einem Modell glauben zu muessen.
LESE_AKTIONEN = {"search", "read", "browse", "lesson_query"}

LESEWORT = {
    "search": "nachgeschlagen", "lesson_query": "nachgeschlagen",
    "read": "gelesen", "browse": "durchgesehen",
}

TYPWORT = {
    "add": "Knoten", "update": "Knoten-Aenderung",
    "lesson": "Lehre", "lesson_update": "Lehre-Aenderung", "lesson_delete": "Lehre-Loeschung",
    "annahme": "Annahme",
    "relation_add": "Kante", "relation_update": "Kante-Aenderung", "relation_remove": "Kante-Loeschung",
    "freigeben": "Freigabe", "zurueckziehen": "Ruecknahme",
}

STAND_DIR = ort.WURZEL / "sichtbarkeit_stand"


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _kennung(conn: sqlite3.Connection, row: sqlite3.Row) -> str | None:
    """Die Kennung fuer eine ERFOLGREICHE Zeile -- oder None, wenn die
    Aktion keine ist (annahme-Liste)."""
    action = row["action"]
    query = row["query"] or ""

    if action == "annahme" and query.startswith("liste:"):
        return None  # Lesezugriff unter demselben Aktionsnamen

    if action == "annahme" and " -> " not in query:
        # frisch angelegt: query ist der Annahmetext, nicht die ID.
        treffer = conn.execute(
            "SELECT id FROM annahmen WHERE annahme = ? ORDER BY created_at DESC LIMIT 1",
            (query,),
        ).fetchone()
        return treffer["id"] if treffer else (query[:40] + "…" if len(query) > 40 else query)

    if action == "lesson":
        treffer = conn.execute(
            "SELECT id FROM lessons_learned WHERE description = ? ORDER BY last_seen DESC LIMIT 1",
            (query,),
        ).fetchone()
        return treffer["id"] if treffer else (query[:40] + "…" if len(query) > 40 else query)

    # lesson_update/lesson_delete/relation_*/annahme_entscheiden: query
    # traegt die ID bereits (lesson_id/relation_id/'annahme_id -> status').
    if action in ("lesson_update", "lesson_delete", "relation_add", "relation_update",
                  "relation_remove") and query:
        return query

    if action == "annahme" and query:
        return query

    return row["node_path"] or query or "?"


def neue_einspielungen(session: str, ab_zeile: int) -> tuple[list[str], int]:
    """Was der Abruf-Haken in DIESE Sitzung eingespielt hat.

    Zweite Quelle neben access_log, und ohne sie fehlt die Haelfte: der
    Abruf-Haken (knowledge_recall_hook.py) protokolliert NICHT ins
    access_log, sondern nach recall_log.jsonl. Deshalb kannte der Melder
    zwar jeden Schreibvorgang, aber keine einzige Einspielung -- also genau
    das, was den Nutzer am meisten angeht: welche Lehre gerade seine Frage
    beantwortet hat.

    Gezaehlt wird in ZEILEN, nicht in Bytes: eine angehaengte Zeile
    verschiebt keine frueheren, und eine halb geschriebene Zeile faellt beim
    JSON-Lesen einfach durch, statt den Zaehler zu verschieben.
    """
    log = ort.WURZEL / "recall_log.jsonl"
    if not log.exists():
        return [], ab_zeile
    kennungen: list[str] = []
    nr = 0
    for nr, roh in enumerate(log.read_text(encoding="utf-8").splitlines(), 1):
        if nr <= ab_zeile or not roh.strip():
            continue
        try:
            satz = json.loads(roh)
        except json.JSONDecodeError:
            continue
        if session and satz.get("session") and satz["session"] != session:
            continue
        kennungen.extend(satz.get("lessons") or [])
    if not kennungen:
        return [], max(nr, ab_zeile)
    ohne_doppel = list(dict.fromkeys(kennungen))
    if len(ohne_doppel) > 4:
        text = ", ".join(ohne_doppel[:4]) + f" und {len(ohne_doppel) - 4} weitere"
    else:
        text = ", ".join(ohne_doppel)
    return [f"eingespielt: {text}"], max(nr, ab_zeile)


def _knotenname(conn: sqlite3.Connection, pfad: str) -> str:
    """Der NAME eines Knotens, nicht sein Pfad (Betreiber-Vorgabe 2026-08-10:
    "mir wuerde eigentlich reichen wenn der knotennamen angezeigt wird").

    Der letzte Pfadteil, nicht der Titel aus dem Bestand. Der Titel war der
    erste Versuch und machte die Zeile LAENGER statt kuerzer -- drei Titel
    fuellen zwei Zeilen, und die Aufgabe war Verknappung. Die Elternkette
    davor traegt fuer den Leser ohnehin nichts bei.
    """
    return pfad.rstrip("/").rsplit("/", 1)[-1] or pfad


def neue_zeilen(conn: sqlite3.Connection, ab_id: int) -> tuple[list[str], int]:
    """Meldezeilen fuer jeden Schreibvorgang mit id > ab_id.

    'started'-Zeilen werden uebersprungen: sie sind kein Ergebnis, nur der
    Beginn eines Vorgangs, dessen Endzeile (completed/rejected/failed)
    gesondert kommt (oder, bei einem Absturz mittendrin, gar nicht -- das
    ist eine eigene, noch offene Fehlklasse, siehe S11 im Plan)."""
    rows = conn.execute(
        "SELECT id, action, node_path, query, status FROM access_log "
        "WHERE id > ? ORDER BY id",
        (ab_id,),
    ).fetchall()
    zeilen: list[str] = []
    letzte_id = ab_id
    gelesen: dict[str, set[str]] = {}
    for r in rows:
        letzte_id = max(letzte_id, r["id"])
        if r["status"] == "started":
            continue
        if r["action"] in LESE_AKTIONEN:
            # Nach Wortwahl gebuendelt und ohne Doppelte: eine Suche schreibt
            # eine Zeile JE TREFFER, und zwanzig Zeilen liest niemand.
            if r["status"] == "completed" and r["node_path"]:
                gelesen.setdefault(LESEWORT[r["action"]], set()).add(r["node_path"])
            continue
        if r["action"] not in SCHREIB_AKTIONEN:
            continue
        typwort = TYPWORT.get(r["action"], r["action"])
        if r["status"] == "completed":
            kennung = _kennung(conn, r)
            if kennung is None:
                continue
            zeilen.append(f"abgelegt: {kennung} ({typwort})")
        elif r["status"] == "rejected":
            zeilen.append(f"abgewiesen: {r['query'] or 'kein Grund protokolliert'} ({typwort})")
        elif r["status"] == "failed":
            zeilen.append(f"fehlgeschlagen: {r['query'] or 'kein Grund protokolliert'} ({typwort})")

    # Lesen VOR das Schreiben: es ist die haeufigere Haelfte und beantwortet
    # die Frage, die ein Nutzer beim Lesen einer Antwort wirklich hat --
    # worauf stuetzt sich das. Geschrieben wird seltener und faellt dadurch
    # auch am Ende der Liste noch auf.
    lesezeilen: list[str] = []
    for wort in ("nachgeschlagen", "gelesen", "durchgesehen"):
        pfade = sorted(gelesen.get(wort, ()))
        if not pfade:
            continue
        namen = [_knotenname(conn, p) for p in pfade]
        if len(namen) <= 3:
            lesezeilen.append(f"{wort}: {', '.join(namen)}")
        else:
            lesezeilen.append(
                f"{wort}: {', '.join(namen[:3])} und {len(namen) - 3} weitere")
    return lesezeilen + zeilen, letzte_id


def _gedeckelt(zeilen: list[str], deckel: int = 5) -> list[str]:
    """Hoechstens `deckel` Zeilen, Rest als Zahl -- wer zwanzig Zeilen
    ausgibt, wird ueberlesen (Planschritt S2, Vorgabe 4)."""
    if len(zeilen) <= deckel:
        return zeilen
    rest = len(zeilen) - deckel
    return zeilen[:deckel] + [f"... und {rest} weitere"]


def _marke_pfad(session: str) -> Path:
    sid = "".join(c for c in (session or "unbekannt") if c.isalnum() or c in "-_")[:40]
    return STAND_DIR / f"{sid}.txt"


def _hook_lauf(session: str) -> None:
    marke = _marke_pfad(session)
    try:
        ab_id = int(marke.read_text(encoding="utf-8").strip()) if marke.exists() else _letzte_id_beim_start()
    except Exception:
        ab_id = _letzte_id_beim_start()

    conn = _verbindung()
    zeilen, letzte_id = neue_zeilen(conn, ab_id)
    conn.close()

    # Einspielungen ganz nach vorn: sie stehen VOR der Antwort, die der
    # Nutzer gerade liest, und erklaeren sie.
    rmarke = STAND_DIR / f"{_marke_pfad(session).stem}.recall"
    try:
        ab_zeile = int(rmarke.read_text(encoding="utf-8").strip())
    except Exception:
        ab_zeile = 0
    ezeilen, letzte_zeile = neue_einspielungen(session, ab_zeile)
    zeilen = ezeilen + zeilen

    STAND_DIR.mkdir(exist_ok=True)
    marke.write_text(str(letzte_id), encoding="utf-8")
    rmarke.write_text(str(letzte_zeile), encoding="utf-8")

    if zeilen:
        # Als JSON-Feld systemMessage, NICHT als blosser Text. Ein
        # PostToolUse-Haken schreibt sein stdout ins Protokoll, wo es der
        # Nutzer nur im ausfuehrlichen Modus zu sehen bekommt -- deshalb hat
        # dieser Melder monatelang gearbeitet und 1715 Vorgaenge abgelegt,
        # ohne dass eine einzige Zeile im Gespraech ankam. Er war nie kaputt,
        # er hat mit sich selbst geredet.
        print(json.dumps({"systemMessage": "\n".join(_gedeckelt(zeilen))}))


def _letzte_id_beim_start() -> int:
    """Nur noch der NOTNAGEL, wenn --init nie lief (z.B. eine Sitzung, die
    vor diesem Melder begann). Baselinet auf die aktuelle Endmarke -- das
    schluckt den allerersten Schreibvorgang DIESES PostToolUse-Aufrufs,
    weil der schon im Protokoll steht, wenn der Haken ueberhaupt feuert
    (gleicher Fehler wie die Gesamtzahl-Falle in L-502be0: Zustand vs.
    Durchsatz). Der Regelfall geht daher ueber init_falls_neu() am
    Sitzungsstart, VOR dem ersten Werkzeugaufruf."""
    try:
        conn = _verbindung()
        r = conn.execute("SELECT MAX(id) m FROM access_log").fetchone()
        conn.close()
        return r["m"] or 0
    except Exception:
        return 0


def init_falls_neu(session: str) -> None:
    """SessionStart-Haken: setzt die Marke dieser Sitzung auf den Stand VOR
    dem ersten Werkzeugaufruf. Nur wenn noch keine Marke existiert -- eine
    fortgesetzte/wiederaufgenommene Sitzung darf nicht zurueckspringen und
    alte Schreibzeilen nochmal zeigen."""
    marke = _marke_pfad(session)
    if marke.exists():
        return
    STAND_DIR.mkdir(exist_ok=True)
    marke.write_text(str(_letzte_id_beim_start()), encoding="utf-8")


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE access_log (id INTEGER PRIMARY KEY, action TEXT,
                    node_path TEXT, query TEXT, status TEXT)""")
    conn.execute("""CREATE TABLE lessons_learned (id TEXT, description TEXT, last_seen TEXT)""")
    conn.execute("""CREATE TABLE annahmen (id TEXT, annahme TEXT, created_at TEXT)""")

    def zeile(id_, action, node_path, query, status):
        conn.execute("INSERT INTO access_log VALUES (?,?,?,?,?)", (id_, action, node_path, query, status))

    # Lesen WIRD gemeldet -- Betreiber-Vorgabe 2026-08-10: "wir wollten im
    # chat anzeigen lassen was du aus brainlehr liest und was du dort
    # reinschreibst, das ist das beeindruckende fuer neue user". Bis dahin
    # stand hier der umgekehrte Satz, Lesen erzeugte bewusst keine Zeile.
    # Die alte Sorge bleibt berechtigt und ist jetzt anders geloest: nicht
    # durch Schweigen, sondern durch Buendeln (eine Zeile je Wortwahl,
    # hoechstens drei Pfade, Rest als Zahl).
    zeile(1, "browse", "/x", None, "completed")
    zeile(2, "search", None, "frage", "completed")
    zeile(3, "relation_list", "/x", None, "completed")
    zeile(4, "annahme", None, "liste:offen", "completed")
    z, letzte = neue_zeilen(conn, 0)
    assert z == ["durchgesehen: x"], f"Lesen muss gemeldet werden, bekam: {z}"
    # Ohne Knotenpfad keine Zeile: eine Suche ohne Treffer hat nichts zu
    # zeigen, und "nachgeschlagen: nichts" ist Laerm.
    assert not any("nachgeschlagen" in x for x in z), \
        "Suche ohne Treffer darf keine Zeile erzeugen"
    assert letzte == 4, "letzte_id muss trotzdem mitwachsen, sonst haengt die Marke"

    # 'started' allein (Absturz zwischen started und completed) -- keine Zeile.
    zeile(5, "add", "/neu", None, "started")
    z, letzte = neue_zeilen(conn, 4)
    assert z == [], "eine blosse started-Zeile ist kein Ergebnis"
    assert letzte == 5

    # Abgewiesen: der kurze Grund erscheint, nicht der volle Fehlertext.
    zeile(6, "add", "/neu", "source_fehlt", "rejected")
    z, letzte = neue_zeilen(conn, 5)
    assert z == ["abgewiesen: source_fehlt (Knoten)"], z

    # Angelegt: node_path traegt die Kennung direkt.
    zeile(7, "add", "/neu", None, "completed")
    z, letzte = neue_zeilen(conn, 6)
    assert z == ["abgelegt: /neu (Knoten)"], z

    # Lehre neu: query ist der Volltext, die ID kommt aus dem Join.
    conn.execute("INSERT INTO lessons_learned VALUES ('L-a1b2c3', 'ein Testfehler', '2026-08-09')")
    zeile(8, "lesson", None, "ein Testfehler", "completed")
    z, letzte = neue_zeilen(conn, 7)
    assert z == ["abgelegt: L-a1b2c3 (Lehre)"], z

    # Lehre neu, aber KEIN Treffer im Join -- faellt auf den Text zurueck,
    # erfindet keine ID.
    zeile(9, "lesson", None, "unbekannter Text", "completed")
    z, letzte = neue_zeilen(conn, 8)
    assert z == ["abgelegt: unbekannter Text (Lehre)"], z

    # Annahme neu: gleicher Mechanismus.
    conn.execute("INSERT INTO annahmen VALUES ('A-d93330', 'wir nehmen an X', '2026-08-09')")
    zeile(10, "annahme", None, "wir nehmen an X", "completed")
    z, letzte = neue_zeilen(conn, 9)
    assert z == ["abgelegt: A-d93330 (Annahme)"], z

    # Annahme entschieden: query traegt die ID schon ('id -> status').
    zeile(11, "annahme", None, "A-d93330 -> bestaetigt", "completed")
    z, letzte = neue_zeilen(conn, 10)
    assert z == ["abgelegt: A-d93330 -> bestaetigt (Annahme)"], z

    # relation_add: query ist die relation_id, direkt lesbar.
    zeile(12, "relation_add", "/quelle", "R-7", "completed")
    z, letzte = neue_zeilen(conn, 11)
    assert z == ["abgelegt: R-7 (Kante)"], z

    # Grenzwert: ab_id == letzte_id -> keine neuen Zeilen.
    z, letzte = neue_zeilen(conn, 12)
    assert z == [] and letzte == 12, "an der Grenze darf nichts doppelt erscheinen"

    # Deckel: bei 7 Vorgaengen erscheinen 5 plus die Restzahl.
    for i in range(13, 20):
        zeile(i, "add", f"/n{i}", None, "completed")
    z, letzte = neue_zeilen(conn, 12)
    assert len(z) == 7, z
    gedeckelt = _gedeckelt(z)
    assert len(gedeckelt) == 6, gedeckelt
    assert gedeckelt[-1] == "... und 2 weitere", gedeckelt
    assert _gedeckelt(["a"]) == ["a"], "unter dem Deckel bleibt unveraendert"

    # init_falls_neu: setzt die Marke einmalig auf den Stand VOR dem ersten
    # Schreibvorgang -- und ruehrt eine bestehende Marke NICHT an, sonst
    # wuerde eine fortgesetzte Sitzung alte Zeilen nochmal zeigen.
    import tempfile
    global STAND_DIR, _verbindung
    alte_verbindung, alter_stand = _verbindung, STAND_DIR
    with tempfile.TemporaryDirectory() as tmp:
        STAND_DIR = Path(tmp)
        _verbindung = lambda db=None: conn  # noqa: E731 -- selbe In-Memory-DB wie oben
        init_falls_neu("probe")
        marke = _marke_pfad("probe")
        assert marke.exists() and marke.read_text() == "19", marke.read_text()
        marke.write_text("3", encoding="utf-8")  # simuliert eine bereits laufende Sitzung
        init_falls_neu("probe")
        assert marke.read_text() == "3", "eine bestehende Marke darf init nicht ueberschreiben"
    STAND_DIR, _verbindung = alter_stand, alte_verbindung

    print("selftest ok (12 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--seit", type=int, default=None, help="alle Schreibzeilen mit id > SEIT")
    p.add_argument("--hook", action="store_true",
                   help="PostToolUse-Modus: liest/schreibt die Marke dieser Sitzung selbst")
    p.add_argument("--init", action="store_true",
                   help="SessionStart-Modus: setzt die Marke VOR dem ersten Werkzeugaufruf")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.init:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        init_falls_neu(payload.get("session_id") or "unbekannt")
        return

    if a.hook:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        _hook_lauf(payload.get("session_id") or "unbekannt")
        return

    conn = _verbindung(a.db)
    ab = a.seit if a.seit is not None else 0
    zeilen, _ = neue_zeilen(conn, ab)
    conn.close()
    if zeilen:
        print("\n".join(_gedeckelt(zeilen)))
    else:
        print("Sichtbarkeit: keine Schreibzeilen seit --seit.")


if __name__ == "__main__":
    main()
