"""Wiedervorspielen aufgezeichneter Anfragen gegen eine eingefrorene
knowledge.db-Momentaufnahme (Auftrag 2026-08-08, Teil 3, siehe
knowledge_db_snapshot.py fuer die Momentaufnahme selbst).

Drei Auswertungen, alle OHNE bekannte richtige Antwort -- KEIN Modell
bewertet hier etwas (VERBOT laut Auftrag):

  Stabilitaet     dieselbe Anfrage zweimal gegen denselben Stand -> dasselbe Ergebnis?
  Schweigequote   wie oft bleibt der Abruf stumm (kein Node, keine Lehre)?
  Unterschied     wo liefern zwei Einstellungen (Parameter-Overrides) Verschiedenes?

Nutzt scripts/knowledge_recall_hook.py::query() direkt, mit embed_fn fest auf
"kein Vektor" -- KEIN Ollama-Aufruf, reiner Stichwort-Kanal, deterministisch
(die zwei Kanaele mit echtem Ollama waeren bei Wiederholung nicht
vergleichbar rein aus Netzwerk-Varianz, unabhaengig vom eigentlichen Befund).

Aeltere recall_log.jsonl-Zeilen ohne 'prompt' (vor Auftrag 2026-08-08) sind
NICHT wiederholbar -- werden gezaehlt, nicht stillschweigend uebergangen.

Zweite Quelle: shared-knowledge/zero_hit_log.jsonl (geschrieben von
knowledge_mcp_server.py::_log_zero_hit(), NUR gelesen, nie veraendert --
GRENZE laut Auftrag). Dessen 'query'-Feld war schon VOR diesem Auftrag
wiederholbar (der Fehlbestand, den Teil 1 fuer recall_log behebt, betraf nur
Treffer-Zeilen dort). Beide Quellen zusammen ergeben die Anfrage-Menge, auf
die sich "650 von 1326" im Auftrag bezieht. WICHTIGER VORBEHALT: zero_hit_log
stammt aus dem MCP-Suchwerkzeug (knowledge_search), das eine ANDERE
Retrieval-Funktion nutzt als hook.query() (dieses Skript ruft ausschliesslich
hook.query()) -- eine wiedervorgespielte zero_hit_log-Zeile zeigt also, was
der RECALL-HOOK-Pfad heute liefern wuerde, nicht zwingend, was das
MCP-Werkzeug damals lieferte. Jede Ausgabezeile traegt 'quelle' dafuer.

Aufruf: python3 knowledge_recall_replay.py <snapshot.db> [--vergleich SCHLUESSEL=WERT]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
HUB = SHARED_KNOWLEDGE.parent
RECALL_LOG = SHARED_KNOWLEDGE / "recall_log.jsonl"
ZERO_HIT_LOG = SHARED_KNOWLEDGE / "zero_hit_log.jsonl"

if str(HUB / "scripts") not in sys.path:
    sys.path.insert(0, str(HUB / "scripts"))
import knowledge_recall_hook as hook  # noqa: E402

_KEIN_MODELL = lambda *a, **k: None  # kein Ollama -- VERBOT: kein Modellaufruf


def _lies_jsonl(log_path: Path) -> list[dict]:
    """Rohe Zeilen einer JSONL-Datei, kaputte Zeilen uebersprungen (nicht
    gezaehlt -- dasselbe Verhaltensmuster wie hook.report()). Datei fehlt ->
    leere Liste, kein Fehler."""
    zeilen = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    zeilen.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return zeilen


def _mit_anfrage(recall_log_path: Path | None = None,
                  zero_hit_log_path: Path | None = None) -> tuple[list[dict], int]:
    """Vereinigt beide Quellen (s. Moduldoc) auf eine gemeinsame Form
    {'prompt', 'cwd', 'quelle'}. Rueckgabe: (Zeilen MIT Anfragetext, Anzahl
    recall_log-Zeilen OHNE -- das sind die 'nicht wiederholbaren', gezaehlt
    statt weggelassen). zero_hit_log-Zeilen haben IMMER einen Anfragetext
    (Schreibpfad erzwingt das), zaehlen also nie zu 'ohne'."""
    mit, ohne = [], 0
    for e in _lies_jsonl(recall_log_path or RECALL_LOG):
        if e.get("prompt"):
            mit.append({"prompt": e["prompt"], "cwd": e.get("cwd"), "quelle": "recall_log"})
        else:
            ohne += 1
    for e in _lies_jsonl(zero_hit_log_path or ZERO_HIT_LOG):
        if e.get("query"):
            mit.append({"prompt": e["query"], "cwd": e.get("cwd"), "quelle": "zero_hit_log"})
    return mit, ohne


def _signatur(nodes: list, lessons: list) -> tuple:
    """Vergleichbare Form eines Abrufergebnisses -- Reihenfolge zaehlt nicht
    (bei Gleichstand/Explore kann sie variieren, ohne dass sich die Menge der
    eingespielten Treffer aendert)."""
    return (
        tuple(sorted(n["path"] for n in nodes)),
        tuple(sorted(l["id"] for l in lessons)),
    )


def _replay(prompt: str, cwd: str | None, snapshot_db: str,
            overrides: dict | None = None) -> tuple[list, list]:
    """Ein Abruf gegen die Momentaufnahme -- hook.DB (Modul-Global) fuer die
    Dauer des Aufrufs auf die Momentaufnahme umgebogen, wie hook.selftest()
    es fuer die eigene Test-DB macht, danach garantiert zurueckgesetzt.
    rand bleibt Vorgabe (echter random.random(), kein fester Wert) -- eine
    fest verdrahtete Wuerfelzahl wuerde die Stabilitaetsmessung selbst
    unwirksam machen (siehe Stabilitaets-Kommentar in auswertung())."""
    saved_db = hook.DB
    saved = {k: getattr(hook, k) for k in (overrides or {})}
    for k, v in (overrides or {}).items():
        setattr(hook, k, v)
    hook.DB = snapshot_db
    try:
        kws = hook.keywords(prompt)
        if len(kws) < hook.MIN_HITS:
            return [], []
        return hook.query(kws, cwd=cwd, embed_fn=_KEIN_MODELL)
    finally:
        hook.DB = saved_db
        for k, v in saved.items():
            setattr(hook, k, v)


def auswertung(snapshot_db: str, recall_log_path: Path | None = None,
               zero_hit_log_path: Path | None = None,
               vergleich_overrides: dict | None = None) -> dict:
    """Fuehrt die drei Auswertungen ueber alle wiederholbaren Zeilen (beide
    Quellen, s. Moduldoc). Jede Anfrage wird zweimal abgerufen (Stabilitaet)
    und, wenn vergleich_overrides gesetzt ist, ein drittes Mal mit den
    ueberschriebenen Parametern (Unterschied). rand bleibt bei jedem der drei
    Aufrufe die echte Zufallsquelle -- zwei Ergebnisse aus demselben Lauf
    koennen also allein durch EXPLORE_RATE auseinanderlaufen, und genau DAS
    ist die Stabilitaetsmessung, kein Testartefakt."""
    mit, ohne = _mit_anfrage(recall_log_path, zero_hit_log_path)
    stumm = stabil = instabil = unterschiedlich = 0
    for e in mit:
        prompt, cwd = e["prompt"], e.get("cwd")
        n1, l1 = _replay(prompt, cwd, snapshot_db)
        n2, l2 = _replay(prompt, cwd, snapshot_db)
        sig1, sig2 = _signatur(n1, l1), _signatur(n2, l2)
        if not n1 and not l1:
            stumm += 1
        if sig1 == sig2:
            stabil += 1
        else:
            instabil += 1
        if vergleich_overrides:
            n3, l3 = _replay(prompt, cwd, snapshot_db, vergleich_overrides)
            if sig1 != _signatur(n3, l3):
                unterschiedlich += 1

    n = len(mit)
    return {
        "snapshot": snapshot_db,
        "gesamt_zeilen": n + ohne,
        "nicht_wiederholbar_ohne_anfrage": ohne,
        "wiederholbar_mit_anfrage": n,
        "schweigequote": f"{stumm}/{n}",
        "stabil": stabil,
        "instabil": instabil,
        "vergleich_overrides": vergleich_overrides,
        "unterschied_zu_vergleich": f"{unterschiedlich}/{n}" if vergleich_overrides else None,
    }


def demo() -> None:
    """Selbsttest: eigene Momentaufnahme mit bekanntem Bestand (ein Knoten,
    dessen Titel+Summary alle vier Anfrage-Woerter woertlich traegt -- kein
    Grenzfall bei MIN_HITS), eigenes recall_log.jsonl mit einer Zeile MIT und
    einer Zeile OHNE 'prompt'. Prueft alle drei Kennzahlen plus die
    Nicht-wiederholbar-Zaehlung."""
    import sqlite3
    import tempfile

    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "snap.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, "
            "content, level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/test/x', 'shared', "
            "'Quartalsbericht Dachrinne', 'Fahrradkorb Regenschirm Testeintrag', "
            "NULL, 0, 'test', 'keine_norm', 'skript:knowledge_recall_replay.py', 'Testvorrichtung')"
        )
        conn.commit()
        conn.close()

        log_path = Path(td) / "recall_log.jsonl"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"prompt": "quartalsbericht dachrinne fahrradkorb regenschirm",
                                 "cwd": None, "nodes": ["/test/x"], "lessons": []}) + "\n")
            f.write(json.dumps({"nodes": ["/alt"], "lessons": []}) + "\n")  # Altzeile ohne prompt
        # Leere zero_hit_log-Fixtur -- sonst griffe die reale Datei (Vorgabewert
        # ZERO_HIT_LOG) und der Selbsttest waere weder isoliert noch schnell.
        zh_path = Path(td) / "zero_hit_log.jsonl"

        r = auswertung(str(db_path), log_path, zh_path)
        assert r["nicht_wiederholbar_ohne_anfrage"] == 1, r
        assert r["wiederholbar_mit_anfrage"] == 1, r
        assert r["stabil"] == 1 and r["instabil"] == 0, r
        assert r["schweigequote"] == "0/1", r
        print("  Bekannter Bestand: Zaehlung/Stabilitaet/Schweigequote ok:", r)

        # NEGATIVFALL: eine Anfrage, die im Bestand nichts trifft -> Schweigequote 1/1.
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"prompt": "voellig unbeteiligter begriff ohne jeden treffer",
                                 "cwd": None, "nodes": [], "lessons": []}) + "\n")
        r2 = auswertung(str(db_path), log_path, zh_path)
        assert r2["wiederholbar_mit_anfrage"] == 2, r2
        assert r2["schweigequote"] == "1/2", r2
        print("  Negativfall (kein Treffer im Bestand) -> Schweigequote zaehlt ihn ok:", r2)

        # Unterschied: MIN_HITS auf 99 hochgesetzt gegen die Vergleichsseite
        # findet garantiert nichts mehr -> muss sich vom Ausgangslauf unterscheiden.
        r3 = auswertung(str(db_path), log_path, zh_path, vergleich_overrides={"MIN_HITS": 99})
        assert r3["unterschied_zu_vergleich"] == "1/2", r3
        print("  Vergleich MIN_HITS=99 findet Unterschied bei der treffenden Anfrage ok:", r3)

        # Zweite Quelle: zero_hit_log traegt 'query' statt 'prompt', zaehlt aber
        # trotzdem als wiederholbar (nie 'ohne') und wird mitausgewertet.
        with open(zh_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "2026-08-07T00:00:00+02:00",
                                 "query": "quartalsbericht dachrinne fahrradkorb regenschirm",
                                 "hits": 0, "cwd": None}) + "\n")
        r4 = auswertung(str(db_path), log_path, zh_path)
        assert r4["wiederholbar_mit_anfrage"] == 3, r4  # 2 aus recall_log + 1 aus zero_hit_log
        assert r4["nicht_wiederholbar_ohne_anfrage"] == 1, r4  # unveraendert -- nur recall_log zaehlt hier
        print("  Zweite Quelle (zero_hit_log, Feld 'query') wird mitgezaehlt ok:", r4)

    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Aufruf: python3 knowledge_recall_replay.py <snapshot.db> "
              "[--vergleich SCHLUESSEL=WERT]", file=sys.stderr)
        sys.exit(1)
    vergleich = None
    if "--vergleich" in sys.argv:
        kv = sys.argv[sys.argv.index("--vergleich") + 1]
        k, v = kv.split("=", 1)
        vergleich = {k: (float(v) if "." in v else int(v))}
    print(json.dumps(auswertung(args[0], vergleich_overrides=vergleich), indent=2, ensure_ascii=False))
