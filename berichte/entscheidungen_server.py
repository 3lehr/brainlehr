#!/usr/bin/env python3
"""entscheidungen_server.py -- lokale Entscheidungsoberflaeche fuer acht
liegen gebliebene Betreiber-Entscheidungen (Auftrag 2026-08-07).

Stdlib-Server (http.server), lauscht NUR auf 127.0.0.1. Serviert
entscheidungen.html und eine kleine JSON-API. Schreibende Aufrufe gehen,
wo ein Skript existiert, ueber genau dieses Skript (Unterprozess bzw.
Funktionsimport) -- kein eigenes SQL fuer Lehren-Eskalation oder
Eilmeldungen. Fuer Siegbedingung/Nachtschicht existiert kein Wrapper-Skript
(nur Lese-Helfer in meisterschaft.py/nachtlaeufer.py) -- dort schreibt
dieser Server direkt in knowledge_config, im selben Muster wie
meisterschaft.titelverteidiger_festhalten() es vormacht.

Jede vorhandene Python-Datei im Verzeichnis wird nur gelesen oder als
Unterprozess/Import aufgerufen, keine einzige veraendert (Grenze des
Auftrags -- mehrere liegen bei anderen Agenten).

Laeuft der Server nicht, aendert sich nichts am Betrieb: reines Zubehoer,
keine Voraussetzung fuer die uebrigen Werkzeuge.

Aufruf:
    python3 entscheidungen_server.py [--port 8799]
    python3 entscheidungen_server.py --selftest
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

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import datetime
import glob
import html
import json
import re
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent  # eine Ebene tiefer seit dem Umzug 2026-08-10
HUB = HERE.parent
DB_PATH = HERE / "brainlehr.db"
HTML_PATH = HERE / "entscheidungen.html"
# Simulator-Auftrag 2026-08-12: 89 ECHTE Anfragen (keine erfundenen Beispiele,
# siehe docs/PLAN_SIMULATOR_2026-08-12.md, Alternative A verworfen).
ECHTKORPUS_PATH = HERE / "runs" / "echtkorpus_2026-08-12T1000.json"
ESKALATION_SCRIPT = HERE / "eskalation_vorlage.py"
EILMELDUNG_SCRIPT = HUB / "scripts" / "eilmeldung_quittieren.py"
AUSWEIS_START_SCRIPT = HERE / "pflege" / "ausweis_start.sh"

sys.path.insert(0, str(HERE))
import eskalation_vorlage  # noqa: E402  -- nur Funktionen aufgerufen, Datei unveraendert
import knowledge_lint  # noqa: E402       -- nur find_norm_conflicts() gelesen
import meisterschaft  # noqa: E402        -- nur *_lesen() gelesen/Schluessel-Namen
import nachtlaeufer  # noqa: E402         -- nur _DEFAULTS gelesen
import raum_daten  # noqa: E402           -- nur sammle() aufgerufen, Datei unveraendert
import speicher  # noqa: E402             -- nur verbinde_bestand() fuer _config_set()

# Abschnitt 11 (Abrufweg): nur GELESEN/AUFGERUFEN, keine dieser Dateien wird
# veraendert. embeddings/knowledge_recall_hook gehoeren einem anderen Agenten
# (haken/knowledge_recall_hook.py, kern/embeddings.py) -- hier nur importiert.
import embeddings  # noqa: E402
import gattung_filter  # noqa: E402
import knowledge_recall_hook  # noqa: E402  -- nur MAX_NODES/MAX_LESSONS/MIN_HITS/keywords/_ist_geltend gelesen
from knowledge_mcp_server import _embedding_ranking, _or_query  # noqa: E402

# Schritt 1 der ADR-020-Reihenfolge (Abschnitt 5): die Origin-Pruefung allein
# ersetzt hier eine echte Ausweispruefung. kern/ausweis.py bleibt tabu fuer
# diesen Auftrag -- nur loese_auf()/darf() werden aufgerufen, keine Zeile
# dort veraendert.
import ausweis as ausweis_kern  # noqa: E402

RUNS_DIR = HERE / "runs"
# raum.html/vergleich.html sind aufgegangen in entscheidungen.html (Betreiber-
# Weisung 2026-08-08: eine Adresse statt drei). /raum und /vergleich bleiben
# als Weiterleitung erreichbar, falls ein Reiter noch die alte Adresse offen hat.

SIEGGROESSEN = meisterschaft.SIEGGROESSEN  # ("trefferquote","schweigequote","streuung","kosten")
GEWICHT_PREFIX = "siegbedingung_gewicht_"
GEWICHT_GERATEN_KEY = "siegbedingung_gewichte_geraten"


# ─── Abschnitt 1: Eskalierte Lehren ─────────────────────────────────────────
#
# Beanstandung 2026-08-07: die alte Beforderung schrieb den rohen, bei
# RULE_CAP=220 Zeichen HART abgeschnittenen Praeventionstext einer Lehre in
# hub/CLAUDE.md -- eine Lehre (fuer Leser mit Fallkenntnis) ist keine Regel
# (verstaendlich ohne Vorwissen).
#
# Korrektur des Auftraggebers noch waehrend der Umsetzung: der Regeltext wird
# NICHT beim Klick und NICHT von dieser Oberflaeche erzeugt (kein Modellaufruf
# hier, kein Warten). Er entsteht FRUEHER, sobald eine Lehre Kandidat wird --
# durch einen eigenen Erzeuger (Nachtlaeufer o.ae.), der ausserhalb dieser
# beiden Dateien liegt und hier NICHT gebaut wird. Diese Datei liest nur.
#
# ERWARTETES FELD FUER DEN ERZEUGER: Tabelle `eskalation_vorschlag` in
# derselben brainlehr.db, Spalten (lesson_id TEXT PRIMARY KEY, regel_vorschlag
# TEXT NOT NULL, erzeugt_am TEXT NOT NULL). Ein Upsert pro Lehre, sobald sie
# nach status='escalated_to_rule' wechselt. Ohne Zeile dort zeigt die
# Oberflaeche ehrlich "Regeltext wird noch erstellt" und bietet dort keine
# Befoerderung an -- besser nichts anzeigen als wieder einen Textausschnitt
# befoerdern.
#
# Rueckstufungs-Merkmal (Ebene 2 derselben Beanstandung): "seit wann steht
# die Regel oben" und "ist sie seither wieder aufgetreten" sind nur ab dem
# Zeitpunkt feststellbar, an dem eine Beforderung diese Zahl selbst
# festhaelt -- Zeit allein zaehlt laut Betreiber-Direktive nicht.
# eskalation_historie(lesson_id, promoted_at, occurrences_at_promotion,
# demoted_at) haelt das fest. Fuer die zwei bereits VOR dieser Anzeige
# befoerderten Lehren (L-40d9a5, L-48e414) gibt es keinen Nachtrag -- ehrlich
# als "unbekannt" ausgewiesen statt rueckwirkend geraten.

def _ensure_eskalation_tabellen(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS eskalation_historie "
        "(lesson_id TEXT PRIMARY KEY, promoted_at TEXT NOT NULL, "
        "occurrences_at_promotion INTEGER NOT NULL, demoted_at TEXT)"
    )
    # Bestandsschutz: Tabelle kann noch aus einer Vorversion ohne demoted_at stammen.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eskalation_historie)")}
    if "demoted_at" not in cols:
        conn.execute("ALTER TABLE eskalation_historie ADD COLUMN demoted_at TEXT")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS eskalation_vorschlag "
        "(lesson_id TEXT PRIMARY KEY, regel_vorschlag TEXT NOT NULL, erzeugt_am TEXT NOT NULL)"
    )


def _eskalation_stand() -> dict:
    conn = eskalation_vorlage.get_db()
    _ensure_eskalation_tabellen(conn)
    conn.commit()
    pool_rows = conn.execute(
        "SELECT l.id, l.occurrences, l.type, l.description, "
        "h.promoted_at, h.demoted_at, v.regel_vorschlag "
        "FROM lessons_learned l "
        "LEFT JOIN eskalation_historie h ON h.lesson_id = l.id "
        "LEFT JOIN eskalation_vorschlag v ON v.lesson_id = l.id "
        "WHERE l.status = ? ORDER BY l.occurrences DESC, l.id",
        (eskalation_vorlage.STATUS_POOL,),
    ).fetchall()
    promoted_rows = conn.execute(
        "SELECT l.id, l.occurrences, l.description, h.promoted_at, h.occurrences_at_promotion "
        "FROM lessons_learned l LEFT JOIN eskalation_historie h ON h.lesson_id = l.id "
        "WHERE l.status = ? ORDER BY l.id",
        (eskalation_vorlage.STATUS_PROMOTED,),
    ).fetchall()
    conn.close()

    def _kandidat(r):
        return {
            "id": r["id"], "occurrences": r["occurrences"], "type": r["type"],
            "description": r["description"],
            "regel_vorschlag": r["regel_vorschlag"],  # None = Erzeuger war noch nicht dran
        }

    # War schon mal oben (demoted_at gesetzt) -> eigene Gruppe, taucht nicht
    # kommentarlos wieder unter den nie befoerderten Kandidaten auf.
    kandidaten = [_kandidat(r) for r in pool_rows if r["demoted_at"] is None]
    zurueckgestuft = [dict(_kandidat(r), war_oben_von=r["promoted_at"], zurueckgestuft_am=r["demoted_at"])
                       for r in pool_rows if r["demoted_at"] is not None]

    erhoehung = sum(len(k["regel_vorschlag"]) for k in kandidaten if k["regel_vorschlag"])
    aktuell = len(eskalation_vorlage.CLAUDE_MD_PATH.read_text(encoding="utf-8")) if \
        eskalation_vorlage.CLAUDE_MD_PATH.exists() else 0
    prozent = round(100 * erhoehung / aktuell, 1) if aktuell else None

    befoerdert = []
    for r in promoted_rows:
        if r["promoted_at"] is None:
            seit, signal = None, "unbekannt — vor Einfuehrung dieser Anzeige befoerdert, keine Vergleichsgrundlage."
        else:
            seit = r["promoted_at"]
            diff = r["occurrences"] - r["occurrences_at_promotion"]
            signal = ("seit Befoerderung nicht erneut aufgetreten — Ruecknahme pruefbar" if diff <= 0
                       else f"seit Befoerderung {diff}× erneut aufgetreten — bleibt oben")
        befoerdert.append({"id": r["id"], "description": r["description"], "seit": seit, "signal": signal})

    return {"kandidaten": kandidaten, "befoerdert": befoerdert, "zurueckgestuft": zurueckgestuft,
            "erhoehung_zeichen": erhoehung,
            "claude_md_zeichen": aktuell, "erhoehung_prozent": prozent}


def _eskalation_befoerdern(lesson_id: str, regel: str) -> dict:
    regel = (regel or "").strip()
    if not regel:
        return {"ok": False, "error": "Regeltext fehlt"}
    conn = eskalation_vorlage.get_db()
    _ensure_eskalation_tabellen(conn)
    row = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE id = ? AND status = ?",
        (lesson_id, eskalation_vorlage.STATUS_POOL),
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "nicht in der Vorlage"}
    text = eskalation_vorlage._read_claude_md(eskalation_vorlage.CLAUDE_MD_PATH)
    new_text = eskalation_vorlage._promote_line(text, lesson_id, regel)
    eskalation_vorlage.CLAUDE_MD_PATH.write_text(new_text, encoding="utf-8")
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute("UPDATE lessons_learned SET status = ? WHERE id = ?",
                 (eskalation_vorlage.STATUS_PROMOTED, lesson_id))
    conn.execute(
        "INSERT INTO eskalation_historie (lesson_id, promoted_at, occurrences_at_promotion) "
        "VALUES (?, ?, ?) ON CONFLICT(lesson_id) DO UPDATE SET "
        "promoted_at=excluded.promoted_at, occurrences_at_promotion=excluded.occurrences_at_promotion",
        (lesson_id, ts, row["occurrences"]),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


def _eskalation_handeln(handlung: str, lesson_id: str, regel: str = "") -> dict:
    if handlung == "befoerdern":
        return _eskalation_befoerdern(lesson_id, regel)
    if handlung == "zurueckstufen":
        ns = SimpleNamespace(lesson_id=lesson_id)
        ok = eskalation_vorlage.cmd_zurueckstufen(ns)
        if ok:
            # Historie bleibt stehen (demoted_at gesetzt) -- sonst verschwindet die
            # Zurueckstufung spurlos und die Lehre sieht wie ein nie befoerderter
            # Kandidat aus. Nur legt eine bereits VOR dieser Anzeige (ohne
            # promoted_at) befoerderte Lehre keine Zeile an -- fuer sie gibt es
            # nichts zu vervollstaendigen.
            conn = eskalation_vorlage.get_db()
            _ensure_eskalation_tabellen(conn)
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute("UPDATE eskalation_historie SET demoted_at = ? WHERE lesson_id = ?",
                         (ts, lesson_id))
            conn.commit()
            conn.close()
        return {"ok": bool(ok)}
    return {"error": "unbekannte Handlung"}


# ─── Abschnitt 2: Normkonflikte (nur lesend) ────────────────────────────────

def _normkonflikte_stand() -> dict:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return knowledge_lint.find_norm_conflicts(conn)
    finally:
        conn.close()


# ─── Abschnitt 3: Siegbedingung gewichten ───────────────────────────────────

def _config_get(keys: list[str]) -> dict[str, str]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        placeholders = ",".join("?" for _ in keys)
        rows = conn.execute(
            f"SELECT key, value FROM knowledge_config WHERE key IN ({placeholders})", keys
        ).fetchall()
        return dict(rows)
    finally:
        conn.close()


def _config_set(pairs: dict[str, str]) -> None:
    # verbinde_bestand statt sqlite3.connect: dieser Server laeuft dauerhaft
    # und antwortet auch bei falschem DB_PATH mit HTTP 200 -- eine leere,
    # stillschweigend angelegte Datenbank saehe in jeder Uebersicht gesund
    # aus (siehe kern/speicher.py::verbinde_bestand). knowledge_config wird
    # hier nur ERGAENZT, der Bestand muss schon da sein.
    conn = speicher.verbinde_bestand(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS knowledge_config "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for k, v in pairs.items():
        conn.execute(
            "INSERT INTO knowledge_config (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (k, v, ts),
        )
    conn.commit()
    conn.close()


def _siegbedingung_stand() -> dict:
    keys = [f"{GEWICHT_PREFIX}{g}" for g in SIEGGROESSEN] + [GEWICHT_GERATEN_KEY]
    raw = _config_get(keys)
    geraten = GEWICHT_GERATEN_KEY not in raw or raw.get(GEWICHT_GERATEN_KEY) == "1"
    return {
        "gewichte": {g: float(raw.get(f"{GEWICHT_PREFIX}{g}", "1.0")) for g in SIEGGROESSEN},
        "geraten": geraten,
    }


def _siegbedingung_setzen(gewichte: dict) -> dict:
    pairs = {}
    for g in SIEGGROESSEN:
        if g in gewichte:
            pairs[f"{GEWICHT_PREFIX}{g}"] = str(float(gewichte[g]))
    pairs[GEWICHT_GERATEN_KEY] = "0"  # Nutzer hat aktiv gesetzt -> nicht mehr geraten
    _config_set(pairs)
    return _siegbedingung_stand()


# ─── Abschnitt 4: Nachtschicht ───────────────────────────────────────────────

def _nachtschicht_stand() -> dict:
    keys = ["nachtlaeufer_aktiv", "nachtlaeufer_backend", "nachtlaeufer_budget"]
    raw = _config_get(keys)
    out = dict(nachtlaeufer._DEFAULTS)
    out.update(raw)
    return {"aktiv": out["nachtlaeufer_aktiv"], "antrieb": out["nachtlaeufer_backend"],
            "budget_aufrufe": out["nachtlaeufer_budget"]}


def _nachtschicht_setzen(aktiv: str, antrieb: str, budget: str) -> dict:
    if aktiv not in ("ein", "aus"):
        return {"error": "aktiv muss 'ein' oder 'aus' sein"}
    try:
        int(budget)
    except (TypeError, ValueError):
        return {"error": "budget muss eine ganze Zahl (Aufrufe) sein"}
    _config_set({
        "nachtlaeufer_aktiv": aktiv,
        "nachtlaeufer_backend": antrieb or "keiner",
        "nachtlaeufer_budget": str(int(budget)),
    })
    return _nachtschicht_stand()


# ─── Abschnitt 5: Eilmeldungen quittieren ───────────────────────────────────

def _eilmeldungen_stand() -> list[dict]:
    out = []
    for path in glob.glob("/tmp/claude-eilmeldung-*.json"):
        sid = Path(path).stem.replace("claude-eilmeldung-", "")
        try:
            state = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        for key, m in (state.get("messages") or {}).items():
            if not m.get("acked"):
                out.append({"sitzung": sid, "schluessel": key, "text": m.get("text", ""),
                            "art": m.get("art", "")})
    return out


def _eilmeldung_quittieren(sid: str, key: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(EILMELDUNG_SCRIPT), sid, key],
        capture_output=True, text=True, timeout=10,
    )
    return {"ok": result.returncode == 0, "ausgabe": result.stdout.strip()}


# ─── Abschnitt 5b: Ausweis (Auftrag 2026-08-15, Nachtrag zu G6) ─────────────
#
# BEFUND: Seit die App-Sandbox scharf ist (app-sandbox, network.client,
# runs/sandbox_scharf_g6_*.json), startet AusweisDienst.swift kein
# Unterprozess mehr -- Foundation.Process() auf ein Skript ausserhalb des
# Bundles ist unter der Sandbox blockiert, egal wie es aufgerufen wird. Der
# Ausweis-Weg folgt darum demselben Muster wie /api/fundstelle und
# /api/domaene-import: die App BESTELLT bei diesem (unsandboxed, per launchd
# laufenden) Dienst, der Dienst ruft pflege/ausweis_start.sh weiter --
# dasselbe Skript, dieselbe Python-Suche, nur eine Netzhuelle statt eines
# App-Unterprozesses.
#
# GEHEIMNIS-WEITERGABE: bleibt STDIN, nie argv -- wie zuvor beim
# Process()-Aufruf aus der App. Der HTTP-Body traegt es vom Klienten zum
# Dienst (Loopback, 127.0.0.1, dieselbe Origin-Schranke wie jeder andere
# schreibende Endpunkt hier); der Dienst reicht es unveraendert per STDIN an
# das Skript weiter. Es landet nirgends in argv, nirgends in der URL/Query
# (deshalb POST mit JSON-Body, nicht GET mit Parametern) und nirgends in
# einem Log dieses Servers -- log_message() ist fuer den ganzen Handler
# stillgelegt (siehe oben), es gibt hier kein Zugriffsprotokoll, das einen
# Anfrage- oder Antwortkoerper festhaelt.
#
# EIN FRISCH ERZEUGTES GEHEIMNIS (Befehl "anlegen") STEHT TROTZDEM EINMAL IN
# DER ANTWORT -- das ist keine neue Undichtigkeit dieses Endpunkts, sondern
# der Zweck des Befehls: ausweis.anlegen() gibt das Geheimnis GENAU EINMAL
# zurueck (kern/ausweis.py, Docstring), die Oberflaeche legt es in die
# Zwischenablage und zeigt es dem Nutzer zum Sichern -- exakt dieselbe
# Offenlegung, die vorher schon ueber STDOUT/Process() lief. Ein Weg, der
# das GAR NICHT preisgibt, gaebe es nur, wenn ausweis.anlegen() selbst anders
# arbeitete (tabu, kern/ausweis.py). Gemessen: kein Bestandteil dieses
# Servers schreibt den Antwortkoerper in eine Datei oder ein Log.
#
# WER DARF AUFRUFEN: dieselbe Schranke wie jeder andere POST hier
# (_herkunft_ok(), Fund O2) -- kein eigener Mechanismus fuer diesen
# Endpunkt. "liste" bleibt GET und ungeprueft, weil ausweis_helfer.py
# "liste" schon heute ohne Geheimnis beantwortet (kein STDIN gelesen) und
# keine Geheimnisse listet (nur Name/Art/Rollen).

def _ausweis_aufrufen(argumente: list[str], geheimnis: str | None) -> dict:
    """Ruft pflege/ausweis_start.sh -- derselbe Helfer, den vorher
    Foundation.Process() aus der App heraus startete. `geheimnis` immer als
    STDIN-Text uebergeben (auch leer), nie ueber argv."""
    if not AUSWEIS_START_SCRIPT.is_file():
        return {"fehler": "Der Ausweis-Helfer wurde auf diesem Rechner nicht gefunden."}
    try:
        result = subprocess.run(
            [str(AUSWEIS_START_SCRIPT), *argumente],
            input=(geheimnis or ""), capture_output=True, text=True, timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {"fehler": "Der Ausweis-Helfer antwortet gerade nicht. Bitte in Kürze erneut versuchen."}
    except OSError:
        return {"fehler": "Der Ausweis-Helfer konnte nicht gestartet werden."}
    try:
        out = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"fehler": "Der Ausweis-Helfer hat mit einem unerwarteten Fehler abgebrochen."}
    if not isinstance(out, dict) or ("fehler" not in out and result.returncode != 0):
        return {"fehler": "Der Ausweis-Helfer hat mit einem unerwarteten Fehler abgebrochen."}
    return out


def _ausweis_liste() -> dict:
    return _ausweis_aufrufen(["liste"], None)


def _ausweis_anlegen(payload: dict) -> dict:
    name = str(payload.get("name", ""))
    art = str(payload.get("art", "maschine"))
    rollen = str(payload.get("rollen", ""))
    geheimnis = payload.get("geheimnis")
    return _ausweis_aufrufen(["anlegen", name, art, rollen], geheimnis)


def _ausweis_einladen(payload: dict) -> dict:
    name = str(payload.get("name", ""))
    fuer = str(payload.get("fuer", ""))
    rollen = str(payload.get("rollen", ""))
    geheimnis = payload.get("geheimnis")
    return _ausweis_aufrufen(["einladen", name, fuer, rollen], geheimnis)


# ─── Abschnitt 6-8: nur anzeigen ─────────────────────────────────────────────

def _titelverteidiger_stand() -> dict | None:
    return meisterschaft.titelverteidiger_lesen(bereich="abruf", db_path=DB_PATH)


def _gesamtstand() -> dict:
    return {
        "eskalation": _eskalation_stand(),
        "normkonflikte": _normkonflikte_stand(),
        "siegbedingung": _siegbedingung_stand(),
        "nachtschicht": _nachtschicht_stand(),
        "eilmeldungen": _eilmeldungen_stand(),
        "titelverteidiger": _titelverteidiger_stand(),
        "herkunftsmodus": {"gefunden": False},
        "freigabe_fremder_anbieter": {"gefunden": False},
    }


# ─── Abschnitt 9: Wissensraum (Auftrag 2026-08-08) ──────────────────────────
#
# PCA-Lauf ist teuer (~1s bei 2600 Punkten) -- Zwischenspeicher, neu gerechnet
# nur wenn brainlehr.db oder recall_log.jsonl seit dem letzten Lauf eine
# neuere mtime tragen. Kein Hintergrund-Refresh, keine Ablaufzeit: die zwei
# mtimes SIND die Gueltigkeitsbedingung.

_raum_cache: dict = {"ergebnis": None, "db_mtime": None, "log_mtime": None}


def _raum_stand() -> dict:
    db_mtime = raum_daten.DB_PATH.stat().st_mtime
    log_mtime = raum_daten.RECALL_LOG_PATH.stat().st_mtime if raum_daten.RECALL_LOG_PATH.exists() else None
    if (_raum_cache["ergebnis"] is None
            or _raum_cache["db_mtime"] != db_mtime
            or _raum_cache["log_mtime"] != log_mtime):
        _raum_cache["ergebnis"] = raum_daten.sammle()
        _raum_cache["db_mtime"] = db_mtime
        _raum_cache["log_mtime"] = log_mtime
    return _raum_cache["ergebnis"]


# ─── Abschnitt 10: A/B-Vergleich Abruf (Auftrag 2026-08-07) ────────────────
#
# Zeigt keinen Sieger. Die Faelle, in denen A (volle Kette) und B (rohe
# Top-3-Suche) auseinandergehen, kommen einzeln nebeneinander -- angereichert
# um die gelieferte Antwort je Seite aus `rows` (unterschiede_A_B traegt nur
# Pfade/bestanden, nicht die Antwort selbst). Zwischenspeicher wie /api/raum:
# neu gelesen nur wenn Dateiname oder mtime der juengsten Laufdatei wechselt.

_vergleich_cache: dict = {"ergebnis": None, "pfad": None, "mtime": None}


def _vergleich_neueste_datei() -> Path | None:
    # ".json." schliesst die Vermerk-Beidateien aus, die andere Werkzeuge
    # NEBEN den Lauf legen (ab_vergleich_abruf_X.json.rasterblick.json,
    # ....gegenprobe.json). Sie matchen das Muster, sortieren sich hinter den
    # echten Lauf und gewinnen dadurch das "neueste" -- seit dem ersten
    # Rasterblick lieferte /api/vergleich also den Inhalt eines Vermerks.
    # Aufgefallen am 2026-08-13, weil der Selbsttest an ["rows"] scheiterte.
    kandidaten = sorted(p for p in RUNS_DIR.glob("ab_vergleich_abruf_*.json")
                        if ".json." not in p.name)
    return kandidaten[-1] if kandidaten else None


def _vergleich_stand() -> dict:
    pfad = _vergleich_neueste_datei()
    if pfad is None:
        return {"error": "kein Vergleichslauf gefunden (runs/ab_vergleich_abruf_*.json)"}
    mtime = pfad.stat().st_mtime
    if (_vergleich_cache["ergebnis"] is None
            or _vergleich_cache["pfad"] != str(pfad)
            or _vergleich_cache["mtime"] != mtime):
        roh = json.loads(pfad.read_text(encoding="utf-8"))
        rows_je_kennung = {r["kennung"]: r for r in roh.get("rows", [])}
        unterschiede = []
        for u in roh.get("unterschiede_A_B", []):
            zeile = rows_je_kennung.get(u["kennung"], {})
            unterschiede.append({
                **u,
                "A_antwort": (zeile.get("A") or {}).get("mit_abruf"),
                "B_antwort": (zeile.get("B") or {}).get("mit_abruf"),
            })
        datum = pfad.stem.replace("ab_vergleich_abruf_", "")
        _vergleich_cache["ergebnis"] = {
            "datei": pfad.name, "datum": datum,
            "model": roh.get("model"), "n_cases": roh.get("n_cases"),
            "bestand_vorher": roh.get("bestand_vorher"),
            "bestand_nachher": roh.get("bestand_nachher"),
            "bestand_unveraendert": roh.get("bestand_unveraendert"),
            "zusammenfassung": roh.get("zusammenfassung"),
            "unterschiede": unterschiede,
        }
        _vergleich_cache["pfad"] = str(pfad)
        _vergleich_cache["mtime"] = mtime
    return _vergleich_cache["ergebnis"]


# ─── Abschnitt 11: Abrufweg (Auftrag 2026-08-12) ───────────────────────────
#
# Fuenf Stationen des Abrufs, ECHT gerechnet fuer eine eingegebene Anfrage --
# dieselben Bausteine wie haken/suchpfad_abruf.kandidaten() und
# messungen/kandidatendiagnose.py (kein Nachbau):
#   1 Anfrage       -- _or_query()/keywords(), MIN_HITS informativ (der
#                       aktive Weg SUCHPFAD_ABRUF=True prueft MIN_HITS NICHT,
#                       das steht dazu -- sonst waere die Anzeige falsch)
#   2 Kandidaten    -- Stichwortkanal (FTS5, _or_query) und Bedeutungskanal
#      je Kanal        (Embedding, _embedding_ranking) GETRENNT, UNGEFILTERT
#                       nach Gattung -- wie kandidatendiagnose.diagnose() es
#                       fuer den Fall d84b6b64 tut, sonst waere die Gattung
#                       schon in der Kanalliste verschwunden und nicht mehr
#                       als EIGENE Station zeigbar
#   3 Verschmelzung -- embeddings.rrf_fuse(stichwort, bedeutung), ungekappt
#   4 Deckel        -- oberste MAX_NODES+MAX_LESSONS der Verschmelzung, dann
#                       Gattung- und Freigabe-Filter, dann Deckel je Art
#   5 geliefert     -- was uebrig bleibt
#
# NICHT nachgebildet (liegt HINTER der Deckel-Station, nicht in den fuenf
# oben genannten): trust_score, rangfolge, Explore-Ersetzung, und bei Lehren
# die Nachsortierung nach Stichworttreffern statt Verschmelzungsrang -- diese
# Stationen aendern die Reihenfolge INNERHALB der bereits gelieferten Menge,
# nicht mehr WER geliefert wird. Wer sie braucht, findet sie in
# knowledge_recall_hook.query().
#
# Anzeige-Deckel je Kanal (ANZEIGE_TOP): nur die Bedeutungskanal-Liste kann
# tausende Eintraege haben (jeder Knoten mit Vektor bekommt einen Rang) --
# fuer die Darstellung werden nur die obersten ANZEIGE_TOP gezeigt, die
# Gesamtzahl bleibt echt (treffer_gesamt).

ANZEIGE_TOP = 30


def _abrufweg_titel(conn: sqlite3.Connection, node_ids: set, lesson_ids: set) -> dict:
    out: dict[str, dict] = {}
    if node_ids:
        ph = ",".join("?" for _ in node_ids)
        for r in conn.execute(
            f"SELECT id, path, title, gattung, gilt_ab, gilt_bis FROM knowledge_nodes WHERE id IN ({ph})",
            list(node_ids),
        ):
            out[r["id"]] = {
                "art": "knoten", "titel": r["title"], "pfad": r["path"],
                "gattung_ok": gattung_filter.ist_arbeitsbestand(r["gattung"]),
                "freigabe_ok": knowledge_recall_hook._ist_geltend(r["gilt_ab"], r["gilt_bis"]),
            }
    if lesson_ids:
        ph = ",".join("?" for _ in lesson_ids)
        for r in conn.execute(
            f"SELECT id, description FROM lessons_learned WHERE id IN ({ph})", list(lesson_ids)
        ):
            out[r["id"]] = {"art": "lehre", "titel": r["description"], "pfad": None,
                             "gattung_ok": True, "freigabe_ok": True}
    return out


def _abrufweg_kanal(ids: list[str], meta: dict, staerke: dict[str, float] | None = None) -> dict:
    eintraege = []
    for i, doc_id in enumerate(ids[:ANZEIGE_TOP]):
        m = meta.get(doc_id, {"art": "?", "titel": doc_id, "pfad": None})
        eintrag = {"id": doc_id, "rang": i + 1, **m}
        if staerke is not None and doc_id in staerke:
            eintrag["staerke"] = round(staerke[doc_id], 4)
        eintraege.append(eintrag)
    return {"treffer_gesamt": len(ids), "gezeigt": len(eintraege), "eintraege": eintraege}


def _bedeutung_staerke(conn: sqlite3.Connection, query_vec: list[float] | None,
                        node_ids: set, lesson_ids: set) -> dict[str, float]:
    """Kanaleigenes Mass des Bedeutungskanals: Cosine-Aehnlichkeit der Anfrage
    zu jedem angezeigten Eintrag. NICHT der Verschmelzungsrang (rrf_fuse) --
    der gewichtet nur die Position IM Kanal, siehe Knoten
    /brainlehr/rrf-gewichtet-den-rang-im-kanal-nicht. Und die rohe Zahl ist
    selbst kein Relevanzfilter (/shared/cosine-aehnlichkeit-ist-anisotrop) --
    hier nur als RELATIVES Mass innerhalb derselben Anfrage weitergereicht,
    nie gegen eine absolute Schwelle geprueft.
    Nur fuer die uebergebenen (angezeigten) IDs berechnet, nicht fuer die
    gesamte Embedding-Tabelle."""
    out: dict[str, float] = {}
    if query_vec is None:
        return out
    for kind, id_set in (("node", node_ids), ("lesson", lesson_ids)):
        if not id_set:
            continue
        ph = ",".join("?" for _ in id_set)
        for r in conn.execute(
            f"SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ? AND model = ? "
            f"AND ref_id IN ({ph})",
            (kind, embeddings.DEFAULT_EMBED_MODEL, *id_set),
        ):
            out[r["ref_id"]] = embeddings.cosine_similarity(query_vec, embeddings.unpack_embedding(r["vector"]))
    return out


def _or_query_woerter(fts_query: str) -> list[str]:
    """Zerlegt das von _or_query() gebaute FTS5-ODER-Muster zurueck in die
    einzelnen Suchworte -- das sind exakt die Worte, die an den Stichwortkanal
    gingen (keine zweite Berechnung derselben Sache, nur die Rueckrichtung
    derselben Zeichenkette). Diese Liste weicht von schluesselwoerter/kws ab:
    kws ist gefiltert (Stoppwoerter raus, Laenge>=4, max. 8) und dient nur der
    MIN_HITS-Anzeige, nicht dem tatsaechlichen Kanal."""
    if not fts_query:
        return []
    out = []
    for teil in fts_query.split(" OR "):
        teil = teil.strip()
        if teil.startswith('"') and teil.endswith('"'):
            teil = teil[1:-1].replace('""', '"')
        out.append(teil)
    return out


def abrufweg_berechnen(conn: sqlite3.Connection, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"leer": True}
    fts_query = _or_query(text)
    kws = knowledge_recall_hook.keywords(text)
    anfrage = {
        "text": text, "schluesselwoerter": kws, "min_hits_schwelle": knowledge_recall_hook.MIN_HITS,
        "min_hits_erfuellt": len(kws) >= knowledge_recall_hook.MIN_HITS,
        "min_hits_wirkt_im_aktiven_weg": not knowledge_recall_hook._suchpfad_aktiv(),
        "stichwort_suchworte": _or_query_woerter(fts_query),
        "eingebetteter_text": text,
    }
    if not fts_query:
        return {"leer": True, "anfrage": anfrage}

    node_ids = [r["id"] for r in conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        "WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 ORDER BY rank", (fts_query,))]
    lesson_ids = [r["id"] for r in conn.execute(
        "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' ORDER BY rank", (fts_query,))]
    stichwort_ordered = embeddings.rrf_fuse(node_ids, lesson_ids, embedding_weight=1.0)

    query_vec = embeddings.embed_text(text)
    if query_vec is not None:
        emb_node_ids = _embedding_ranking(conn, "node", query_vec, None)
        emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, None)
    else:
        emb_node_ids, emb_lesson_ids = [], []
    bedeutung_ordered = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)

    gewicht = embeddings.hybrid_retrieval_weight()
    fused = embeddings.rrf_fuse(stichwort_ordered, bedeutung_ordered, embedding_weight=gewicht)
    fused_rang = {doc_id: i + 1 for i, doc_id in enumerate(fused)}
    stichwort_rang = {doc_id: i + 1 for i, doc_id in enumerate(stichwort_ordered)}
    bedeutung_rang = {doc_id: i + 1 for i, doc_id in enumerate(bedeutung_ordered)}

    max_nodes, max_lessons = knowledge_recall_hook.MAX_NODES, knowledge_recall_hook.MAX_LESSONS
    deckel_groesse = max_nodes + max_lessons
    pool = fused[:deckel_groesse]

    # Metadaten (Titel/Gattung/Freigabe) nur fuer das, was irgendwo angezeigt
    # wird: die obersten ANZEIGE_TOP je Kanal, der ganze Deckel-Pool, und der
    # Ueberhang direkt darueber (fuer die "ueber dem Deckel"-Station unten).
    angezeigt = (set(stichwort_ordered[:ANZEIGE_TOP]) | set(bedeutung_ordered[:ANZEIGE_TOP])
                 | set(pool) | set(fused[deckel_groesse:deckel_groesse + ANZEIGE_TOP]))
    meta_ids_node = angezeigt & (set(node_ids) | set(emb_node_ids))
    meta_ids_lesson = angezeigt & (set(lesson_ids) | set(emb_lesson_ids))
    meta = _abrufweg_titel(conn, meta_ids_node, meta_ids_lesson)
    staerke = _bedeutung_staerke(conn, query_vec, meta_ids_node, meta_ids_lesson)

    # Deckel-Station: Reihenfolge des Pools bleibt die Verschmelzungs-Reihenfolge.
    # Je Eintrag zuerst Gattung, dann Freigabe, dann -- unter den ueberlebenden --
    # der Deckel je Art (Knoten/Lehren getrennt gezaehlt).
    deckel_eintraege = []
    n_gezaehlt = l_gezaehlt = 0
    geliefert_knoten, geliefert_lehren = [], []
    for doc_id in pool:
        m = meta.get(doc_id, {"art": "?", "titel": doc_id, "pfad": None, "gattung_ok": True, "freigabe_ok": True})
        grund = None
        if not m.get("gattung_ok", True):
            grund = "gattung"
        elif not m.get("freigabe_ok", True):
            grund = "freigabe"
        else:
            if m["art"] == "knoten":
                if n_gezaehlt < max_nodes:
                    n_gezaehlt += 1
                    geliefert_knoten.append(doc_id)
                else:
                    grund = "deckel_art"
            else:
                if l_gezaehlt < max_lessons:
                    l_gezaehlt += 1
                    geliefert_lehren.append(doc_id)
                else:
                    grund = "deckel_art"
        deckel_eintraege.append({
            "id": doc_id, "rang_verschmolzen": fused_rang[doc_id],
            "rang_stichwort": stichwort_rang.get(doc_id), "rang_bedeutung": bedeutung_rang.get(doc_id),
            "art": m["art"], "titel": m["titel"], "pfad": m.get("pfad"),
            "ausgeschieden": grund,
        })

    # Aussenherum: die besten je Kanal, die es nicht einmal in den Pool schaffen --
    # Station "ueber dem Deckel", damit die Kanalspitze nicht kommentarlos endet.
    ueber_deckel = []
    for doc_id in fused[deckel_groesse:deckel_groesse + ANZEIGE_TOP]:
        m = meta.get(doc_id)
        if m is None:
            continue
        ueber_deckel.append({
            "id": doc_id, "rang_verschmolzen": fused_rang[doc_id],
            "rang_stichwort": stichwort_rang.get(doc_id), "rang_bedeutung": bedeutung_rang.get(doc_id),
            "art": m["art"], "titel": m["titel"], "pfad": m.get("pfad"), "ausgeschieden": "deckel",
        })

    return {
        "leer": False,
        "anfrage": anfrage,
        "kanaele": {
            "stichwort": _abrufweg_kanal(stichwort_ordered, meta),
            "bedeutung": _abrufweg_kanal(bedeutung_ordered, meta, staerke),
        },
        "embedding_verfuegbar": query_vec is not None,
        "verschmelzung_gewicht": gewicht,
        "deckel": {"max_nodes": max_nodes, "max_lessons": max_lessons, "pool_groesse": deckel_groesse,
                   "eintraege": deckel_eintraege, "ueber_deckel": ueber_deckel},
        "geliefert": {"knoten": geliefert_knoten, "lehren": geliefert_lehren,
                      "eintraege": [dict(meta[i], id=i) for i in geliefert_knoten + geliefert_lehren]},
    }


def _echtkorpus_stand() -> dict:
    """Anfragetexte fuer den Simulator -- reine Wortlaute, nichts erfunden.
    Fehlt die Datei (z.B. auf einem anderen Rechner), liefert eine leere
    Liste statt eines 500ers; der Simulator meldet das dann im Klartext."""
    if not ECHTKORPUS_PATH.exists():
        return {"faelle": []}
    d = json.loads(ECHTKORPUS_PATH.read_text(encoding="utf-8"))
    return {"faelle": [f["prompt"] for f in d.get("faelle", []) if f.get("prompt")]}


def _fundstelle_stand(quelle: str, text: str) -> dict:
    """Die Bestellung der App: "wo genau steht das".

    Die Rechnung liegt bewusst hier und nicht in Swift -- der Volltext liegt
    als .txt neben den PDFs, das ist Textarbeit, und sie ist ohne gebaute App
    pruefbar (python3 kern/fundstelle.py --quelle 14). Die App bestellt.
    """
    import fundstelle  # liegt in kern/, per Suchpfad oben eingehaengt
    return fundstelle.loese(quelle, text).als_dict()


def _quellenbestand() -> dict:
    """Der Nenner. Ohne ihn ist jede Aussage ueber Abdeckung eine Behauptung."""
    import fundstelle
    return fundstelle.bestand()


def _quellenliste() -> dict:
    """Die Quellen mit Gattung und Freigabe -- fuer den Browser der App.

    Liest quellen.json direkt statt kern/fundstelle.py zu erweitern: Diese
    Datei haelt gerade eine andere Sitzung, und ein neuer Endpunkt hier
    kollidiert mit nichts.

    FREIGABE: Das Quellenverzeichnis von buckeberg kennt keine solche Spalte.
    Sie wird deshalb NICHT erfunden -- der Wert bleibt leer, und die
    Sichtbarkeitspruefung der App liest daraus "gesperrt". Das ist die
    sichere Richtung: Wer hier ersatzweise "offen" einsetzt, baut eine
    Schranke, die sich durch eine fehlende Spalte oeffnet.
    """
    import fundstelle
    w = fundstelle.korpus_wurzel()
    pfad = w / "dossier" / "quellen.json"
    if not pfad.is_file():
        return {"zeilen": []}
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    zeilen = []
    for nr, q in sorted(((k, v) for k, v in roh.items() if k.isdigit()),
                        key=lambda x: int(x[0])):
        zeilen.append({
            "nummer": nr,
            "kurz": q.get("kurz", ""),
            "art": q.get("art", ""),
            "freigabe": q.get("freigabe"),
            "markierbar": bool(q.get("suchtext")),
            "rang": int(q.get("rang") or 0),
        })
    return {"zeilen": zeilen}


def _domaene_import(paket: dict) -> dict:
    """H8b: das atelier schickt den kompletten Paketinhalt (siehe
    docs/PLAN_OPENLEHR_2026-08-14.md §H8), die Pruefung UND das Schreiben
    liegen in kern/domaene.py. Vertrag: domaene.speichere(paket) prueft wie
    pruefe() und liefert bei Annahme zusaetzlich {"gespeichert": int,
    "uebersprungen": int} (Wirkung Null, ADR-018 -- jede geschriebene Zeile
    traegt norm_rang=NULL, wirkt also noch nicht). Bei Ablehnung
    {"angenommen": False, "grund": str} -- grund bereits in Nutzersprache,
    wird unveraendert durchgereicht.

    NACHTRAG 2026-08-15: vorher rief diese Funktion domaene.pruefe() --
    reine Pruefung, ohne Schreibung. Die App meldete daraufhin "gilt jetzt",
    obwohl der Bestand unveraendert blieb (Befund vom selben Tag). Jetzt
    schreibt der Aufruf tatsaechlich, deshalb steht dieser Pfad seit diesem
    Commit NICHT mehr in _OHNE_KOPFPRUEFUNG -- siehe Kommentar dort.

    Fehlt kern/domaene.py noch, kommt hier "verfuegbar": False zurueck statt
    eines Absturzes -- das atelier zeigt das als "kann gerade nicht geprueft
    werden."
    """
    try:
        import domaene  # liegt in kern/, per Suchpfad oben eingehaengt
    except ImportError:
        return {"verfuegbar": False}
    return domaene.speichere(paket)


def _domaene_oberflaeche(domaene_id: str) -> dict:
    """Die Bildschirm-Beschreibung einer IMPORTIERTEN Domaene.

    Gegenstueck zu /api/domaene-import: dort reist die Beschreibung herein,
    hier wird sie gelesen. Ohne diesen Weg muesste das atelier die
    Manifest-DATEI im Dateisystem suchen -- genau das tat `DomaenenSeite` als
    ausdrueckliche Bruecke, und damit waere der Importweg fuer die Oberflaeche
    wirkungslos gewesen (ADR-012: das Wissenspaket reist, das Werkzeug wird
    installiert).

    Drei Antworten, weil der Aufrufer drei Lagen unterscheiden muss:
      {"importiert": False}                     hier nicht importiert
      {"importiert": True, "bildschirme": []}   importiert, ohne Bildschirm
      {"importiert": True, "bildschirme": [..]} importiert, mit Beschreibung
    Der mittlere Fall ist nach ADR-013 zulaessig -- eine Domaene darf nur
    Wissen mitbringen. Ein leeres Ergebnis und "gar nicht da" sind fuer den
    Menschen zwei verschiedene Saetze, deshalb hier zwei verschiedene
    Antworten und nicht eine leere Liste fuer beides."""
    try:
        import domaene
    except ImportError:
        return {"verfuegbar": False}
    ob = domaene.lies_oberflaeche(domaene_id)
    if ob is None:
        return {"importiert": False}
    return {"importiert": True, "fassung": ob.get("fassung"),
            "bildschirme": ob.get("bildschirme") or []}


def _abrufweg_stand(text: str) -> dict:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return abrufweg_berechnen(conn, text)
    finally:
        conn.close()


def _eintrag_html(kennung: str) -> str | None:
    """Kleine lokale Leseseite fuer anklickbare Brainlehr-Kennungen."""
    if not re.fullmatch(r"(?:L-[0-9a-f]{6}|[0-9a-f]{8,64})", kennung):
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        if kennung.startswith("L-"):
            row = conn.execute(
                "SELECT id, type, severity, description, root_cause, resolution, "
                "prevention, status, freigabe FROM lessons_learned WHERE id = ?",
                (kennung,),
            ).fetchone()
            if not row:
                return None
            titel = f"{row['id']} — {row['type']}"
            meta = (f"Schweregrad: {row['severity']} · Status: {row['status']} · "
                    f"Freigabe: {row['freigabe']}")
            felder = (("Lehre", row["description"]),
                      ("Ursache", row["root_cause"]),
                      ("Lösung", row["resolution"]),
                      ("Vorbeugung", row["prevention"]))
        else:
            row = conn.execute(
                "SELECT id, path, title, summary, content, source, freigabe "
                "FROM knowledge_nodes WHERE id = ? AND zurueckgezogen = 0",
                (kennung,),
            ).fetchone()
            if not row:
                return None
            titel = f"{row['id']} — {row['title']}"
            meta = f"Pfad: {row['path']} · Freigabe: {row['freigabe']}"
            felder = (("Kurzfassung", row["summary"]),
                      ("Inhalt", row["content"]),
                      ("Quelle", row["source"]))
    finally:
        conn.close()

    abschnitte = "".join(
        f"<section><h2>{html.escape(name)}</h2><p>{html.escape(str(wert))}</p></section>"
        for name, wert in felder if wert
    )
    return (
        "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(titel)}</title></head>"
        "<body><main style=\"max-width:48rem;margin:3rem auto;padding:0 1rem;"
        "font:17px/1.55 system-ui,sans-serif\"><a href=\"/\">← Brainlehr</a>"
        f"<h1>{html.escape(titel)}</h1><p>{html.escape(meta)}</p>{abschnitte}"
        "</main></body></html>"
    )


# ─── Ausweispruefung (ADR-020 Abschnitt 5, Schritt 1) ──────────────────────
#
# BEFUND, DER DIES ERZWINGT: _herkunft_ok() prueft nur den Origin-Kopf. Ein
# Browser setzt ihn selbst und kann ihn nicht faelschen -- ein Programm
# (Python-`requests`, ein MCP-Server, jeder HTTP-Klient) setzt jeden
# Origin-Kopf, den der Code will. Solange der Dienst an 127.0.0.1 gebunden
# bleibt, traegt die Origin-Pruefung trotzdem etwas (fremde Webseiten im
# Browser des Betreibers). Faellt die Bindung (Voraussetzung fuer ADR-020
# Abschnitt 5, spaeter), ist sie NICHT schwaecher, sondern wirkungslos --
# genau das schliesst diese Pruefung, bevor irgendein Werkzeug umzieht.
#
# WIE SICH EIN KLIENT AUSWEIST: ein Geheimnis je Aufruf, im Kopf
# 'Authorization: Bearer <Geheimnis>' -- dem in kern/ausweis.py bereits
# angekuendigten Weg (Docstring dort: "spaeter aus dem Bearer-Token
# (ADR-001)"). Kein eigenes Session-Token: ein zusaetzlicher Ausstellungs-
# /Ablaufmechanismus fuer Sitzungen waere ein zweites Geheimnis-System neben
# kern/ausweis.py, das dort bereits Ablauf UND Widerruf kennt (widerrufen(),
# entwiderrufen(), gilt_bis) -- ein Kopf mit dem Ausweis-Geheimnis selbst
# nutzt das, ohne es zu duplizieren.
#
# WIRD DAS GEHEIMNIS PROTOKOLLIERT? Handler.log_message() ist fuer den ganzen
# Server stillgelegt (Zeile oben), also gibt es hier kein Zugriffslog, das
# Kopfzeilen mitschriebe. sqlite3.connect()/Query-Logging dieses Moduls
# beruehrt keine HTTP-Kopfzeilen. Gemessen per Grep auf 'log' in dieser
# Datei: ausser log_message() (leer) kein Treffer.
#
# WELCHE RECHT WIRD VERLANGT: 'verwaltung:schreiben' -- laut ROLLEN in
# kern/ausweis.py traegt nur 'betreiber' (per '*') dieses Recht, und es steht
# in NICHT_DELEGIERBAR. Passt zum Docstring dieser Datei: eine Oberflaeche
# fuer "liegen gebliebene BETREIBER-Entscheidungen", kein Mehrbenutzerdienst.
_SCHREIBRECHT = "verwaltung:schreiben"

# ZWISCHENSTAND, BENANNT STATT VERSCHWIEGEN: /api/ausweis-anlegen und
# /api/ausweis-einladen pruefen ihre Beglaubigung bereits SELBST, eine Ebene
# tiefer -- das mitgeschickte Geheimnis geht unveraendert an
# kern/ausweis.py::anlegen()/einladen(), und die pruefen dort die
# Einbuergerung (_pruefe_einbuergerung/_aussteller_name) gegen denselben
# Bestand. Eine zweite, gleichlautende Kopf-Pruefung HIER waere kein
# zweiter Schutz, sondern ein zweiter Weg zum selben Fehler -- und sie
# bricht den einzigen Weg, den die App fuer einen Ausweis-Wechsel hat:
# app/Sources/Atelier/AusweisDienst.swift (tabu fuer diesen Auftrag) traegt
# das Geheimnis im JSON-Body, nicht im Authorization-Kopf. Bekommt die App
# eine eigene Kopf-Uebertragung, ziehen auch diese zwei Pfade auf die
# einheitliche Pruefung um -- bis dahin bleibt es bei der tieferliegenden.
#
# NACHTRAG 2026-08-15 (Regression aus Commit 03cce992, Fund im selben
# Auftrag wie die Origin-Nachruestung in DomaeneImportDienst.swift/
# QuellenBereich.swift): /api/fundstelle und /api/domaene-import wurden von
# "7 von 9 POST-Pfaden" ohne eigene Pruefung mitgezogen, obwohl der Commit-
# Titel ausdruecklich nur "schreibende Dienst-Endpunkte" meint. Gemessen,
# nicht vermutet: _fundstelle_stand() ruft fundstelle.loese() -- eine reine
# Textstellen-Aufloesung, kein INSERT/UPDATE/write_text in kern/fundstelle.py
# (grep bestaetigt). /api/domaene-import blieb hier so lange richtig
# gerechnet, wie _domaene_import() domaene.pruefe() rief (read-only ueber
# speicher.lesen(), kein Schreibpfad erreicht).
#
# NACHTRAG 2026-08-15, zweite Aenderung, GENAU DER FALL, DEN DER ERSTE
# NACHTRAG SELBST ANGEKUENDIGT HAT: _domaene_import() ruft jetzt
# domaene.speichere() (Befund vom selben Tag -- die App meldete "gilt
# jetzt", der Bestand blieb unveraendert, weil nur geprueft, nie
# geschrieben wurde). Ab hier gilt fuer /api/domaene-import wieder dieselbe
# Begruendung wie fuer jeden anderen schreibenden Pfad: 'verwaltung:schreiben'
# ist die Sache nach richtig, also raus aus dieser Liste.
_OHNE_KOPFPRUEFUNG = frozenset({
    "/api/ausweis-anlegen", "/api/ausweis-einladen",
    "/api/fundstelle",
})


def _ausweis_kopf(headers) -> str | None:
    wert = headers.get("Authorization", "")
    if not wert.startswith("Bearer "):
        return None
    geheimnis = wert[len("Bearer "):].strip()
    return geheimnis or None


def _beglaubigt_fuer_schreiben(headers) -> bool:
    """Loest den Authorization-Kopf ueber kern/ausweis.py auf. Kein Fehler,
    kein Zustand hier gehalten -- nur True/False, wie kern/ausweis.py es
    selbst schon fuer jeden anderen Aufrufer entscheidet (widerrufen,
    abgelaufen, falsches Geheimnis, kein Geheimnis: alle vier fallen dort
    gleich auf 'unbeglaubigt' zurueck, keine Sonderbehandlung noetig)."""
    geheimnis = _ausweis_kopf(headers)
    if not geheimnis:
        return False
    a = ausweis_kern.loese_auf(geheimnis=geheimnis)
    return a.beglaubigt and ausweis_kern.darf(a, _SCHREIBRECHT)


# ─── HTTP ─────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # ponytail: stdout-Stille, kein eigenes Log-Format
        pass

    def _herkunft_ok(self) -> bool:
        """Fund O2 (docs/SICHERHEITSFUNDE_2026-08-14.md): POST prueft weder
        Herkunft noch Kennung -- 0 Treffer fuer ausweis|Authorization|token.
        Jede fremde Seite im Browser des Betreibers konnte so schreiben, ohne
        Rechnerzugang. Browser setzen bei POST-Anfragen IMMER einen
        Origin-Kopf (Fetch-Standard), auch bei gleichem Ursprung -- das macht
        ihn zur Schranke, OHNE entscheidungen.html anzufassen (tabu fuer
        diesen Auftrag): ein Aufruf von der eigenen, hier ausgelieferten
        Seite traegt automatisch den passenden Origin, ein fremder nicht."""
        origin = self.headers.get("Origin")
        if not origin:
            return False
        return origin == f"http://127.0.0.1:{self.server.server_port}"

    def _json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; "
                         "base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _lokaler_host(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _datei(self, pfad: Path, typ: str) -> None:
        """Eine Datei vom Datentraeger ausliefern. NUR fuer die fest benannten
        Pfade unten -- keine allgemeine Dateiauslieferung. Der Aufrufer nennt
        den Pfad, nie der Klient: ein Pfad aus der Anfrage waere mit '..' der
        Schluessel zu jeder Datei dieses Rechners."""
        if not pfad.exists():
            self._json({"error": f"nicht vorhanden: {pfad.name}"}, 404)
            return
        body = pfad.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/eintrag/"):
            if not self._lokaler_host():
                self._json({"error": "nicht erlaubt"}, 403)
                return
            body = _eintrag_html(self.path.removeprefix("/eintrag/"))
            if body is None:
                self._json({"error": "Eintrag nicht gefunden"}, 404)
                return
            self._html(body)
            return
        # Verbundkarte (Schritt 2, docs/PLAN_DIAGRAMME_2026-08-16.md): das
        # ERZEUGNIS wird ausgeliefert, nicht neu berechnet -- ein Lauf ueber
        # 27 Repos dauert gemessen 22 s und gehoert nicht in eine Anfrage.
        # Aktuell gehalten wird beim ERZEUGEN (melder/verbundkarte.py), nicht
        # beim Anzeigen.
        if self.path == "/landkarten" or self.path.startswith("/landkarten."):
            self._datei(HERE / "landkarten.html", "text/html; charset=utf-8")
            return
        # Die Auswahl ergibt sich aus dem, was TATSAECHLICH erzeugt wurde --
        # keine gepflegte Liste im Quelltext, die neben dem Ablageort her
        # altert. Fehlt eine Karte, taucht sie schlicht nicht auf.
        if self.path == "/api/landkarten":
            ordner = HERE / "docs" / "karten"
            karten = []
            for p in sorted(ordner.glob("*.md")) if ordner.exists() else []:
                kopf = p.read_text(encoding="utf-8").split("\n", 1)[0]
                karten.append({"kennung": p.stem, "titel": kopf.lstrip("# ").strip() or p.stem})
            self._json({"karten": karten})
            return
        if self.path.startswith("/api/domaene-oberflaeche?"):
            from urllib.parse import parse_qs, urlparse
            kennung = (parse_qs(urlparse(self.path).query).get("domaene") or [""])[0]
            self._json(_domaene_oberflaeche(kennung))
            return
        if self.path.startswith("/api/landkarte?"):
            from urllib.parse import parse_qs, urlparse
            gewuenscht = (parse_qs(urlparse(self.path).query).get("k") or [""])[0]
            # Der Klient nennt eine KENNUNG, nie einen Pfad: alles andere waere
            # mit '..' der Schluessel zu jeder Datei dieses Rechners.
            if not re.fullmatch(r"[a-z0-9_-]{1,64}", gewuenscht or ""):
                self._json({"error": "unbekannte Karte"}, 400)
                return
            pfad = HERE / "docs" / "karten" / f"{gewuenscht}.md"
            if not pfad.exists():
                self._json({"error": "noch nicht erzeugt -- python3 melder/landkarten.py"}, 404)
                return
            text = pfad.read_text(encoding="utf-8")
            anfang = text.find("```mermaid")
            ende = text.find("```", anfang + 10) if anfang >= 0 else -1
            mermaid = text[anfang + len("```mermaid"):ende].strip() if ende > 0 else ""
            hinweis = text[ende + 3:].strip() if ende > 0 else ""
            # Der Graph liegt als Beistelldatei aus DEMSELBEN Lauf daneben
            # (melder/landkarten.py schreibt .md und .json zusammen). Fehlt
            # sie, faellt nur die Wegsuche aus und das Bild bleibt -- kein
            # Grund, die ganze Karte zu verweigern.
            graph = {}
            gpfad = pfad.with_suffix(".json")
            if gpfad.exists():
                try:
                    graph = json.loads(gpfad.read_text(encoding="utf-8"))
                except ValueError:
                    graph = {}
            self._json({"mermaid": mermaid, "hinweis": hinweis, "markdown": text,
                        "graph": {"knoten": graph.get("knoten", []),
                                  "kanten": graph.get("kanten", [])}})
            return
        if self.path == "/statisch/mermaid.min.js":
            self._datei(HERE / "berichte" / "statisch" / "mermaid.min.js",
                        "application/javascript; charset=utf-8")
            return
        if self.path in ("/", "/entscheidungen.html"):
            body = HTML_PATH.read_text(encoding="utf-8").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/stand":
            try:
                self._json(_gesamtstand())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path in ("/raum", "/raum.html", "/vergleich", "/vergleich.html"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/api/raum":
            try:
                self._json(_raum_stand())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path == "/api/vergleich":
            try:
                self._json(_vergleich_stand())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path == "/api/echtkorpus":
            try:
                self._json(_echtkorpus_stand())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path == "/api/quellenbestand":
            try:
                self._json(_quellenbestand())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path == "/api/quellenliste":
            try:
                self._json(_quellenliste())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if self.path == "/api/ausweisliste":
            try:
                self._json(_ausweis_liste())
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        self._json({"error": "unbekannter Pfad"}, 404)

    def do_POST(self):
        if not self._herkunft_ok():
            self._json({"error": "nicht erlaubt"}, 403)
            return
        if (self.path not in _OHNE_KOPFPRUEFUNG
                and not _beglaubigt_fuer_schreiben(self.headers)):
            self._json({"error": "Diese Aktion braucht einen gültigen "
                                  "Ausweis (Kopf 'Authorization: Bearer "
                                  "<Geheimnis>')."}, 403)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json({"error": "ungueltiges JSON"}, 400)
            return
        try:
            if self.path == "/api/eskalation":
                out = _eskalation_handeln(payload.get("handlung", ""), payload.get("id", ""),
                                           payload.get("regel", ""))
            elif self.path == "/api/eilmeldung":
                out = _eilmeldung_quittieren(payload.get("sitzung", ""), payload.get("schluessel", ""))
            elif self.path == "/api/siegbedingung":
                out = _siegbedingung_setzen(payload.get("gewichte", {}))
            elif self.path == "/api/nachtschicht":
                out = _nachtschicht_setzen(payload.get("aktiv", ""), payload.get("antrieb", ""),
                                            payload.get("budget", ""))
            elif self.path == "/api/abrufweg":
                out = _abrufweg_stand(payload.get("text", ""))
            elif self.path == "/api/fundstelle":
                out = _fundstelle_stand(str(payload.get("quelle", "")),
                                        str(payload.get("text", "")))
            elif self.path == "/api/domaene-import":
                out = _domaene_import(payload)
            elif self.path == "/api/ausweis-anlegen":
                out = _ausweis_anlegen(payload)
            elif self.path == "/api/ausweis-einladen":
                out = _ausweis_einladen(payload)
            else:
                self._json({"error": "unbekannter Pfad"}, 404)
                return
            self._json(out)
        except Exception as e:
            self._json({"error": str(e)}, 500)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8799)
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        return _selftest()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        # ADR-020, Weg 3 (kein Klient startet den Dienst mit -- ADR-020
        # begruendet, warum das architektonisch ausscheidet): scheitert der
        # Start, weil der Port belegt ist, muss das lesbar sein statt einer
        # rohen Stapelspur. pflege/wissensraum_start.sh faengt den
        # Normalfall (Dienst laeuft schon) vorher per curl-Probe ab; dieser
        # Zweig greift, wenn trotzdem direkt gestartet wird und dort etwas
        # anderes sitzt.
        print(
            "An dieser Stelle laeuft bereits etwas -- moeglicherweise der "
            "Dienst schon. Bitte pruefen, bevor erneut gestartet wird."
        )
        return 1
    print(f"Entscheidungsoberflaeche: http://127.0.0.1:{args.port}/  (nur lokal, Strg+C zum Beenden)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def _selftest() -> int:
    """Ponytail-Selbsttest: liest den echten Bestand read-only, schreibt
    Siegbedingung/Nachtschicht in eine TEMPORAERE DB-Kopie (nie die echte),
    prueft Rundlauf + dass keine der Original-Skriptdateien beruehrt wird."""
    import shutil
    import tempfile

    global DB_PATH, AUSWEIS_START_SCRIPT
    real_db_mtime = DB_PATH.stat().st_mtime

    # 1) Gesamtstand gegen die echte DB muss ohne Ausnahme durchlaufen.
    stand = _gesamtstand()
    assert "eskalation" in stand and "normkonflikte" in stand
    assert stand["titelverteidiger"] is None or isinstance(stand["titelverteidiger"], dict)
    assert stand["herkunftsmodus"] == {"gefunden": False}
    assert DB_PATH.stat().st_mtime == real_db_mtime, "Gesamtstand hat die echte DB veraendert"

    # 1b) Echtkorpus fuer den Simulator: reine Lesefunktion, muss auch ohne
    # die Datei (anderer Rechner) ohne Ausnahme eine leere Liste liefern.
    korpus = _echtkorpus_stand()
    assert isinstance(korpus["faelle"], list)
    if ECHTKORPUS_PATH.exists():
        assert len(korpus["faelle"]) > 0
        assert all(isinstance(f, str) and f for f in korpus["faelle"])

    # 2) Schreibpfade (Siegbedingung/Nachtschicht) gegen eine Kopie.
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "brainlehr.db"
        shutil.copy2(DB_PATH, copy)
        DB_PATH = copy
        try:
            vor = _siegbedingung_stand()
            assert vor["gewichte"]["kosten"] == 1.0  # Vorgabe, solange nichts gesetzt

            nach = _siegbedingung_setzen({"kosten": 3.5, "streuung": 0.0})
            assert nach["gewichte"]["kosten"] == 3.5
            assert nach["gewichte"]["streuung"] == 0.0
            assert nach["geraten"] is False, "nach explizitem Setzen darf 'geraten' nicht mehr True sein"

            n_vor = _nachtschicht_stand()
            assert n_vor["aktiv"] == "aus"  # Vorgabe

            n_nach = _nachtschicht_setzen("ein", "keiner", "12")
            assert n_nach["aktiv"] == "ein"
            assert n_nach["budget_aufrufe"] == "12"

            fehler = _nachtschicht_setzen("vielleicht", "keiner", "12")
            assert "error" in fehler, "Negativfall: ungueltiger aktiv-Wert muss abgelehnt werden"
        finally:
            DB_PATH = Path(__file__).resolve().parent.parent / "brainlehr.db"

    # 2b) Eskalation: befoerdern/zurueckstufen gegen Kopien von DB und
    # CLAUDE.md -- eskalation_vorlage haelt DB_PATH/CLAUDE_MD_PATH als
    # eigene Modul-Globale, deshalb hier eigens umgehaengt statt ueber
    # entscheidungen_server.DB_PATH (das eskalation_vorlage nicht sieht).
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "brainlehr.db"
        md_copy = Path(tmp) / "CLAUDE.md"
        shutil.copy2(eskalation_vorlage.DB_PATH, db_copy)
        md_copy.write_text("# Testkopf\n", encoding="utf-8")
        real_ev_db, real_ev_md = eskalation_vorlage.DB_PATH, eskalation_vorlage.CLAUDE_MD_PATH
        eskalation_vorlage.DB_PATH = db_copy
        eskalation_vorlage.CLAUDE_MD_PATH = md_copy
        try:
            conn = sqlite3.connect(str(db_copy))
            conn.execute(
                "INSERT INTO lessons_learned (id, type, description, prevention, occurrences, status) "
                "VALUES ('L-selftest', 'antipattern', 'Testlehre', 'Testregel.', 3, ?)",
                (eskalation_vorlage.STATUS_POOL,),
            )
            conn.commit()
            conn.close()

            # Negativfall (rot vor gruen): kein Regeltext -> abgelehnt.
            fehler = _eskalation_befoerdern("L-selftest", "")
            assert fehler.get("ok") is False, "Negativfall: leerer Regeltext darf nicht befoerdern"
            assert "[L-selftest]" not in md_copy.read_text(encoding="utf-8")

            vor = _eskalation_stand()
            assert any(k["id"] == "L-selftest" for k in vor["kandidaten"])

            ok = _eskalation_befoerdern("L-selftest", "Klartext-Regel fuer den Selbsttest.")
            assert ok.get("ok") is True
            assert "[L-selftest] Klartext-Regel fuer den Selbsttest." in md_copy.read_text(encoding="utf-8"), \
                "Befoerderung muss den UNGEKUERZTEN, uebergebenen Regeltext schreiben (nicht die alte _cap()-Kuerzung)"

            nach = _eskalation_stand()
            assert not any(k["id"] == "L-selftest" for k in nach["kandidaten"]), "befoerderte Lehre muss aus den Kandidaten verschwinden"
            treffer = [b for b in nach["befoerdert"] if b["id"] == "L-selftest"]
            assert treffer and treffer[0]["seit"] is not None, "Beforderungszeitpunkt muss festgehalten sein"

            demote = _eskalation_handeln("zurueckstufen", "L-selftest")
            assert demote.get("ok") is True
            assert "[L-selftest]" not in md_copy.read_text(encoding="utf-8")
            danach = _eskalation_stand()
            assert any(k["id"] == "L-selftest" for k in danach["zurueckgestuft"]), \
                "zurueckgestufte Lehre gehoert in die eigene Gruppe, nicht kommentarlos zurueck unter die Kandidaten"
            assert not any(k["id"] == "L-selftest" for k in danach["kandidaten"])
        finally:
            eskalation_vorlage.DB_PATH = real_ev_db
            eskalation_vorlage.CLAUDE_MD_PATH = real_ev_md

    # 3) Eilmeldungen: leerer/kaputter Zustand darf nicht crashen (Negativfall).
    assert isinstance(_eilmeldungen_stand(), list)

    # 3a) Ausweis: der neue Bruecken-Endpunkt zum Ausweis-Helfer (Abschnitt
    # 5b). Rot-vor-gruen fuer die Grenzwerte aus dem Auftrag 2026-08-15:
    # Skript fehlt, Dienst haengt (Timeout), Geheimnis nur ueber STDIN, nie
    # argv. widerrufen/abgelaufen sind Eigenschaften von kern/ausweis.py
    # (eigener Selbsttest dort, _selftest_widerruf) -- hier nur geprueft,
    # dass eine solche {"fehler": ...}-Antwort UNVERAENDERT durchgereicht
    # wird, ohne kern/ausweis.py's Logik zu duplizieren.
    echtes_skript = AUSWEIS_START_SCRIPT

    # Grenzwert: Skript fehlt (Dienst nicht eingerichtet) -- verstaendliche
    # Meldung statt Absturz.
    AUSWEIS_START_SCRIPT = Path(tempfile.mkdtemp()) / "fehlt.sh"
    fehlend = _ausweis_liste()
    assert fehlend == {"fehler": "Der Ausweis-Helfer wurde auf diesem Rechner nicht gefunden."}

    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake_ausweis_start.py"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, json\n"
            "g = sys.stdin.read()\n"
            "if sys.argv[1] == 'widerrufen':\n"
            "    print(json.dumps({'fehler': \"'x' ist widerrufen -- kein neues Mandat.\"}))\n"
            "else:\n"
            "    print(json.dumps({'stdin_laenge': len(g), 'argv': ' '.join(sys.argv[1:])}))\n",
            encoding="utf-8")
        fake.chmod(0o755)
        AUSWEIS_START_SCRIPT = fake

        # Geheimnis nur ueber STDIN -- argv traegt hier nur Name/Art/Rollen,
        # nie das Geheimnis selbst.
        r = _ausweis_aufrufen(["echo-check", "name"], "g3h31m")
        assert r.get("stdin_laenge") == len("g3h31m"), "Geheimnis muss auf STDIN ankommen"
        assert "g3h31m" not in r.get("argv", ""), "Geheimnis darf nie in argv stehen"

        # Widerrufen/abgelaufen: {"fehler": ...} kommt unveraendert durch.
        r2 = _ausweis_aufrufen(["widerrufen"], None)
        assert r2 == {"fehler": "'x' ist widerrufen -- kein neues Mandat."}

    AUSWEIS_START_SCRIPT = echtes_skript

    # Grenzwert: Dienst antwortet langsam -- derselbe Codepfad (Timeout-
    # Behandlung), ohne 20 Sekunden real zu warten.
    _echt_run = subprocess.run

    def _haengt(*a, **k):
        raise subprocess.TimeoutExpired(cmd="ausweis_start.sh", timeout=k.get("timeout", 20))
    subprocess.run = _haengt
    try:
        langsam = _ausweis_liste()
    finally:
        subprocess.run = _echt_run
    assert langsam == {"fehler": "Der Ausweis-Helfer antwortet gerade nicht. Bitte in Kürze erneut versuchen."}

    # Am echten Skript: liste() muss ohne Ausnahme antworten (auch wenn die
    # Ausweisdatei fehlt -- kern/ausweis.py gibt dann eine leere Liste
    # zurueck, keinen Fehler).
    echt = _ausweis_liste()
    assert "fehler" in echt or "ausweise" in echt, "liste() muss entweder Fehler oder Bestand liefern, nie crashen"

    # 3b) Abrufweg: Negativfall (leere Anfrage), und der Fall aus Knoten
    # d84b6b64 -- verliert seinen Rang-1-Treffer aus dem Bedeutungskanal an
    # Rauschen aus zwei Kanaelen (Verschmelzungsrang schlechter als 1). Vor
    # dem Vergleichs-Check (3c): dessen Datenlage haengt an einer fremden
    # Laufdatei-Auswahl und darf einen eigenen, unabhaengigen Befund nicht
    # verdecken (rot-vor-gruen gilt je Station, nicht nur am Blockende).
    leer = _abrufweg_stand("   ")
    assert leer.get("leer") is True, "Negativfall: leere Anfrage darf keinen Weg berechnen"
    fall = _abrufweg_stand("Dichtung Leckage Treibstofftank Fehleranalyse Startverzoegerung")
    assert fall["leer"] is False
    ziel = next((e for e in fall["deckel"]["eintraege"] if e["id"] == "nasa-llis-812"), None)
    assert ziel is not None, "Zielknoten muss im Deckel-Pool auftauchen (Verschmelzungsrang 7 von 17)"
    assert ziel["rang_bedeutung"] == 1, "Zielknoten muss Rang 1 im Bedeutungskanal haben"
    assert ziel["rang_verschmolzen"] > 1, "Rang muss sich in der Verschmelzung gegenueber dem Bedeutungskanal verschlechtern"
    assert ziel["ausgeschieden"] is not None, "Zielknoten darf in diesem Bestand nicht geliefert werden"
    # Kanaleigenes Mass (Cosine, nicht Verschmelzungsrang) muss bis zur
    # Oberflaeche durchgereicht sein -- der Bedeutungsraum-Ansicht braucht es.
    if fall.get("embedding_verfuegbar"):
        bed_eintrag = next((e for e in fall["kanaele"]["bedeutung"]["eintraege"] if e["id"] == "nasa-llis-812"), None)
        assert bed_eintrag is not None and "staerke" in bed_eintrag, \
            "Rang-1-Treffer im Bedeutungskanal muss eine Cosine-Staerke tragen"
        assert -1.0 <= bed_eintrag["staerke"] <= 1.0, "Cosine-Staerke muss im gueltigen Wertebereich liegen"

    # 3c) Vergleich: Zusammenfuehrung unterschiede_A_B + rows ueber `kennung`.
    v = _vergleich_stand()
    if "error" not in v:
        assert v["n_cases"] == len(json.loads(_vergleich_neueste_datei().read_text(encoding="utf-8"))["rows"])
        for u in v["unterschiede"]:
            assert "A_antwort" in u and "B_antwort" in u

    # 3d) Fundstelle: die Bestellung der App. Laeuft auch ohne buckeberg --
    # dann ist der Bestand nicht erreichbar und JEDE Antwort lautet "weiss
    # ich nicht", was genau richtig ist. Der Negativfall ist hier der
    # eigentliche Test: nie eine Seite ohne Beleg.
    b = _quellenbestand()
    assert "quellen" in b and "mit_fundstelle" in b
    leer_f = _fundstelle_stand("", "")
    assert leer_f["belegt"] is False and leer_f["seite"] is None and leer_f["grund"], \
        "Negativfall: ohne Angabe darf keine Fundstelle behauptet werden"
    unfug = _fundstelle_stand("", "Kernfusionsreaktor im Kellergeschoss der Anlage")
    assert unfug["belegt"] is False and unfug["seite"] is None, \
        "Negativfall: ein Wortlaut ohne Beleg darf keine Seite bekommen"
    if b["erreichbar"] and b["nummern_mit_fundstelle"]:
        nr = b["nummern_mit_fundstelle"][0]
        treffer = _fundstelle_stand(nr, "")
        assert treffer["belegt"] and treffer["markierbar"], f"Quelle {nr} muss aufloesen"
        assert Path(treffer["absolut"]).is_file(), "aufgeloeste Datei muss existieren"

    # 3e) Quellenliste: Der Browser der App haengt daran.
    ql = _quellenliste()["zeilen"]
    if b["erreichbar"]:
        assert ql, "Quellenliste darf bei erreichbarem Korpus nicht leer sein"
        assert all(z["nummer"].isdigit() for z in ql), "Verwaltungszeile durchgerutscht"
        # Die Freigabe wird NICHT erfunden -- fehlt sie im Verzeichnis, bleibt
        # sie leer, und die App liest daraus "gesperrt". Sichere Richtung.
        assert all("freigabe" in z for z in ql)
        assert sum(1 for z in ql if z["markierbar"]) == b["mit_fundstelle"], \
            "markierbar in der Liste muss zum gezaehlten Bestand passen"

    print("Selbsttest gruen: Gesamtstand read-only unveraendert, "
          "Siegbedingung/Nachtschicht-Rundlauf inkl. Negativfall bestanden, "
          "Fundstelle schweigt ohne Beleg.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
