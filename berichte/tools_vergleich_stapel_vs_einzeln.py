"""Einmal-Werkzeug, nicht Teil der Lieferung: vergleicht Vektoren aus
/tmp/vektoren_vorher.db (einzeln gerechnet, Rot-Lauf 2026-08-07T20:06:15) mit
denen in der aktuellen brainlehr.db (stapelweise gerechnet, BATCH_SIZE=32) --
gleiche ref_id/kind/project_id, Kosinus. Stichprobe gemischt kurz/lang ueber
Textlaenge (len(coalesce(content,''))+len(summary) fuer Knoten, len(description)
fuer Lehren).
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

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import embeddings

OLD = "/tmp/vektoren_vorher.db"
NEW = str(Path(__file__).parent.parent / "brainlehr.db")

old = sqlite3.connect(OLD)
new = sqlite3.connect(NEW)

# Stichprobe: 60 kuerzeste + 60 laengste Knoten-Texte (Extreme, keine Zufallsauswahl
# aus der Mitte -- wenn Batch-Padding/Attention-Masken etwas verzerren, zeigt es
# sich am ehesten an den Randlaengen) + 30 Lehren.
rows = old.execute(
    "SELECT id, project_id, length(coalesce(content,'')) + length(summary) AS len "
    "FROM knowledge_nodes ORDER BY len ASC LIMIT 60"
).fetchall()
rows += old.execute(
    "SELECT id, project_id, length(coalesce(content,'')) + length(summary) AS len "
    "FROM knowledge_nodes ORDER BY len DESC LIMIT 60"
).fetchall()
node_sample = [(r[0], r[1]) for r in rows]

lesson_rows = old.execute(
    "SELECT id FROM lessons_learned LIMIT 30"
).fetchall()
lesson_rows = [(r[0], None) for r in lesson_rows]

sims = []
missing = 0
for ref_id, project_id in node_sample:
    o = old.execute(
        "SELECT vector FROM knowledge_embeddings WHERE kind='node' AND ref_id=? AND project_id=?",
        (ref_id, project_id)).fetchone()
    n = new.execute(
        "SELECT vector FROM knowledge_embeddings WHERE kind='node' AND ref_id=? AND project_id=?",
        (ref_id, project_id)).fetchone()
    if not o or not n:
        missing += 1
        continue
    v_old = embeddings.unpack_embedding(o[0])
    v_new = embeddings.unpack_embedding(n[0])
    sims.append(embeddings.cosine_similarity(v_old, v_new))

lesson_sims = []
for ref_id, project_id in lesson_rows:
    # Lehren-Embedding-PK ist (kind, ref_id, project_id_aus_fanout) -- wir nehmen
    # irgendeine vorhandene project_id-Zeile fuer diese ref_id aus old.
    o = old.execute(
        "SELECT project_id, vector FROM knowledge_embeddings WHERE kind='lesson' AND ref_id=? LIMIT 1",
        (ref_id,)).fetchone()
    if not o:
        continue
    n = new.execute(
        "SELECT vector FROM knowledge_embeddings WHERE kind='lesson' AND ref_id=? AND project_id=?",
        (ref_id, o[0])).fetchone()
    if not n:
        missing += 1
        continue
    v_old = embeddings.unpack_embedding(o[1])
    v_new = embeddings.unpack_embedding(n[0])
    lesson_sims.append(embeddings.cosine_similarity(v_old, v_new))

all_sims = sims + lesson_sims
print(f"n_verglichen={len(all_sims)} (nodes={len(sims)}, lessons={len(lesson_sims)}), fehlend={missing}")
if all_sims:
    print(f"min={min(all_sims):.6f}  median={statistics.median(all_sims):.6f}  mean={statistics.mean(all_sims):.6f}  max={max(all_sims):.6f}")
    worst = sorted(zip(all_sims, node_sample + lesson_rows), key=lambda x: x[0])[:5]
    print("5 schlechteste:", worst)
old.close()
new.close()
