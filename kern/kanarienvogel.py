#!/usr/bin/env python3
"""kanarienvogel.py -- Aufgabe 63 (docs/PLAN_PARALLEL_2026-08-13.md): Sonde,
die denselben Weg wie eine echte Abruf-Anfrage geht (RO-Zugang ueber die
Naht kern/speicher.py::lesen() -- dieselbe Tuer, durch die Produktivcode
inzwischen gehen soll, statt einer selbst geoeffneten Verbindung -- und
dieselbe embed_text()-Funktion wie haken/knowledge_recall_hook.py::query())
und meldet, ob Datenbank und Einbettung UEBERHAUPT geantwortet haben. Der
Grund, warum das mehr als Regeltreue ist: Eine eigene Verbindung wuerde
einen Weg pruefen, den im Betrieb niemand geht -- die Sonde soll belegen,
dass der ECHTE Weg zur Datenbank traegt, und der echte Weg fuehrt seit
speicher.py durch diese Naht. Eine Sonde, die daran vorbeigreift, meldet
im schlimmsten Fall "gesund", waehrend die Naht selbst kaputt ist. Damit
zerfaellt B in melder/vier_nenner.py
(Aufgabe 62) in 'ehrlich leer' (beide haben geantwortet, nur nichts
Passendes gefunden) und 'stumm ausgefallen' (einer der beiden Wege war tot).

EIGENER AUFRUFER, NICHT VERDRAHTET (Nachtrag des Auftraggebers waehrend
dieser Arbeit): parallel laeuft eine Nullmessung (Okkultation) des
Abrufwegs -- eine Aenderung an haken/knowledge_recall_hook.py waere darin
nicht mehr von einer echten Verschiebung zu unterscheiden (Lehre L-7318ce).
Diese Sonde importiert deshalb nur dieselben PRIMITIVEN (speicher.lesen,
embeddings.embed_text), haengt sich aber an KEINER Stelle in query()/main()
ein. Vorbereitet fuer eine spaetere Verdrahtung: EIN try/except-umwickelter
Aufruf von pruefen_und_melden() direkt nach dem Erfolg von
'nodes, lessons = query(...)' in main() (haken/knowledge_recall_hook.py),
noch vor der 'leer'-Verzweigung, damit er sowohl den leeren als auch den
Treffer-Zweig erreicht -- das ist der einzige Ort, an dem 'bei jedem Abruf'
im Wortsinn stimmt. Diese eine Zeile zu setzen ist ein eigener, spaeterer
Schritt (siehe Bericht an den Auftraggeber), kein Teil dieses Auftrags.

KEINE VERUNREINIGUNG: kein Schreibzugriff auf knowledge_nodes/
lessons_learned, keine FTS-Abfrage, keine Zeile in recall_log.jsonl oder
sonst einem Trefferprotokoll -- ein 'SELECT 1 ... LIMIT 1' und ein
embed_text()-Aufruf mit festem, bedeutungslosem Sondentext beruehren keine
Trefferliste und zaehlen in keiner Abrufzahl mit. Der Bestand kennt
gattung='nachschlagewerk' fuer 'darf im Heuhaufen liegen, ist nie Ziel
eines Pruefstands' -- hier reicht die staerkere Form 'gar nichts
schreiben, keine Suchfunktion aufrufen', weil die Sonde keinen Knoten
braucht, nur die Verbindung selbst.

MELDUNG: nur bei Ausfall wird eine Zeile in kanarienvogel_alarm.jsonl
angehaengt (WURZEL, Append-only wie recall_log.jsonl) -- bei Erfolg bleibt
die Sonde still (Auftrag Punkt 3: eine 'alles gut'-Zeile bei jedem Aufruf
wird nach drei Tagen ueberlesen)."""
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

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = _w
if str(WURZEL / "haken") not in sys.path:
    sys.path.insert(0, str(WURZEL / "haken"))
import embeddings  # noqa: E402 -- dieselbe Funktion wie query() (embeddings.embed_text)
import speicher  # noqa: E402 -- die Naht (kern/speicher.py): lesen() statt eigener Verbindung

ALARM_LOG = WURZEL / "kanarienvogel_alarm.jsonl"
SONDENTEXT = "kanarienvogel sondentext ohne inhaltliche bedeutung"


def pruefen(db_path: str | Path | None = None, embed_fn=None) -> dict:
    """Geht denselben Weg wie Produktivcode ueber die Naht (kern/speicher.py
    ::lesen()) zur DB, embed_text() fuer die Einbettung. Beide injizierbar
    (Walkthrough-Doktrin) -- die Rot-Probe speist einen kaputten Pfad bzw.
    eine fehlschlagende Einbettungsfunktion ein, ohne den echten Betrieb zu
    beruehren."""
    embed_fn = embed_fn or embeddings.embed_text
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db_ok, embedding_ok = True, True
    fehler: list[str] = []
    try:
        with speicher.lesen(db_path) as conn:
            conn.execute("SELECT 1 FROM knowledge_nodes LIMIT 1").fetchone()
    except Exception as e:  # noqa: BLE001 -- jeder Fehler ist ein Ausfall, keiner darf durchrutschen
        db_ok = False
        fehler.append(f"datenbank: {e}")
    try:
        vektor = embed_fn(SONDENTEXT)
        if not vektor:
            embedding_ok = False
            fehler.append("einbettung: embed_text lieferte nichts (None/leer)")
    except Exception as e:  # noqa: BLE001
        embedding_ok = False
        fehler.append(f"einbettung: {e}")
    return {"ts": ts, "db_ok": db_ok, "embedding_ok": embedding_ok, "fehler": fehler}


def _melde_alarm(befund: dict, alarm_log: Path | None = None) -> None:
    """Schreibt NUR bei Ausfall eine Zeile ins Protokoll -- nie in den Chat
    (Auftrag Punkt 3). Beiwerk, darf nie werfen (gleiche Regel wie
    log_recall() in haken/knowledge_recall_hook.py)."""
    if befund["db_ok"] and befund["embedding_ok"]:
        return
    ziel = alarm_log if alarm_log is not None else ALARM_LOG
    try:
        with open(ziel, "a", encoding="utf-8") as f:
            f.write(json.dumps(befund, ensure_ascii=False) + "\n")
    except OSError:
        pass


def pruefen_und_melden(db_path: str | Path | None = None, embed_fn=None,
                        alarm_log: Path | None = None) -> dict:
    befund = pruefen(db_path=db_path, embed_fn=embed_fn)
    _melde_alarm(befund, alarm_log=alarm_log)
    return befund


def _selftest() -> None:
    import tempfile

    # Deterministischer gruener Fall -- injizierte Einbettungsfunktion, kein
    # echter Ollama-Netzwerkaufruf im Test (Walkthrough-Doktrin: mockbare
    # Aussenwelt).
    gruen = lambda _t: [0.1, 0.2, 0.3]  # noqa: E731
    befund = pruefen(embed_fn=gruen)
    assert befund["db_ok"] is True and befund["embedding_ok"] is True, befund
    assert befund["fehler"] == []

    with tempfile.TemporaryDirectory() as tmp:
        alarm_pfad = Path(tmp) / "alarm.jsonl"

        # ROT-PROBE 1 (Auftrag, unverzichtbar): Datenbankpfad unbrauchbar --
        # eine Wegwerfkopie ohne Datei an dem Pfad, kein echter Datenbestand
        # beruehrt.
        kaputt = str(Path(tmp) / "nicht-vorhanden.db")
        b = pruefen_und_melden(db_path=kaputt, embed_fn=gruen, alarm_log=alarm_pfad)
        assert b["db_ok"] is False, b
        assert b["embedding_ok"] is True, b  # Kanaele unabhaengig -- Einbettung bleibt unberuehrt
        zeilen = alarm_pfad.read_text(encoding="utf-8").splitlines()
        assert len(zeilen) == 1, zeilen
        assert json.loads(zeilen[0])["db_ok"] is False

        # Gruener Aufruf danach bleibt STILL -- keine zweite Zeile.
        pruefen_und_melden(embed_fn=gruen, alarm_log=alarm_pfad)
        assert len(alarm_pfad.read_text(encoding="utf-8").splitlines()) == 1

        # ROT-PROBE 2: Einbettungskanal liefert nichts (Ollama unerreichbar/
        # kein Modell -- embed_text() ist per Vertrag best-effort und liefert
        # dann None, kein Wurf).
        b2 = pruefen_und_melden(embed_fn=lambda _t: None, alarm_log=alarm_pfad)
        assert b2["db_ok"] is True and b2["embedding_ok"] is False, b2
        zeilen2 = alarm_pfad.read_text(encoding="utf-8").splitlines()
        assert len(zeilen2) == 2, zeilen2
        assert json.loads(zeilen2[-1])["embedding_ok"] is False

        # ROT-PROBE 3: Einbettungsfunktion wirft statt still zu scheitern --
        # auch das ist ein Ausfall, kein durchrutschender Fehler.
        def _wirft(_t):
            raise RuntimeError("ollama nicht erreichbar")
        b3 = pruefen(embed_fn=_wirft)
        assert b3["embedding_ok"] is False, b3
        assert "ollama nicht erreichbar" in b3["fehler"][0]

    print("SELFTEST OK: kanarienvogel")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        import pprint
        pprint.pprint(pruefen())
