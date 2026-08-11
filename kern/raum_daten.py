#!/usr/bin/env python3
"""raum_daten.py -- Datenlieferant fuer raum.html (Wissensraum-Ansicht).

Nur lesend (sqlite3 mode=ro). Liefert genau die Struktur, an der raum.html
haengt: {"punkte","spuren","gesetzt","ereignisse","varianz","unaufloesbar"}.

WARUM PCA UND NICHT t-SNE (Konsil docs/KONSIL_WISSENSRAUM_ANSICHT_2026-08-08.md):
PCA ist out-of-sample-faehig -- ein neuer Eintrag wird auf die bestehenden
Achsen projiziert, die Karte steht still. Bei t-SNE entsteht jeder Punkt nur
relativ zu allen anderen im selben Lauf; ein neuer Eintrag verschiebt das
ganze Bild, und dann ist jeder Vergleich zwischen zwei Zeitpunkten wertlos.

WARUM sklearn.decomposition.PCA statt Kovarianz von Hand: sklearn ist bereits
installiert (kein neuer Dependency-Zuwachs), und PCA(svd_solver="full") legt
intern eine SVD der zentrierten N x 1024-Matrix, nicht die 1024x1024-Kovarianz
explizit -- die Kosten haengen damit ohnehin an min(N, 1024), also an der
kleineren Seite, ohne dass wir das per Hand erzwingen muessen. Von Hand
(numpy.cov ueber 1024 Spalten -> 1024x1024-Eigenzerlegung) waere langsamer
UND fehleranfaelliger (Vorzeichen-/Skalierungs-Fallstricke), fuer denselben
Wert.

AUS NAEHE WIRD NIE EINE KANTE ERZEUGT -- gesetzt kommt nur aus
knowledge_relations (von Hand geprueft), spuren nur aus gemessener
Kookkurrenz im Abrufprotokoll (Schwelle 2, wie hebb_kanten.py).
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
import itertools
import json
import re
import sqlite3
import sys
from pathlib import Path

HERE = _w
DB_PATH = HERE / "brainlehr.db"
RECALL_LOG_PATH = HERE / "recall_log.jsonl"

_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f�]")


def _clean(s: str | None) -> str:
    """Steuerzeichen und kaputte Ersatzzeichen (U+FFFD) raus -- sonst bricht
    die JSON-Einbettung an einzelnen Bestandseintraegen."""
    return _CTRL_RE.sub("", s or "")


def _kuerzen(s: str | None, n: int = 88) -> str:
    return _clean(s)[:n]


def _erstes_segment(path: str | None) -> str:
    return (path or "").strip("/").split("/", 1)[0] if path else ""


def _projekte_erstes(raw: str | None) -> str:
    try:
        arr = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return ""
    return arr[0] if arr else ""


def _lade_punkte(conn: sqlite3.Connection) -> tuple[list[dict], list[list[float]], dict[str, int], dict[str, int]]:
    """Ein Punkt je distinktem (kind, ref_id) mit Embedding, gejoint auf
    knowledge_nodes bzw. lessons_learned. knowledge_embeddings hat den
    Primaerschluessel (kind, ref_id, project_id) -- MIN(rowid) waehlt je
    ref_id genau eine Zeile, damit keine Dubletten als Punkte auftauchen."""
    punkte: list[dict] = []
    vektoren: list[list[float]] = []
    pfad_index: dict[str, int] = {}
    lehre_index: dict[str, int] = {}

    node_rows = conn.execute(
        "SELECT n.id, n.path, n.title, n.created_at, n.norm_rang, n.zurueckgezogen, e.vector "
        "FROM knowledge_nodes n JOIN knowledge_embeddings e "
        "ON e.ref_id = n.id AND e.kind='node' AND e.rowid = "
        "(SELECT MIN(rowid) FROM knowledge_embeddings WHERE kind='node' AND ref_id=n.id)"
    ).fetchall()
    for r in node_rows:
        idx = len(punkte)
        pfad_index[r["path"]] = idx
        punkte.append({
            "k": "n", "t": _kuerzen(r["title"]), "a": _erstes_segment(r["path"]),
            "p": r["path"], "d": (r["created_at"] or "")[:10],
            "r": r["norm_rang"] or 0, "z": r["zurueckgezogen"] or 0,
            "v": [0.0, 0.0, 0.0], "h": 0,
        })
        vektoren.append(_unpack(r["vector"]))

    lesson_rows = conn.execute(
        "SELECT l.id, l.description, l.type, l.first_seen, l.severity, l.projects, "
        "l.pruefstelle, e.vector "
        "FROM lessons_learned l JOIN knowledge_embeddings e "
        "ON e.ref_id = l.id AND e.kind='lesson' AND e.rowid = "
        "(SELECT MIN(rowid) FROM knowledge_embeddings WHERE kind='lesson' AND ref_id=l.id)"
    ).fetchall()
    for r in lesson_rows:
        idx = len(punkte)
        lehre_index[r["id"]] = idx
        punkte.append({
            "k": "l", "t": _kuerzen(r["description"]), "a": "lehre/" + (r["type"] or ""),
            "p": r["id"], "d": (r["first_seen"] or "")[:10],
            "s": r["severity"] or "", "pr": _projekte_erstes(r["projects"]),
            "g": 1 if r["pruefstelle"] else 0,
            "r": 0, "z": 0, "v": [0.0, 0.0, 0.0], "h": 0,
        })
        vektoren.append(_unpack(r["vector"]))

    return punkte, vektoren, pfad_index, lehre_index


def _unpack(blob: bytes) -> list[float]:
    import struct
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _pca_koordinaten(vektoren: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    import numpy as np
    from sklearn.decomposition import PCA

    X = np.asarray(vektoren, dtype=np.float64)
    normen = np.linalg.norm(X, axis=1, keepdims=True)
    normen[normen == 0] = 1.0
    Xn = X / normen

    k = min(3, Xn.shape[0], Xn.shape[1])
    pca = PCA(n_components=k, svd_solver="full")
    koord = pca.fit_transform(Xn)
    varianz = list(pca.explained_variance_ratio_)
    if k < 3:
        koord = np.pad(koord, ((0, 0), (0, 3 - k)))
        varianz = varianz + [0.0] * (3 - k)

    spanne = np.max(np.abs(koord), axis=0)
    spanne[spanne == 0] = 1.0
    koord = koord / spanne
    return koord.tolist(), varianz


def _abrufprotokoll(pfad_index: dict[str, int], lehre_index: dict[str, int]) -> tuple[list[dict], list[dict], int, list[int]]:
    """Ein Durchlauf durch recall_log.jsonl: loest nodes (Pfade) und lessons
    (Kennungen) auf, zaehlt Treffer je Punkt, sammelt Ereignisse fuer den
    Zeitregler und Paar-Kookkurrenz fuer die Spuren-Ansicht."""
    ereignisse: list[dict] = []
    paare: dict[tuple[int, int], int] = {}
    unaufloesbar = 0
    trefferzahl = [0] * (len(pfad_index) + len(lehre_index))

    if not RECALL_LOG_PATH.exists():
        return [], [], 0, trefferzahl

    with RECALL_LOG_PATH.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            try:
                d = json.loads(zeile)
            except (TypeError, ValueError):
                continue
            idxs: set[int] = set()
            for p in d.get("nodes") or []:
                i = pfad_index.get(p)
                if i is None:
                    unaufloesbar += 1
                else:
                    idxs.add(i)
            for lid in d.get("lessons") or []:
                i = lehre_index.get(lid)
                if i is None:
                    unaufloesbar += 1
                else:
                    idxs.add(i)
            for i in idxs:
                trefferzahl[i] += 1
            if idxs:
                ereignisse.append({"t": (d.get("ts") or "")[:16], "n": sorted(idxs)})
            for a, b in itertools.combinations(sorted(idxs), 2):
                paare[(a, b)] = paare.get((a, b), 0) + 1

    spuren = [{"a": a, "b": b, "w": w} for (a, b), w in paare.items() if w >= 2]
    return ereignisse, spuren, unaufloesbar, trefferzahl


def _gesetzte_beziehungen(conn: sqlite3.Connection, pfad_index: dict[str, int]) -> list[dict]:
    """Nur gesetzte Beziehungen, deren beide Enden im aktuellen Bestand
    auffindbar sind -- kein Naehe-Ersatz, nie erzeugt aus PCA-Distanz."""
    out = []
    for r in conn.execute("SELECT source_path, target_path FROM knowledge_relations"):
        a = pfad_index.get(r["source_path"])
        b = pfad_index.get(r["target_path"])
        if a is not None and b is not None:
            out.append({"a": a, "b": b})
    return out


def sammle() -> dict:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        punkte, vektoren, pfad_index, lehre_index = _lade_punkte(conn)
        if vektoren:
            koord, varianz = _pca_koordinaten(vektoren)
            for i, k in enumerate(koord):
                punkte[i]["v"] = k
        else:
            varianz = [0.0, 0.0, 0.0]

        ereignisse, spuren, unaufloesbar, trefferzahl = _abrufprotokoll(pfad_index, lehre_index)
        for i, h in enumerate(trefferzahl):
            punkte[i]["h"] = h

        gesetzt = _gesetzte_beziehungen(conn, pfad_index)

        return {
            "punkte": punkte, "spuren": spuren, "gesetzt": gesetzt,
            "ereignisse": ereignisse, "varianz": varianz, "unaufloesbar": unaufloesbar,
        }
    finally:
        conn.close()


def _selftest() -> int:
    import shutil
    import struct
    import tempfile

    global DB_PATH, RECALL_LOG_PATH
    real_db_size = DB_PATH.stat().st_size
    real_db_mtime = DB_PATH.stat().st_mtime

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db = tmp / "brainlehr.db"
        DB_PATH = db
        RECALL_LOG_PATH = tmp / "recall_log.jsonl"

        conn = sqlite3.connect(str(db))
        conn.executescript(
            "CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, path TEXT, title TEXT, "
            "created_at TEXT, norm_rang INTEGER, zurueckgezogen INTEGER);"
            "CREATE TABLE lessons_learned (id TEXT PRIMARY KEY, description TEXT, type TEXT, "
            "first_seen TEXT, severity TEXT, projects TEXT, pruefstelle TEXT);"
            "CREATE TABLE knowledge_embeddings (kind TEXT, ref_id TEXT, project_id TEXT, "
            "vector BLOB);"
            "CREATE TABLE knowledge_relations (source_path TEXT, target_path TEXT);"
        )

        def vec(seed: int) -> bytes:
            vals = [(seed * 7 + i) % 11 - 5.0 for i in range(8)]
            return struct.pack(f"<{len(vals)}f", *vals)

        nodes = [
            ("n1", "/apps/a", "Knoten A", "2026-08-01T00:00:00+00:00", 0, 0),
            ("n2", "/apps/b", "Knoten B", "2026-08-01T00:00:00+00:00", 0, 0),
            ("n3", "/apps/tot", "Toter Pfad (wird nicht mehr referenziert)", "2026-08-01T00:00:00+00:00", 0, 0),
        ]
        lessons = [
            ("L-aaa111", "Lehre eins mit \x07 Steuerzeichen und � Ersatzzeichen", "insight",
             "2026-08-01T00:00:00+00:00", "low", "[]", None),
            ("L-bbb222", "Lehre zwei", "error", "2026-08-01T00:00:00+00:00", "high", "[\"x\"]", "irgendwo.py"),
        ]
        for i, n in enumerate(nodes):
            conn.execute("INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?)", n)
            conn.execute("INSERT INTO knowledge_embeddings VALUES ('node',?,'shared',?)", (n[0], vec(i)))
        for i, l in enumerate(lessons):
            conn.execute("INSERT INTO lessons_learned VALUES (?,?,?,?,?,?,?)", l)
            conn.execute("INSERT INTO knowledge_embeddings VALUES ('lesson',?,'shared',?)", (l[0], vec(i + 10)))
        # gesetzte Beziehung: eine mit beiden Enden vorhanden, eine mit totem Ziel
        conn.execute("INSERT INTO knowledge_relations VALUES ('/apps/a','/apps/b')")
        conn.execute("INSERT INTO knowledge_relations VALUES ('/apps/a','/apps/nie-vorhanden')")
        conn.commit()
        conn.close()

        RECALL_LOG_PATH.write_text(
            json.dumps({"ts": "2026-08-01T09:00:00+00:00", "nodes": ["/apps/a", "/apps/b"], "lessons": []}) + "\n"
            + json.dumps({"ts": "2026-08-01T09:05:00+00:00", "nodes": ["/apps/a", "/apps/b"], "lessons": []}) + "\n"
            + json.dumps({"ts": "2026-08-01T09:10:00+00:00", "nodes": ["/apps/a"], "lessons": []}) + "\n"
            # Fall c: gesaeuberter Pfad UND gueltige Lehren-Kennung im selben Abruf.
            + json.dumps({"ts": "2026-08-01T09:15:00+00:00",
                           "nodes": ["/apps/pfad-vor-der-saeuberung"], "lessons": ["L-aaa111"]}) + "\n",
            encoding="utf-8",
        )

        d = sammle()

        # a) Schwelle: (a,b) zweimal gemeinsam -> genau eine Spur. Kein Paar mit w==1.
        n1_idx = next(i for i, p in enumerate(d["punkte"]) if p.get("p") == "/apps/a")
        n2_idx = next(i for i, p in enumerate(d["punkte"]) if p.get("p") == "/apps/b")
        treffer_ab = [s for s in d["spuren"] if {s["a"], s["b"]} == {n1_idx, n2_idx}]
        assert len(treffer_ab) == 1 and treffer_ab[0]["w"] == 2, "Grenzwert Schwelle=2 verletzt (a,b sollten 1 Spur, Gewicht 2 ergeben)"
        assert not any(s["w"] < 2 for s in d["spuren"]), "Negativfall: Paar mit nur 1 gemeinsamem Abruf darf keine Spur erzeugen"

        # b) gesetzte Beziehung: beide Enden vorhanden -> erscheint; totes Ziel -> nicht.
        assert any(g["a"] == n1_idx and g["b"] == n2_idx for g in d["gesetzt"]), "gueltige gesetzte Beziehung fehlt"
        assert len(d["gesetzt"]) == 1, "Beziehung mit totem Ziel haette NICHT erscheinen duerfen"

        # c) halb kaputter Abruf: unaufloesbar++, Lehre bekommt trotzdem ihren Treffer.
        l_idx = next(i for i, p in enumerate(d["punkte"]) if p.get("p") == "L-aaa111")
        assert d["unaufloesbar"] == 1, f"unaufloesbar sollte 1 sein, war {d['unaufloesbar']}"
        assert d["punkte"][l_idx]["h"] >= 1, "Lehre haette trotz kaputtem Pfad im selben Abruf ihren Treffer behalten sollen"
        # Text sauber: kein Steuerzeichen/Ersatzzeichen im Titel.
        assert "\x07" not in d["punkte"][l_idx]["t"] and "�" not in d["punkte"][l_idx]["t"]

        # d) varianz hat genau drei Werte.
        assert len(d["varianz"]) == 3, "varianz muss genau drei Werte haben"

        assert len(d["punkte"]) == 5  # 3 Knoten + 2 Lehren

    # Live-DB darf durch den Selbsttest nicht angefasst worden sein.
    DB_PATH = HERE / "brainlehr.db"
    RECALL_LOG_PATH = HERE / "recall_log.jsonl"
    assert DB_PATH.stat().st_size == real_db_size
    assert DB_PATH.stat().st_mtime == real_db_mtime

    print("Selbsttest gruen: Schwelle, gesetzte Beziehungen, halb kaputter Abruf, varianz-Form -- alle vier bestanden.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    print(json.dumps(sammle(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
