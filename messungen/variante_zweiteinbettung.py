#!/usr/bin/env python3
"""V1 -- situative Zweiteinbettung, gegen den Bedeutungskanal gemessen.

Plan: docs/PLAN_EINBETTUNGSVARIANTEN_2026-08-16.md, Abschnitt V1.
Befund: Knoten 291c2e3f -- Aufgaben im Pruefkorpus sind Situationsbeschreibungen
in Alltagssprache, Ziele sind technische Fehlerbeschreibungen mit Eigennamen.

IDEE: jedes Ziel bekommt ZUSAETZLICH zu seiner bestehenden Einbettung eine, die
seine LAGE beschreibt statt seiner Technik (Haiku ueber die Anthropic-API,
L-a69129 -- kein lokales Modell fuers Umschreiben). Ein Ziel gilt als
getroffen, wenn EINE seiner beiden Einbettungen den besseren Rang liefert.

WAS DIES NICHT ANFASST: knowledge_embeddings (nur mode=ro geoeffnet), das
Gerüst messungen/einbettungsvarianten.py (nur importiert), den Produktivbestand.
Alles Zusaetzliche lebt im Arbeitsspeicher.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import numpy as np  # noqa: E402

import embeddings  # noqa: E402
import einbettungsvarianten as basis  # noqa: E402  -- Gerüst wird nur gelesen/importiert

DB = _w / "brainlehr.db"
HAIKU_MODELL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "Du beschreibst die LAGE eines technischen Lehrsatzes in Alltagssprache. "
    "Ein Satz, maximal zwei. KEINE Eigennamen, KEINE Code-Bezeichner, KEINE "
    "Dateinamen, KEINE Funktionsnamen -- nur die Situation, in der jemand auf "
    "dieses Problem stossen wuerde. Antworte NUR mit der Umschreibung."
)


def api_verfuegbar() -> str | None:
    """Prueft, ob ein Anthropic-API-Zugang besteht -- NICHT annehmen, NICHT
    auf ein lokales Modell ausweichen (L-a69129, dreimal verletzt). Gibt den
    Fehlgrund zurueck, oder None wenn nutzbar."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return "ANTHROPIC_API_KEY ist nicht gesetzt"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return "Python-Paket 'anthropic' ist nicht installiert"
    return None


def lade_zieltext(conn: sqlite3.Connection, art: str, ziel_id: str) -> str:
    """Der bestehende Volltext des Ziels -- Ausgangsmaterial fuer die
    situative Umschreibung."""
    if art == "lesson":
        row = conn.execute(
            "SELECT description, root_cause, resolution, prevention "
            "FROM lessons_learned WHERE id = ?", (ziel_id,)).fetchone()
        if not row:
            return ""
        return "\n".join(t for t in row if t)
    row = conn.execute(
        "SELECT title, summary, content FROM knowledge_nodes WHERE path = ? OR id = ?",
        (ziel_id, ziel_id)).fetchone()
    if not row:
        return ""
    return "\n".join(t for t in row if t)


def situative_umschreibung(client, zieltext: str) -> str | None:
    """Ein Haiku-Aufruf je Ziel. None bei leerem Ausgangstext oder API-Fehler
    -- ein Ausfall darf die Messung nicht abbrechen, nur dieses Ziel bleibt
    dann ohne Zweiteinbettung (zaehlt als nicht verbessert, nicht als Fehler)."""
    zieltext = (zieltext or "").strip()
    if not zieltext:
        return None
    try:
        resp = client.messages.create(
            model=HAIKU_MODELL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": zieltext[:4000]}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        return text or None
    except Exception as exc:  # Netzwerk/API-Fehler -- best effort, kein Absturz
        print(f"warnung: Haiku-Aufruf fehlgeschlagen: {exc}", file=sys.stderr)
        return None


def rang_zweiteinbettung(frage_text: str, ziel: str, ids: list[str], mat: np.ndarray,
                          zusatz_id_zu_vec: dict[str, list[float]]) -> int | None:
    """Rang ueber die BESTEHENDE Kandidatenmatrix, plus -- falls vorhanden --
    das Ziel ein zweites Mal mit seiner situativen Einbettung, an derselben
    Kosinus-Metrik gemessen. Der bessere (kleinere) der beiden Raenge gilt."""
    frage_vec = embeddings.embed_text(frage_text)
    r_basis = basis.rang_des_ziels(frage_vec, ziel, ids, mat)

    zusatz_vec = zusatz_id_zu_vec.get(ziel)
    if frage_vec is None or zusatz_vec is None:
        return r_basis

    # Rang des Ziels ueber seine ZWEITE Einbettung: die Kandidatenmenge ist
    # dieselbe, nur der Vektor an der Zielposition wird ausgetauscht.
    q = np.array(frage_vec, dtype=np.float32)
    q /= max(float(np.linalg.norm(q)), 1e-9)
    z = np.array(zusatz_vec, dtype=np.float32)
    z /= max(float(np.linalg.norm(z)), 1e-9)
    sims = mat @ q
    ziel_sim_zusatz = float(z @ q)
    # Rang = 1 + Anzahl Kandidaten, die besser sind als die Zusatz-Aehnlichkeit
    # (das Ziel selbst zaehlt nicht doppelt gegen sich).
    besser = int(np.sum(sims > ziel_sim_zusatz))
    andere_ids_besser = sum(1 for j, s in enumerate(sims) if ids[j] != ziel and s > ziel_sim_zusatz)
    r_zusatz = andere_ids_besser + 1

    if r_basis is None:
        return r_zusatz
    return min(r_basis, r_zusatz)


def stufe_zweiteinbettung(faelle: list[dict], ids: list[str], mat: np.ndarray,
                           zusatz_id_zu_vec: dict[str, list[float]]) -> dict:
    raenge = []
    for f in faelle:
        r = rang_zweiteinbettung(f["task"], f["target_id"], ids, mat, zusatz_id_zu_vec)
        raenge.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": r})
    return {"name": "1-zweiteinbettung", "raenge": raenge}


def demo() -> None:
    """Netzloser Selbsttest der Rangrechnung mit Handmatrix, Vorbild demo()
    im Geruest. Prueft insbesondere: die Zusatz-Einbettung kann einen Rang
    VERBESSERN, aber nie verschlechtern (min() der beiden)."""
    ids = ["a", "b", "c"]
    mat = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]], dtype=np.float32)
    mat[2] /= np.linalg.norm(mat[2])

    # Basis-Frage zeigt auf [1,0] -- "a" liegt vorn, "c" ganz hinten (Rang 3).
    # Zusatz-Einbettung von "c" zeigt jetzt auch auf [1,0]: c muss auf Rang 1
    # vorruecken, ohne dass sich a oder b aendern.
    zusatz = {"c": [1.0, 0.0]}

    # embed_text real aufzurufen wuerde Netz brauchen -- monkeypatch fuer den Selbsttest.
    orig = embeddings.embed_text
    embeddings.embed_text = lambda text, **kw: [1.0, 0.0]
    try:
        rang = rang_zweiteinbettung("frage", "c", ids, mat, zusatz)
        assert rang == 1, f"Zusatz-Einbettung haette c auf Rang 1 heben muessen, war {rang}"

        rang_a = rang_zweiteinbettung("frage", "a", ids, mat, zusatz)
        assert rang_a == 1, "a war schon Rang 1 und darf es bleiben"

        # Ziel ohne Zusatz-Einbettung faellt auf den Basis-Rang zurueck (b und
        # c sind gleich [0,1] -- bei Gleichstand entscheidet Reihenfolge in
        # ids, b vor c, also Basis-Rang 2).
        rang_b = rang_zweiteinbettung("frage", "b", ids, mat, {})
        assert rang_b == 2, f"b ohne Zusatz muss Basis-Rang behalten, war {rang_b}"

        # Fehlender Frage-Vektor -> None, wie im Geruest.
        embeddings.embed_text = lambda text, **kw: None
        assert rang_zweiteinbettung("frage", "a", ids, mat, zusatz) is None
    finally:
        embeddings.embed_text = orig

    probe = {"name": "probe", "raenge": [{"rang": 1}, {"rang": 7}, {"rang": None}]}
    a = basis.auswertung(probe, kandidaten=42)
    assert a["in_top5"] == 1 and a["nicht_im_kanal"] == 1
    print("demo: ok", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--korpus", required=True, help="Pfad zum Pruefkorpus (kein Vorgabewert)")
    p.add_argument("--out", default=None)
    p.add_argument("--gegenprobe", action="store_true",
                    help="Situative Umschreibung durch den Originaltext ersetzen -- "
                         "muss Stufe 0 reproduzieren (top5=4/35)")
    a = p.parse_args()

    fehlgrund = api_verfuegbar()
    if fehlgrund and not a.gegenprobe:
        print(f"Abbruch: kein Anthropic-API-Zugang ({fehlgrund}). "
              "L-a69129 verbietet das Ausweichen auf ein lokales Modell.", file=sys.stderr)
        sys.exit(1)

    faelle = basis.lade_faelle(Path(a.korpus))
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ids, mat = basis.lade_kandidaten(conn)

    # Zusatz-Einbettung je EINDEUTIGES Ziel im Korpus -- nicht je Fall (mehrere
    # Faelle koennen dasselbe Ziel haben, Doppelarbeit waere nur Kosten ohne Nutzen).
    ziel_arten = {(f["target_kind"], f["target_id"]) for f in faelle}
    zusatz_id_zu_vec: dict[str, list[float]] = {}
    client = None
    if not fehlgrund:
        import anthropic
        client = anthropic.Anthropic()

    for art, ziel_id in sorted(ziel_arten):
        zieltext = lade_zieltext(conn, art, ziel_id)
        if a.gegenprobe:
            umschreibung = zieltext  # Gegenprobe: Original statt Umschreibung
        else:
            umschreibung = situative_umschreibung(client, zieltext)
        if not umschreibung:
            continue
        vec = embeddings.embed_text(umschreibung)
        if vec is not None:
            zusatz_id_zu_vec[ziel_id] = vec

    bestand = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()

    stufen = [stufe_zweiteinbettung(faelle, ids, mat, zusatz_id_zu_vec)]
    ergebnis = {
        "korpus": str(Path(a.korpus).resolve()).replace(str(_w) + "/", ""),
        "faelle": len(faelle),
        "modell": embeddings.DEFAULT_EMBED_MODEL,
        "umschreibungsmodell": HAIKU_MODELL if not a.gegenprobe else "keins (Gegenprobe: Originaltext)",
        "ziele_mit_zusatzeinbettung": len(zusatz_id_zu_vec),
        "ziele_gesamt": len(ziel_arten),
        "knoten_bestand": bestand,
        "kandidaten_im_kanal": len(ids),
        "gemessen_wird": ("Rang des Ziels im REINEN Bedeutungskanal, besserer Rang aus "
                          "Basis-Einbettung ODER situativer Zusatz-Einbettung -- nicht der "
                          "volle Suchweg"),
        "grenze": ["misst nicht den vollen Suchweg (nur den Bedeutungskanal)",
                   "35 Faelle sind klein -- ein knapper Unterschied ist kein Ergebnis",
                   "misst nicht die Betriebskosten der Zweiteinbettung (Haiku je Ziel, einmalig)",
                   "prueft nur die Vorprobe (35 Faelle als Kandidaten UND Ziele je nach Korpus) "
                   "-- keine Aussage ueber den vollen Bestand von 5964 Knoten/Lehren"],
        "stufen": [basis.auswertung(s, len(ids)) for s in stufen],
        "roh": {s["name"]: s["raenge"] for s in stufen},
    }
    text = json.dumps(ergebnis, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"geschrieben: {a.out}", file=sys.stderr)
    for s in ergebnis["stufen"]:
        print(f"{s['name']:20} top5={s['in_top5']}/{s['faelle']}  top50={s['in_top50']}  "
              f"median={s['median_rang']}  von {s['kandidaten']} Kandidaten")


if __name__ == "__main__":
    demo()
    main()
