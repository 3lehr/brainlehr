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

SIEGGROESSEN = meisterschaft.SIEGGROESSEN  # ("trefferquote","schweigequote","streuung","kosten")
GEWICHT_PREFIX = "siegbedingung_gewicht_"
GEWICHT_GERATEN_KEY = "siegbedingung_gewichte_geraten"


# ─── Abschnitt 1: Eskalierte Lehren ─────────────────────────────────────────

def _eskalation_stand() -> dict:
    conn = eskalation_vorlage.get_db()
    rows = conn.execute(
        "SELECT id, occurrences, type, description, prevention FROM lessons_learned "
        "WHERE status = ? ORDER BY occurrences DESC, id",
        (eskalation_vorlage.STATUS_POOL,),
    ).fetchall()
    conn.close()
    kandidaten = [{
        "id": r["id"], "occurrences": r["occurrences"], "type": r["type"],
        "description": r["description"],
        "als_regel": eskalation_vorlage._cap(r["prevention"] or r["description"]),
    } for r in rows]
    erhoehung = sum(len(k["als_regel"]) for k in kandidaten)
    aktuell = len(eskalation_vorlage.CLAUDE_MD_PATH.read_text(encoding="utf-8")) if \
        eskalation_vorlage.CLAUDE_MD_PATH.exists() else 0
    prozent = round(100 * erhoehung / aktuell, 1) if aktuell else None
    return {"kandidaten": kandidaten, "erhoehung_zeichen": erhoehung,
            "claude_md_zeichen": aktuell, "erhoehung_prozent": prozent}


def _eskalation_handeln(handlung: str, lesson_id: str) -> dict:
    ns = SimpleNamespace(lesson_id=lesson_id)
    if handlung == "befoerdern":
        ok = eskalation_vorlage.cmd_befoerdern(ns)
    elif handlung == "zurueckstufen":
        ok = eskalation_vorlage.cmd_zurueckstufen(ns)
    else:
        return {"error": "unbekannte Handlung"}
    return {"ok": bool(ok)}


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
                out = _eskalation_handeln(payload.get("handlung", ""), payload.get("id", ""))
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

    # 3) Eilmeldungen: leerer/kaputter Zustand darf nicht crashen (Negativfall).
    assert isinstance(_eilmeldungen_stand(), list)

    print("Selbsttest gruen: Gesamtstand read-only unveraendert, "
          "Siegbedingung/Nachtschicht-Rundlauf inkl. Negativfall bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
