#!/usr/bin/env python3
"""MESSAUFTRAG (Betreiber, 2026-08-13), dritte und entscheidende Frage:
Bringt ein Antwort-VEKTOR ueberhaupt etwas ueber den vorhandenen
STICHWORT-Weg (haken/antwort_abruf.py, top_begriffe + knowledge_search)
hinaus?

VERGLEICH, je Antwort:
  (a) STICHWORT-WEG WIE VERDRAHTET: exakt der Aufruf aus
      antwort_abruf.top_begriffe() + kms.knowledge_search(..., max_results=15)
      -- keine Nachbildung, derselbe Code (import, kein Copy).
  (b) VEKTOR UEBER DEN VOLLEN ANTWORTTEXT: embeddings.embed_text(antwort)
      (bewusst NICHT auf 30 Begriffe verdichtet -- das ist ja gerade die
      Frage), Kosinus gegen ALLE gespeicherten Node-/Lesson-Vektoren
      (knowledge_embeddings, Modell bge-m3 -- dasselbe Modell wie (a) intern
      nutzt), Top 15.
Metrik: SCHNITTMENGE der beiden Top-15-Mengen, UND was der Vektor bringt, das
der Stichwort-Weg NICHT bringt (der eigentlich interessante Rest).

ACHTUNG WEGEN MESSUNG 1 (siehe abschneidegrenze_bge_m3.py): bge-m3 schneidet
bei ca. 2048 Token (~8000 Zeichen) ab. Eine Antwort ueber dieser Laenge liefert
in (b) nur einen Vektor ihres ANFANGS -- wird je Fall vermerkt
(''abgeschnitten''), nicht verschwiegen.

STICHPROBE: 25 echte Antworten aus dem eigenen Sitzungsprotokoll (>=400
Zeichen, wie MIN_LEN in antwort_abruf.py), GLEICHMAESSIG ueber die Sitzung
verteilt (Schrittweite = Gesamtzahl/25) statt der ersten 25 -- sonst waeren
nur fruehe Themen vertreten. Begruendung der Groesse: 25 Faelle x (~0.4s
Stichwortsuche + ~0.3s Embedding + ~0.2s Kosinus) bleibt weit unter dem
10-Minuten-Deckel und liefert genug Faelle fuer eine Ja/Nein-Entscheidung
ueber Schnittmengen-Groessenordnung -- keine statistische Signifikanzpruefung
beauftragt, nur eine Groessenordnung.

GRENZEN: schreibt nur nach runs/. kern/, haken/knowledge_recall_hook.py,
knowledge_mcp_server.py nur importiert/gelesen, nicht geaendert.

Aufruf:
    python3 messungen/vektor_vs_stichwort.py --out runs/<name>.json
    python3 messungen/vektor_vs_stichwort.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import argparse
import json
from pathlib import Path

import embeddings          # kern/embeddings.py
import knowledge_mcp_server as kms  # knowledge_mcp_server.py
import pruefkorpus          # kern/pruefkorpus.py
import speicher             # kern/speicher.py -- lesen(), keine eigene
# sqlite3.connect-Tuer (tests/test_naht_ratsche.py zaehlt genau das).
import antwort_abruf as aa  # haken/antwort_abruf.py -- top_begriffe wiederverwendet

WURZEL = _w
TRANSCRIPT = Path(
    "/Users/lehrmacbook/.claude/projects/"
    "-Volumes-daten-Begod2026-brainlehr--claude-worktrees-hallo-01e380/"
    "d695fd29-c21d-485a-b4d0-f73757047a9d.jsonl")
MIN_LEN = 400
TOP_N = 15  # = antwort_abruf.MAX_RESULTS_STOP, gleicher Deckel fuer fairen Vergleich
SAMPLE_N = 25
ABSCHNEIDE_ZEICHEN = 8000  # Befund aus abschneidegrenze_bge_m3.py


def lade_antworten(transcript=TRANSCRIPT, min_len=MIN_LEN) -> list[str]:
    texte = []
    with open(transcript, encoding="utf-8", errors="replace") as f:
        for zeile in f:
            try:
                d = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "assistant":
                continue
            inhalt = (d.get("message") or {}).get("content") or []
            stuecke = [c.get("text", "") for c in inhalt
                       if isinstance(c, dict) and c.get("type") == "text"]
            text = "\n".join(t for t in stuecke if t)
            if len(text) >= min_len:
                texte.append(text)
    return texte


def stichprobe(antworten: list[str], n: int = SAMPLE_N) -> list[str]:
    if len(antworten) <= n:
        return antworten
    schritt = len(antworten) / n
    return [antworten[int(i * schritt)] for i in range(n)]


def lade_vektoren() -> list[tuple[str, str, list[float]]]:
    with speicher.lesen() as conn:
        rows = conn.execute("SELECT kind, ref_id, vector FROM knowledge_embeddings").fetchall()
    return [(k, r, embeddings.unpack_embedding(v)) for k, r, v in rows]


def stichwort_treffer(antwort: str, n: int = TOP_N) -> list[tuple[str, str]] | None:
    """Exakt der verdrahtete Weg aus antwort_abruf.modus_stop: top_begriffe()
    dann knowledge_search(). None wenn keine Begriffe (wie im Original)."""
    begriffe = aa.top_begriffe(antwort)
    if not begriffe:
        return None
    ergebnis = kms.knowledge_search(" ".join(begriffe), max_results=n)
    treffer = ergebnis.get("results") or []
    out = []
    for e in treffer:
        if e.get("kind") == "lesson":
            out.append(("lesson", e.get("id", "")))
        else:
            out.append(("node", e.get("path", "")))
    return out


def vektor_treffer(antwort: str, vektoren: list[tuple[str, str, list[float]]],
                    n: int = TOP_N) -> tuple[list[tuple[str, str]], bool]:
    """Kosinus des vollen Antworttextes gegen alle gespeicherten Vektoren.
    Zweiter Rueckgabewert: wurde die Antwort vermutlich abgeschnitten
    (Laenge > ABSCHNEIDE_ZEICHEN, siehe Messung 1)."""
    qv = embeddings.embed_text(antwort)
    abgeschnitten = len(antwort) > ABSCHNEIDE_ZEICHEN
    if qv is None:
        return [], abgeschnitten
    bewertet = sorted(
        ((embeddings.cosine_similarity(qv, v), k, r) for k, r, v in vektoren),
        reverse=True, key=lambda t: t[0])
    return [(k, r) for _, k, r in bewertet[:n]], abgeschnitten


def messen(sample_n: int = SAMPLE_N) -> dict:
    alle = lade_antworten()
    sample = stichprobe(alle, sample_n)
    vektoren = lade_vektoren()

    faelle = []
    summe_schnitt = 0
    summe_nur_vektor = 0
    summe_nur_stichwort = 0
    ausgewertete = 0
    ohne_begriffe = 0
    abgeschnittene = 0

    for antwort in sample:
        sw = stichwort_treffer(antwort)
        if sw is None:
            ohne_begriffe += 1
            continue
        vk, abgeschnitten = vektor_treffer(antwort, vektoren)
        if abgeschnitten:
            abgeschnittene += 1
        sw_set = set(sw)
        vk_set = set(vk)
        schnitt = sw_set & vk_set
        nur_vektor = vk_set - sw_set
        nur_stichwort = sw_set - vk_set
        ausgewertete += 1
        summe_schnitt += len(schnitt)
        summe_nur_vektor += len(nur_vektor)
        summe_nur_stichwort += len(nur_stichwort)
        faelle.append({
            "antwort_laenge": len(antwort),
            "abgeschnitten_fuer_vektor": abgeschnitten,
            "stichwort_treffer_n": len(sw_set),
            "vektor_treffer_n": len(vk_set),
            "schnittmenge_n": len(schnitt),
            "nur_vektor_n": len(nur_vektor),
            "nur_stichwort_n": len(nur_stichwort),
            "nur_vektor_beispiele": sorted(f"{k}:{r}" for k, r in list(nur_vektor)[:5]),
        })

    return {
        "stichprobe_gesamt_kandidaten": len(alle),
        "stichprobe_gezogen": len(sample),
        "ausgewertet": ausgewertete,
        "ohne_idf_begriffe_uebersprungen": ohne_begriffe,
        "davon_fuer_vektor_abgeschnitten": abgeschnittene,
        "top_n_je_weg": TOP_N,
        "summe_schnittmenge": summe_schnitt,
        "summe_nur_vektor": summe_nur_vektor,
        "summe_nur_stichwort": summe_nur_stichwort,
        "durchschnitt_schnittmenge_von_top_n": (
            round(summe_schnitt / ausgewertete, 2) if ausgewertete else 0),
        "durchschnitt_nur_vektor_von_top_n": (
            round(summe_nur_vektor / ausgewertete, 2) if ausgewertete else 0),
        "faelle": faelle,
        "befund_text": (
            f"Ueber {ausgewertete} ausgewertete Antworten (von {len(sample)} gezogen, "
            f"{ohne_begriffe} ohne IDF-Begriffe uebersprungen): im Schnitt "
            f"{round(summe_schnitt / ausgewertete, 2) if ausgewertete else 0} von "
            f"{TOP_N} Vektor-Treffern stehen bereits in der Stichwort-Trefferliste, "
            f"{round(summe_nur_vektor / ausgewertete, 2) if ausgewertete else 0} sind "
            f"NUR ueber den Vektor erreichbar (nicht im Stichwort-Weg). "
            f"{abgeschnittene} von {ausgewertete} Antworten lagen ueber der in Messung 1 "
            f"gefundenen Abschneidegrenze -- ihr Vektor bildet nur den Anfang ab."
        ),
    }


def _selftest() -> None:
    # Reine Mengenlogik, kein Modellaufruf: Schnittmenge/Rest korrekt berechnet.
    sw = {("node", "/a"), ("node", "/b"), ("lesson", "L-1")}
    vk = {("node", "/a"), ("lesson", "L-2")}
    assert (sw & vk) == {("node", "/a")}
    assert (vk - sw) == {("lesson", "L-2")}
    assert (sw - vk) == {("node", "/b"), ("lesson", "L-1")}
    print("selftest ok (Mengenlogik)", file=_sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sample-n", type=int, default=SAMPLE_N)
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return
    ergebnis = messen(a.sample_n)
    print(ergebnis["befund_text"])
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"Geschrieben: {a.out}")


if __name__ == "__main__":
    main()
