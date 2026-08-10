#!/usr/bin/env python3
"""Werkzeugabdeckung -- prueft JEDES Werkzeug in knowledge_mcp_server.TOOLS
gegen eine Wegwerf-DB, drei Faelle je Werkzeug (Auftrag 2026-08-07):

  a) gueltiger Aufruf     -> erwartetes Ergebnis (kein Fehler)
  b) Pflichtangabe fehlt  -> sprechender Fehler, KEIN roher KeyError/Traceback
  c) unsinnige Angabe     -> sprechender Fehler, KEIN stiller Erfolg

Werkzeugliste kommt aus server.TOOLS (dem echten Register), nicht aus einer
eigenen Kopie -- ein neues Werkzeug taucht automatisch auf und wird, falls
CASES keinen Eintrag dafuer hat, als LUECKE gemeldet statt stillschweigend
uebersprungen.

Aufruf: .venv/bin/python shared-knowledge/schreibpruefstand/werkzeugabdeckung.py
Exit-Code != 0, wenn ein Fall b)/c) einen rohen Fehler liefert oder eine
Luecke gefunden wurde.
"""

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
import os
import re
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = HIER.parent

# Wegwerf-DB, VOR dem Import gesetzt -- DB_PATH wird beim Modul-Import einmal
# fest aus BEGOD_KNOWLEDGE_DB gelesen (siehe Kopf von knowledge_mcp_server.py).
_TMP_DIR = tempfile.mkdtemp(prefix="werkzeugabdeckung-")
os.environ["BEGOD_KNOWLEDGE_DB"] = str(Path(_TMP_DIR) / "wegwerf.db")

sys.path.insert(0, str(SHARED_KNOWLEDGE))
import knowledge_mcp_server as server  # noqa: E402

TESTSITZUNG = "werkzeugabdeckung-testlauf"
TESTMODELL = "werkzeugabdeckung-script"
TESTAKTEUR = "werkzeugabdeckung"
QUELLE = f"erzeugt aus shared-knowledge/schreibpruefstand/werkzeugabdeckung.py (Testlauf {server.now_iso()})"


def rufe(name: str, args: dict) -> tuple[dict, dict | str, bool]:
    """Ruft ein Werkzeug wie ein echter MCP-Client (ueber handle_request,
    JSON-RPC tools/call) -- nicht den Handler direkt, damit derselbe Pfad
    geprueft wird, den ein Aufrufer tatsaechlich nimmt."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
           "params": {"name": name, "arguments": args}}
    resp = server.handle_request(req)
    result = resp.get("result", {})
    flagged = bool(result.get("isError"))
    raw_text = result.get("content", [{}])[0].get("text", "")
    try:
        content = json.loads(raw_text)
    except json.JSONDecodeError:
        content = raw_text
    if isinstance(content, dict) and "error" in content:
        flagged = True
    return resp, content, flagged


_ROH_MARKER = (
    "Traceback (most recent", "sqlite3.OperationalError", "sqlite3.IntegrityError",
    "sqlite3.ProgrammingError", "<class '", "object at 0x", "NoneType",
)


def wirkt_roh(content: dict | str) -> bool:
    """Erkennt einen rohen Python-Fehler statt einer sprechenden Meldung:
    entweder der nackte KeyError-Text ('schluessel') oder eine erkennbare
    Stapelspur/Exception-Signatur irgendwo im Text."""
    text = content.get("error") if isinstance(content, dict) and "error" in content else content
    text = str(text)
    if re.fullmatch(r"'[^']*'", text):
        return True
    return any(m in text for m in _ROH_MARKER)


# ─── Testdaten anlegen (eine kleine, wegwerfbare Baumstruktur) ──────────────

def _identitaet(args: dict) -> dict:
    return {**args, "session": TESTSITZUNG, "model": TESTMODELL, "actor": TESTAKTEUR}


def bootstrap() -> dict:
    _, a, flagged = rufe("knowledge_add", _identitaet({
        "parent_path": "/", "title": "Pruefstand Testknoten A",
        "summary": "Testknoten A fuer Werkzeugabdeckungspruefung.",
        "source": QUELLE, "anlass": "skript",
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Knoten A): {a}")
    path_a = a["path"]

    _, b, flagged = rufe("knowledge_add", _identitaet({
        "parent_path": path_a, "title": "Pruefstand Testknoten B",
        "summary": "Testknoten B fuer Relations-/Update-Tests.",
        "source": QUELLE, "anlass": "skript",
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Knoten B): {b}")
    path_b = b["path"]

    _, e, flagged = rufe("knowledge_add", _identitaet({
        "parent_path": path_a, "title": "Pruefstand Testknoten E (zurueckgezogen)",
        "summary": "Wird sofort zurueckgezogen, fuer den freigeben-Test.",
        "source": QUELLE, "anlass": "skript",
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Knoten E): {e}")
    path_e = e["path"]
    _, zr, flagged = rufe("knowledge_zurueckziehen", _identitaet(
        {"path": path_e, "grund": "Testrueckzug fuer freigeben-Testfall."}))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Knoten E zurueckziehen): {zr}")

    _, f_, flagged = rufe("knowledge_add", _identitaet({
        "parent_path": path_a, "title": "Pruefstand Testknoten F (fuer relation_remove)",
        "summary": "Wird fuer eine wegwerfbare Kante gebraucht.",
        "source": QUELLE, "anlass": "skript",
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Knoten F): {f_}")
    path_f = f_["path"]
    _, rel_wegwerf, flagged = rufe("knowledge_relation_add", _identitaet({
        "source_node": path_a, "target_node": path_f, "relation_type": "references",
        "evidence": "Wegwerfkante fuer relation_remove-Testfall.", "source": QUELLE,
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Wegwerfkante): {rel_wegwerf}")
    relation_id_wegwerf = rel_wegwerf["id"]

    _, l_, flagged = rufe("lesson_record", _identitaet({
        "type": "insight", "description": "Testlehre fuer Werkzeugabdeckungspruefung (wegwerfbar).",
        "anlass": "skript",
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Lehre): {l_}")
    lesson_id = l_["id"]

    _, rel, flagged = rufe("knowledge_relation_add", _identitaet({
        "source_node": path_a, "target_node": path_b, "relation_type": "references",
        "evidence": "Testkante fuer Werkzeugabdeckungspruefung.", "source": QUELLE,
    }))
    if flagged:
        sys.exit(f"Bootstrap fehlgeschlagen (Kante): {rel}")

    return {
        "path_a": path_a, "path_b": path_b, "path_e": path_e, "path_f": path_f,
        "lesson_id": lesson_id, "relation_id": rel["id"],
        "relation_id_wegwerf": relation_id_wegwerf,
    }


# ─── Faelle je Werkzeug ──────────────────────────────────────────────────
# Wert je Fall: dict (statische Argumente), Aufrufbares ctx->dict (braucht
# Bootstrap-Daten), oder None ("kein Pflichtfeld"/"keine Eingabeparameter" --
# der Fall entfaellt strukturell, ist aber KEINE Luecke).
# "erwartung" steuert Fall c): "fehler" (Vorgabe, erwartet sprechenden
# Fehler) oder "gnaedig" (ein leeres/transparentes Ergebnis auf Unsinn ist
# hier fachlich richtig, z.B. Browse eines nicht vorhandenen Astes).

CASES = {
    "knowledge_browse": {
        "valid": {"path": "/"},
        "missing": None,
        "nonsense": {"path": "/nichts-das-es-gibt-xyz"},
        "erwartung_c": "gnaedig",
    },
    "knowledge_read": {
        "valid": lambda ctx: {"node_id": ctx["path_a"]},
        "missing": {},
        "nonsense": {"node_id": "nichts-das-es-gibt-xyz"},
    },
    "knowledge_search": {
        "valid": {"query": "Pruefstand"},
        "missing": {},
        "nonsense": {"query": "Pruefstand", "max_results": "viele"},
    },
    "knowledge_add": {
        "valid": lambda ctx: {"parent_path": ctx["path_a"], "title": "Pruefstand Kind C",
                               "summary": "Testkind C.", "source": QUELLE, "anlass": "skript"},
        "missing": {"title": "x", "summary": "y", "source": "z"},  # parent_path fehlt
        "nonsense": {"parent_path": "/nichts-das-es-gibt", "title": "Unsinn",
                     "summary": "Unsinn", "source": QUELLE},
    },
    "knowledge_update": {
        "valid": lambda ctx: {"node_id": ctx["path_b"], "summary": "Aktualisierte Zusammenfassung B."},
        "missing": {},
        "nonsense": {"node_id": "nichts-das-es-gibt-xyz", "summary": "x"},
    },
    "knowledge_zurueckziehen": {
        # eigener Wegwerfknoten pro Lauf, damit der Rueckzug niemanden stoert
        "valid": lambda ctx: {
            "path": rufe("knowledge_add", _identitaet({
                "parent_path": ctx["path_a"], "title": f"Wegwerfknoten zurueckziehen {id(ctx)}",
                "summary": "Wegwerfbar.", "source": QUELLE, "anlass": "skript",
            }))[1]["path"],
            "grund": "Testrueckzug fuer Werkzeugabdeckungspruefung.",
        },
        "missing": lambda ctx: {"path": ctx["path_b"]},  # grund fehlt
        "nonsense": {"path": "nichts-das-es-gibt-xyz", "grund": "Testrueckzug"},
    },
    "knowledge_freigeben": {
        "valid": lambda ctx: {"path": ctx["path_e"]},  # war in bootstrap() zurueckgezogen
        "missing": {},  # weder node_id noch path
        "nonsense": {"path": "nichts-das-es-gibt-xyz"},
    },
    "knowledge_relation_add": {
        "valid": lambda ctx: {
            "source_node": ctx["path_a"],
            "target_node": rufe("knowledge_add", _identitaet({
                "parent_path": ctx["path_a"], "title": f"Wegwerfknoten Kante {id(ctx)}",
                "summary": "Wegwerfbar.", "source": QUELLE, "anlass": "skript",
            }))[1]["path"],
            "relation_type": "references", "evidence": "Testkante.", "source": QUELLE,
        },
        "missing": {"target_node": "x", "relation_type": "references", "evidence": "y"},  # source_node fehlt
        "nonsense": lambda ctx: {"source_node": ctx["path_a"], "target_node": "nichts-das-es-gibt-xyz",
                                  "relation_type": "references", "evidence": "y"},
    },
    "knowledge_relation_list": {
        "valid": {},
        "missing": None,
        "nonsense": {"node": "nichts-das-es-gibt-xyz"},
    },
    "knowledge_relation_update": {
        "valid": lambda ctx: {"relation_id": ctx["relation_id"], "evidence": "Aktualisierte Testkante."},
        "missing": {},
        "nonsense": {"relation_id": "nichts-das-es-gibt-xyz", "evidence": "x"},
    },
    "knowledge_relation_remove": {
        "valid": lambda ctx: {"relation_id": ctx["relation_id_wegwerf"]},
        "missing": {},
        "nonsense": {"relation_id": "nichts-das-es-gibt-xyz"},
    },
    "lesson_record": {
        "valid": {"type": "insight", "description": "Testlehre valid case.", "anlass": "skript"},
        "missing": {"description": "x"},  # type fehlt
        "nonsense": {"type": "voellig_unbekannter_typ", "description": "Unsinnstyp-Testlehre."},
    },
    "lesson_update": {
        "valid": lambda ctx: {"lesson_id": ctx["lesson_id"], "resolution": "Testresolution aktualisiert."},
        "missing": {},
        "nonsense": {"lesson_id": "nichts-das-es-gibt-xyz", "resolution": "x"},
    },
    "lesson_query": {
        "valid": {"type": "insight"},
        "missing": None,
        "nonsense": {"status": "voellig_unbekannt"},
        "erwartung_c": "gnaedig",
    },
    "knowledge_sitzung": {
        "valid": {"session": TESTSITZUNG},
        "missing": {},
        "nonsense": {"session": "nichts-das-es-gibt-session"},
        "erwartung_c": "gnaedig",
    },
    "knowledge_modell": {
        "valid": {"model": TESTMODELL},
        "missing": {},
        "nonsense": {"model": "nichts-das-es-gibt-modell"},
        "erwartung_c": "gnaedig",
    },
    "knowledge_stats": {
        "valid": {},
        "missing": None,
        "nonsense": None,
    },
    "knowledge_trust_score": {
        "valid": lambda ctx: {"kind": "node", "ref": ctx["path_a"]},
        "missing": {"kind": "node"},
        "nonsense": {"kind": "node", "ref": "nichts-das-es-gibt-xyz"},
        # exists:false ist die sprechende, transparente Antwort auf Unsinn --
        # kein stiller Erfolg (score wird trotzdem geliefert, aber markiert).
        "nonsense_ok": lambda content: isinstance(content, dict) and content.get("exists") is False,
    },
    "kurator_lauf": {
        "valid": {"scharf": False},
        "missing": None,
        # bool() akzeptiert jeden Wahrheitswert (dokumentierter Kompromiss,
        # keine Typpruefung) -- ein int statt bool laeuft einfach durch.
        "nonsense": {"scharf": 123},
        "erwartung_c": "gnaedig",
    },
}


def bewerte(zweig: str, name: str, content, flagged: bool, erwartung: str = "fehler",
            gnaedig_ok=None) -> tuple[bool, str]:
    roh = wirkt_roh(content) if flagged else False
    if zweig == "a":  # gueltig -> muss durchgehen
        if flagged:
            return False, f"gueltiger Aufruf schlug fehl: {content}"
        return True, "ok"
    if zweig == "b":  # Pflichtangabe fehlt -> muss sprechend scheitern
        if not flagged:
            return False, f"fehlende Pflichtangabe wurde still angenommen: {content}"
        if roh:
            return False, f"roher Fehler statt sprechender Meldung: {content}"
        return True, "ok (sprechend abgelehnt)"
    # zweig == "c": unsinnige Angabe
    if flagged:
        if roh:
            return False, f"roher Fehler statt sprechender Meldung: {content}"
        return True, "ok (sprechend abgelehnt)"
    # kein Fehler signalisiert -- nur zulaessig, wenn als "gnaedig" erwartet
    # oder eine werkzeugspezifische Transparenzpruefung greift
    if erwartung == "gnaedig":
        return True, f"ok (gnaedig: leeres/transparentes Ergebnis, kein Fehler noetig) -- {content}"
    if gnaedig_ok is not None and gnaedig_ok(content):
        return True, f"ok (transparent, kein stiller Erfolg) -- {content}"
    return False, f"stiller Erfolg auf unsinnige Angabe: {content}"


def loese(wert, ctx):
    if callable(wert):
        return wert(ctx)
    return wert


def hauptlauf() -> int:
    ctx = bootstrap()
    print(f"Wegwerf-DB: {os.environ['BEGOD_KNOWLEDGE_DB']}")
    print(f"Register meldet {len(server.TOOLS)} Werkzeuge.\n")

    zeilen = []
    fehler_zaehler = 0
    luecken = []
    sauber, unsauber = [], []

    for name in server.TOOLS:  # Reihenfolge/Menge kommt aus dem Register
        if name not in CASES:
            luecken.append(name)
            print(f"LUECKE  {name}: kein Testfall im Skript hinterlegt")
            fehler_zaehler += 1
            continue

        spec = CASES[name]
        tool_ok = True
        for zweig, schluessel in (("a", "valid"), ("b", "missing"), ("c", "nonsense")):
            wert = spec.get(schluessel)
            if wert is None:
                print(f"{name:28s} [{zweig}] entfaellt (kein Pflichtfeld / keine Eingabeparameter)")
                continue
            args = loese(wert, ctx)
            _, content, flagged = rufe(name, args)
            ok, begruendung = bewerte(
                zweig, name, content, flagged,
                erwartung=spec.get("erwartung_c", "fehler") if zweig == "c" else "fehler",
                gnaedig_ok=spec.get("nonsense_ok") if zweig == "c" else None,
            )
            status = "PASS" if ok else "FAIL"
            print(f"{name:28s} [{zweig}] {status}: {begruendung}")
            zeilen.append((name, zweig, ok, begruendung))
            if not ok:
                fehler_zaehler += 1
                tool_ok = False
        (sauber if tool_ok else unsauber).append(name)

    print("\n─── Selbstprobe: bewerte() muss einen absichtlichen rohen Fehler erkennen ───")
    def _knall(_args):
        return _args["gibt_es_nicht"]
    server.TOOLS["_selbsttest_roh"] = {
        "description": "nur fuer die Selbstprobe", "inputSchema": {"type": "object", "properties": {}},
        "handler": _knall,
    }
    try:
        _, boom_content, boom_flagged = rufe("_selbsttest_roh", {})
        ok, begruendung = bewerte("b", "_selbsttest_roh", boom_content, boom_flagged)
        if ok:
            print(f"SELBSTPROBE FAIL: roher KeyError wurde NICHT erkannt ({begruendung})")
            fehler_zaehler += 1
        else:
            print(f"SELBSTPROBE PASS: roher KeyError korrekt als Fehlschlag erkannt ({begruendung})")
    finally:
        del server.TOOLS["_selbsttest_roh"]

    print(f"\n─── Zusammenfassung ───")
    print(f"Werkzeuge im Register: {len(server.TOOLS)}")
    print(f"Davon ohne Testfall (LUECKE): {len(luecken)} -- {luecken}")
    print(f"Sauber (alle Faelle bestanden): {len(sauber)} -- {sauber}")
    print(f"Mit rohem Fehler/Luecke (mind. ein Fall FAIL): {len(unsauber)} -- {unsauber}")
    print(f"Faelle gesamt gewertet: {len(zeilen)}, davon fehlgeschlagen: {sum(1 for *_, ok, _ in zeilen if not ok)}")
    print(f"Gesamtfehler (Faelle + Luecken): {fehler_zaehler}")

    return 1 if fehler_zaehler else 0


if __name__ == "__main__":
    sys.exit(hauptlauf())
