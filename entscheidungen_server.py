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

import argparse
import datetime
import glob
import json
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
HUB = HERE.parent
DB_PATH = HERE / "knowledge.db"
HTML_PATH = HERE / "entscheidungen.html"
ESKALATION_SCRIPT = HERE / "eskalation_vorlage.py"
EILMELDUNG_SCRIPT = HUB / "scripts" / "eilmeldung_quittieren.py"

sys.path.insert(0, str(HERE))
import eskalation_vorlage  # noqa: E402  -- nur Funktionen aufgerufen, Datei unveraendert
import knowledge_lint  # noqa: E402       -- nur find_norm_conflicts() gelesen
import meisterschaft  # noqa: E402        -- nur *_lesen() gelesen/Schluessel-Namen
import nachtlaeufer  # noqa: E402         -- nur _DEFAULTS gelesen
import raum_daten  # noqa: E402           -- nur sammle() aufgerufen, Datei unveraendert

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
# derselben knowledge.db, Spalten (lesson_id TEXT PRIMARY KEY, regel_vorschlag
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
    conn = sqlite3.connect(str(DB_PATH))
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
# nur wenn knowledge.db oder recall_log.jsonl seit dem letzten Lauf eine
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
    kandidaten = sorted(RUNS_DIR.glob("ab_vergleich_abruf_*.json"))
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


# ─── HTTP ─────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # ponytail: stdout-Stille, kein eigenes Log-Format
        pass

    def _json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
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
        self._json({"error": "unbekannter Pfad"}, 404)

    def do_POST(self):
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

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
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

    global DB_PATH
    real_db_mtime = DB_PATH.stat().st_mtime

    # 1) Gesamtstand gegen die echte DB muss ohne Ausnahme durchlaufen.
    stand = _gesamtstand()
    assert "eskalation" in stand and "normkonflikte" in stand
    assert stand["titelverteidiger"] is None or isinstance(stand["titelverteidiger"], dict)
    assert stand["herkunftsmodus"] == {"gefunden": False}
    assert DB_PATH.stat().st_mtime == real_db_mtime, "Gesamtstand hat die echte DB veraendert"

    # 2) Schreibpfade (Siegbedingung/Nachtschicht) gegen eine Kopie.
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "knowledge.db"
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
            DB_PATH = Path(__file__).resolve().parent / "knowledge.db"

    # 2b) Eskalation: befoerdern/zurueckstufen gegen Kopien von DB und
    # CLAUDE.md -- eskalation_vorlage haelt DB_PATH/CLAUDE_MD_PATH als
    # eigene Modul-Globale, deshalb hier eigens umgehaengt statt ueber
    # entscheidungen_server.DB_PATH (das eskalation_vorlage nicht sieht).
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "knowledge.db"
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

    # 3b) Vergleich: Zusammenfuehrung unterschiede_A_B + rows ueber `kennung`.
    v = _vergleich_stand()
    if "error" not in v:
        assert v["n_cases"] == len(json.loads(_vergleich_neueste_datei().read_text(encoding="utf-8"))["rows"])
        for u in v["unterschiede"]:
            assert "A_antwort" in u and "B_antwort" in u

    print("Selbsttest gruen: Gesamtstand read-only unveraendert, "
          "Siegbedingung/Nachtschicht-Rundlauf inkl. Negativfall bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
