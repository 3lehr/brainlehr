#!/usr/bin/env python3
"""V2 -- die Anfrage wird vor der Suche in ein hypothetisches Zieldokument
uebersetzt (HyDE-artig), statt den Bestand zu aendern.

Plan: docs/PLAN_EINBETTUNGSVARIANTEN_2026-08-16.md
Gerüst (nur gelesen, nicht geaendert): messungen/einbettungsvarianten.py

Modellwahl ist NICHT frei: L-a69129 (dreimal verletzt) verlangt Haiku ueber
die Anthropic-API fuer Umschreibungen dieser Art, kein lokales Modell. Fehlt
Paket oder Schluessel, bricht dieses Werkzeug ab statt auszuweichen.

GRENZE: siehe --out-Datei, Feld "grenze". Kurzfassung: misst den reinen
Bedeutungskanal (nicht den vollen Suchweg), 35 Faelle sind klein, und die
Umschreibedauer ist eine Betriebskostenschaetzung, keine Lastmessung.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sqlite3
import sys
import time
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import embeddings  # noqa: E402
import einbettungsvarianten as basis  # noqa: E402  -- nur gelesen, nicht geaendert

HAIKU_MODELL = "claude-haiku-4-5-20251001"

_SYSTEM = (
    "Du uebersetzt eine alltagssprachliche Situationsbeschreibung in einen "
    "kurzen technischen Eintrag, wie er in einer Fehler-/Lehrendatenbank "
    "stehen wuerde: knapp, mit Eigennamen/Komponenten, ohne Hoeflichkeitsfloskeln. "
    "Antworte NUR mit dem Eintragstext, keine Erklaerung."
)


def api_verfuegbar() -> str | None:
    """None wenn nutzbar, sonst ein Grund als Text (fuer die Meldung)."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return "Paket 'anthropic' ist nicht installiert"
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY ist nicht gesetzt"
    return None


def umschreiben(task_text: str, *, client=None) -> tuple[str, float]:
    """Liefert (umschriebener_text, dauer_sekunden). client ist injizierbar
    fuer Tests -- siehe demo()."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    start = time.monotonic()
    antwort = client.messages.create(
        model=HAIKU_MODELL,
        max_tokens=200,
        system=_SYSTEM,
        messages=[{"role": "user", "content": task_text}],
    )
    dauer = time.monotonic() - start
    text = "".join(b.text for b in antwort.content if getattr(b, "type", "") == "text").strip()
    return text, dauer


def stufe_v2(faelle: list[dict], ids: list[str], mat, *, client=None) -> tuple[dict, list[float]]:
    raenge = []
    dauern = []
    for f in faelle:
        umschrift, dauer = umschreiben(f["task"], client=client)
        dauern.append(dauer)
        r = basis.rang_des_ziels(embeddings.embed_text(umschrift), f["target_id"], ids, mat)
        raenge.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": r,
                        "umschrift": umschrift})
    return {"name": "2-anfrageumschrift", "raenge": raenge}, dauern


def demo() -> None:
    """Netzloser Selbsttest: Rangrechnung (von basis geerbt) plus die
    Dauer-Erfassung mit einem Fake-Client -- kein Netz, keine Datenbank."""
    ids = ["a", "b", "c"]
    import numpy as np
    mat = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]], dtype=np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True)
    assert basis.rang_des_ziels([1.0, 0.0], "a", ids, mat) == 1

    class FakeBlock:
        type = "text"
        text = "technischer eintrag"

    class FakeAntwort:
        content = [FakeBlock()]

    class FakeClient:
        class messages:
            @staticmethod
            def create(**kw):
                return FakeAntwort()

    text, dauer = umschreiben("irgendeine lage", client=FakeClient())
    assert text == "technischer eintrag"
    assert dauer >= 0.0

    probe = {"name": "probe", "raenge": [{"rang": 1}, {"rang": 7}, {"rang": 200}, {"rang": None}]}
    a = basis.auswertung(probe, kandidaten=999)
    assert a["median_rang"] == 7 and a["in_top5"] == 1
    print("demo: ok", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--korpus", required=True, help="Pfad zum Pruefkorpus (kein Vorgabewert)")
    p.add_argument("--out", default=None)
    p.add_argument("--gegenprobe", action="store_true",
                    help="Umschrift durch die Originalfrage ersetzen -- muss Stufe 0 treffen")
    a = p.parse_args()

    if not a.gegenprobe:
        grund = api_verfuegbar()
        if grund:
            print(f"ABBRUCH: {grund} -- kein Ausweichen auf ein lokales Modell (L-a69129).",
                  file=sys.stderr)
            sys.exit(1)

    faelle = basis.lade_faelle(Path(a.korpus))
    conn = sqlite3.connect(f"file:{basis.DB}?mode=ro", uri=True)
    ids, mat = basis.lade_kandidaten(conn)
    conn.close()

    if a.gegenprobe:
        class IdentitaetsClient:
            class messages:
                @staticmethod
                def create(**kw):
                    class B:
                        type = "text"
                        text = kw["messages"][0]["content"]
                    class R:
                        content = [B()]
                    return R()
        stufe, dauern = stufe_v2(faelle, ids, mat, client=IdentitaetsClient())
        stufe["name"] = "gegenprobe-identitaet"
    else:
        stufe, dauern = stufe_v2(faelle, ids, mat)

    aus = basis.auswertung(stufe, len(ids))
    ergebnis = {
        "korpus": str(Path(a.korpus).resolve()).replace(str(_w) + "/", ""),
        "faelle": len(faelle),
        "modell": embeddings.DEFAULT_EMBED_MODEL,
        "umschreibe_modell": HAIKU_MODELL if not a.gegenprobe else "identitaet(gegenprobe)",
        "kandidaten_im_kanal": len(ids),
        "grenze": ["misst nicht den vollen Suchweg, nur den reinen Bedeutungskanal",
                   "35 Faelle sind klein -- ein knapper Unterschied ist kein Ergebnis",
                   "Dauer ist je-Anfrage-Overhead dieses Laufs, keine Lastmessung im Betrieb"],
        "stufe": aus,
        "dauer_je_umschrift_sekunden": {
            "median": round(st.median(dauern), 3) if dauern else None,
            "min": round(min(dauern), 3) if dauern else None,
            "max": round(max(dauern), 3) if dauern else None,
            "summe": round(sum(dauern), 3) if dauern else None,
        },
        "roh": stufe["raenge"],
    }
    text = json.dumps(ergebnis, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"geschrieben: {a.out}", file=sys.stderr)
    print(f"{aus['name']:20} top5={aus['in_top5']}/{aus['faelle']}  top50={aus['in_top50']}  "
          f"median={aus['median_rang']}  von {aus['kandidaten']} Kandidaten")


if __name__ == "__main__":
    demo()
    main()
