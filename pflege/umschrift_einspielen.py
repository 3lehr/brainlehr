"""Umschriften einspielen -- aber nur, was den Pruefstein besteht.

Die Schranke ist der Punkt: ein beanstandeter Knoten wird NICHT geschrieben,
er bleibt so stehen, wie er war. Damit kann dieser Lauf den Bestand nur
verbessern oder unveraendert lassen, nie verschlechtern. Ein Sieb, das nur
berichtet, haette den Zahlendreher aus Los 04 ('538-454' statt '438-454')
in den Bestand gelassen und einen Bericht daneben gelegt, den niemand liest.

Geschrieben wird ueber knowledge_update aus knowledge_mcp_server.py, nicht
per SQL: nur dieser Weg traegt Pruefungen, Herkunftsschranke, Protokoll,
Fassungshistorie und den Neubau des Vektors. Ein Import der Werkzeugfunktion
statt eines Werkzeugaufrufs je Knoten -- dieselbe Kette, ohne 385 Aufrufe
(L-95d30e).

Aufruf:
  python3 umschrift_einspielen.py <verzeichnis_mit_neu> [--apply]
  python3 umschrift_einspielen.py --selftest

Ohne --apply wird nur gezaehlt. BEGOD_KNOWLEDGE_DB entscheidet, WOHIN
geschrieben wird -- fuer Probelaeufe auf eine Kopie zeigen lassen.
"""
from __future__ import annotations

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent  # eine Ebene tiefer seit dem Umzug 2026-08-10
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import ort  # noqa: E402
from umschrift_pruefstein import pruefe_knoten  # noqa: E402


def einspielen(los_verzeichnis: Path, neu_verzeichnis: Path, apply: bool,
               update_fn=None, katalog: dict | None = None,
               ersetzungen: dict | None = None) -> dict:
    """update_fn injizierbar (Walkthrough-Doktrin): der Selbsttest laeuft
    ohne Datenbank und ohne Ollama."""
    if update_fn is None:
        from knowledge_mcp_server import knowledge_update
        update_fn = knowledge_update
    bericht = {"geprueft": 0, "geschrieben": 0, "abgelehnt": [], "fehler": [],
               "tags_verworfen": 0}
    for neu_pfad in sorted(neu_verzeichnis.glob("los*.json")):
        alt_pfad = los_verzeichnis / neu_pfad.name
        if not alt_pfad.exists():
            bericht["fehler"].append(f"{neu_pfad.name}: kein Original")
            continue
        alt = {r["id"]: r for r in json.loads(alt_pfad.read_text(encoding="utf-8"))}
        neu = {r["id"]: r for r in json.loads(neu_pfad.read_text(encoding="utf-8"))}
        for nid, a in alt.items():
            n = neu.get(nid)
            if n is None:
                bericht["abgelehnt"].append({"id": nid, "grund": "fehlt in der Umschrift"})
                continue
            bericht["geprueft"] += 1
            befund = pruefe_knoten(a, n)
            if not befund["ok"]:
                bericht["abgelehnt"].append({
                    "id": nid, "grund": "Traeger verloren oder erfunden",
                    "fehlend": befund["fehlend"], "erfunden": befund["erfunden"]})
                continue
            tags = n.get("tags")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = None
            if katalog is not None and isinstance(tags, list):
                # Erst auf den Leitbegriff abbilden, dann filtern. Ohne diesen
                # Schritt faellt ein bekanntes Synonym ('entscheid') heraus,
                # statt auf seine Kategorie ('entscheidung') zu zeigen -- der
                # Schreiber hatte recht, nur das Wort war ein anderes.
                abgebildet = [(ersetzungen or {}).get(t, t) for t in tags]
                erlaubt = list(dict.fromkeys(t for t in abgebildet if t in katalog))
                bericht["tags_verworfen"] += len(tags) - len(erlaubt)
                tags = erlaubt
            if not apply:
                bericht["geschrieben"] += 1
                continue
            ergebnis = update_fn(nid, title=n["title"], summary=n["summary"],
                                 content=n["co"], tags=tags,
                                 actor="claude-code", model="claude-opus-5")
            if isinstance(ergebnis, dict) and ergebnis.get("error"):
                bericht["fehler"].append(f"{nid}: {ergebnis['error']}")
            else:
                bericht["geschrieben"] += 1
    return bericht


def main(argv: list[str]) -> int:
    neu_verzeichnis = Path(argv[1])
    los_verzeichnis = neu_verzeichnis.parent / "lose"
    apply = "--apply" in argv
    kat_pfad = WURZEL / "runs" / "tagkatalog.json"
    kat = json.loads(kat_pfad.read_text(encoding="utf-8")) if kat_pfad.exists() else {}
    katalog = kat.get("tags")
    ersetzungen = kat.get("ersetzungen", {})
    print(f"Ziel: {ort.DB}\nModus: {'SCHREIBEN' if apply else 'nur zaehlen'}\n")
    b = einspielen(los_verzeichnis, neu_verzeichnis, apply, katalog=katalog,
                   ersetzungen=ersetzungen)
    print(f"geprueft:    {b['geprueft']}")
    print(f"geschrieben: {b['geschrieben']}")
    print(f"abgelehnt:   {len(b['abgelehnt'])}  (bleiben unveraendert im Bestand)")
    if b["tags_verworfen"]:
        print(f"Tags ausserhalb des Katalogs verworfen: {b['tags_verworfen']}")
    for f in b["fehler"]:
        print(f"  FEHLER {f}")
    ablage = WURZEL / "runs" / "umschrift_abgelehnt.json"
    ablage.write_text(json.dumps(b["abgelehnt"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAbgelehnte je Knoten: {ablage}")
    return 0 if not b["fehler"] else 1


def demo() -> None:
    """Ohne DB, ohne Ollama: update_fn wird injiziert. Belegt die Schranke in
    beide Richtungen -- der saubere Knoten geht durch, der mit verlorener Zahl
    nicht, und der mit erfundener Zahl auch nicht."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        wurzel = Path(d)
        (wurzel / "lose").mkdir()
        (wurzel / "neu").mkdir()
        alt = [
            {"id": "a", "title": "ADR-023", "summary": "8,50 USD je Nachricht", "co": "Faktor 3.", "tags": []},
            {"id": "b", "title": "Zweiter", "summary": "Messreihe 285, 426, 657", "co": "", "tags": []},
            {"id": "c", "title": "Dritter", "summary": "Nichts Besonderes", "co": "", "tags": []},
        ]
        neu = [
            {"id": "a", "title": "Was die Kaskade kostet (ADR-023)",
             "summary": "Je Nachricht wurden 8,50 USD gemessen.", "co": "Das ist Faktor 3.",
             "tags": ["methodik", "erfundenes-tag", "entscheid"]},
            {"id": "b", "title": "Zweiter Knoten", "summary": "Eine Messreihe lag vor.",
             "co": "", "tags": []},                       # 285/426/657 verloren -> Schranke
            {"id": "c", "title": "Dritter Knoten", "summary": "Nichts Besonderes, Wert 99.",
             "co": "", "tags": []},                       # 99 erfunden -> Schranke
        ]
        (wurzel / "lose" / "los01.json").write_text(json.dumps(alt), encoding="utf-8")
        (wurzel / "neu" / "los01.json").write_text(json.dumps(neu), encoding="utf-8")

        geschrieben = []

        def fake_update(nid, **kw):
            geschrieben.append((nid, kw.get("tags")))
            return {"status": "ok"}

        b = einspielen(wurzel / "lose", wurzel / "neu", apply=True,
                       update_fn=fake_update, katalog={"methodik": 91, "entscheidung": 11},
                       ersetzungen={"entscheid": "entscheidung"})
        assert b["geprueft"] == 3, b
        assert b["geschrieben"] == 1, f"nur der saubere Knoten darf durch: {b}"
        assert [g[0] for g in geschrieben] == ["a"], geschrieben
        abgelehnt = {x["id"] for x in b["abgelehnt"]}
        assert abgelehnt == {"b", "c"}, abgelehnt
        # 'entscheid' ist kein Katalogeintrag, aber eine bekannte Ersetzung --
        # es muss als 'entscheidung' ankommen, nicht verworfen werden.
        assert geschrieben[0][1] == ["methodik", "entscheidung"], (
            f"Synonym muss auf den Leitbegriff zeigen: {geschrieben}")
        assert b["tags_verworfen"] == 1, f"nur das erfundene Tag darf fallen: {b}"

        # Gegenprobe: ohne --apply wird nichts geschrieben, aber gleich gezaehlt.
        geschrieben.clear()
        b2 = einspielen(wurzel / "lose", wurzel / "neu", apply=False,
                        update_fn=fake_update, katalog={"methodik": 91, "entscheidung": 11},
                        ersetzungen={"entscheid": "entscheidung"})
        assert not geschrieben, "Trockenlauf darf nicht schreiben"
        assert b2["geschrieben"] == 1 and len(b2["abgelehnt"]) == 2, b2
    print("umschrift_einspielen.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        raise SystemExit(main(sys.argv))
