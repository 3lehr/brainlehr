#!/usr/bin/env python3
"""Pruefkorpus aus rueckblickend beschrifteten Abrufversagen.

ANLASS (2026-08-11): echtkorpus.py liefert 77 Faelle, davon 71 Arbeitsauftraege
und nur 6 Fragen -- zwei davon falsch einsortiert. Der Grund ist strukturell:
eine Nachricht bekommt ihr Ziel dadurch, dass sie einen Pfad oder eine Kennung
NENNT, und das tun vor allem Arbeitsauftraege. Eine echte Fachfrage nennt keine
Adresse (L-3ba807).

Der Bestand zeigt selbst einen Ausweg: manchmal beschriftet der Betreiber im
NACHHINEIN, was haette gefunden werden muessen -- "warum hast du X nicht
gelesen". Das ist ein Goldstandard-Fall: ein belegter Fehlgriff, benannt von
der Person, die den Fehlgriff erlebt hat, statt eines erdachten Falls.

Dieses Modul sucht genau diese Sorte Nachricht in den Sitzungstranskripten
(dieselbe Quelle wie echtkorpus.sitzungs_nachrichten, hier aber ordnungs-
erhaltend gelesen, weil die VORGAENGERnachricht gebraucht wird) und macht
daraus einen Fall:

  Aufgabentext  die Nachricht VOR der Beschwerde -- die, bei der der Abruf
                versagt hat
  Zielangabe    die Kennung/der Pfad, den der Betreiber in der Beschwerde
                selbst genannt hat, gegen die Datenbank geprueft

Aufruf:
    python3 rueckblick.py --sammeln --out runs/rueckblick_2026-08-11.json
    python3 rueckblick.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
ROOT = WURZEL.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "haken"))
sys.path.insert(0, str(ROOT / "kern"))
sys.path.insert(0, str(WURZEL))

import echtkorpus as ek  # noqa: E402  -- SITZUNGEN, kennungen, kennung_pruefen, satzart, Filter
import speicher  # noqa: E402

# Beobachtbare Beschwerde-/Nachfrageform, die auf ein Versaeumnis zeigt.
# Freie Formulierung, kein starres Muster -- DOTALL, weil "warum hast du ...
# nicht gelesen" oft ueber mehrere eingeschobene Woerter/Zeilen laeuft.
BESCHWERDE = re.compile(
    r"warum\s+hast\s+du\b.{0,200}?\bnicht\b.{0,80}?\b"
    r"(gelesen|gefunden|gewusst|gesehen|gepr[üu]ft|angeschaut|angesehen|beachtet)\b"
    r"|das\s+steht\s+doch\s+in\b"
    r"|h[äa]ttest\s+du\b.{0,80}?\b(angesehen|gelesen|gepr[üu]ft|angeschaut|gefunden)\b"
    r"|du\s+kennst\s+doch\b",
    re.IGNORECASE | re.DOTALL,
)

# Automatische Fortsetzungs-Zusammenfassung (Claude Code, bei Kontext-Ende) --
# als "user"-Nachricht gespeichert, aber kein Betreibertext. Enthaelt oft
# zitierte Gespraechsfetzen, die die Beschwerdeform zufaellig treffen (2 von
# 3 rohen Treffern im ersten Lauf waren genau das).
_AUTOZUSAMMENFASSUNG = re.compile(
    r"^This session is being continued from a previous conversation")


def _texte_geordnet(pfad: Path) -> list[str]:
    """Echte Nutzernachrichten EINER Sitzung, in Transkriptreihenfolge.
    Extraktion identisch zu echtkorpus.sitzungs_nachrichten, hier aber pro
    Datei statt gepoolt, weil die Nachbarschaft (Vorgaenger) gebraucht wird."""
    try:
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    raus = []
    for zeile in zeilen:
        try:
            satz = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if satz.get("type") != "user":
            continue
        inhalt = (satz.get("message") or {}).get("content")
        if isinstance(inhalt, str):
            text = inhalt.strip()
        elif isinstance(inhalt, list):
            text = "\n".join(
                t.get("text", "") for t in inhalt
                if isinstance(t, dict) and t.get("type") == "text").strip()
        else:
            continue
        if ek._ist_echte_frage(text) and not _AUTOZUSAMMENFASSUNG.match(text):
            raus.append(text)
    return raus


def faelle_aus_sitzung(texte: list[str], conn) -> list[dict]:
    """Ein Fall pro (Vorgaenger, Beschwerde)-Paar: Beschwerde traegt Form UND
    eine echte Kennung, ein Vorgaenger existiert. Ohne Vorgaenger kein Fall --
    es gibt nichts, das der Aufgabentext sein koennte."""
    faelle = []
    for i in range(1, len(texte)):
        beschwerde = texte[i]
        if not BESCHWERDE.search(beschwerde):
            continue
        ziele = set()
        for k in sorted(ek.kennungen(beschwerde)):
            treffer = ek.kennung_pruefen(k, conn)
            if treffer:
                ziele.add((treffer["art"], treffer["id"]))
        if not ziele:
            continue
        vorgaenger = texte[i - 1]
        faelle.append({
            "prompt": vorgaenger,
            "beschwerde": beschwerde,
            "klasse": "rueckblick",
            "satzart": ek.satzart(vorgaenger),
            "ziele": [{"art": a, "id": j} for a, j in sorted(ziele)],
        })
    return faelle


def sammeln(conn) -> tuple[int, int, list[dict]]:
    """Liefert (Transkripte, Kandidaten, Faelle). Kandidat = Beschwerdesatz
    mit Form UND mindestens einer Kennung im Text (vor Vorgaenger-Pruefung)."""
    n_transkripte = 0
    n_kandidaten = 0
    faelle: list[dict] = []
    if not ek.SITZUNGEN.exists():
        return 0, 0, []
    for pfad in ek.SITZUNGEN.glob("*/[0-9a-f-]*.jsonl"):
        n_transkripte += 1
        texte = _texte_geordnet(pfad)
        for i, t in enumerate(texte):
            if BESCHWERDE.search(t) and ek.kennungen(t):
                n_kandidaten += 1
        faelle.extend(faelle_aus_sitzung(texte, conn))
    return n_transkripte, n_kandidaten, faelle


def _selftest() -> None:
    class FakeCursor:
        def __init__(self, treffer): self._treffer = treffer
        def fetchone(self): return self._treffer

    class FakeConn:
        def __init__(self, echte_lehren): self._lehren = echte_lehren
        def execute(self, sql, params):
            wert = params[0]
            if "lessons_learned" in sql:
                return FakeCursor({"id": wert} if wert in self._lehren else None)
            return FakeCursor(None)

    conn = FakeConn(echte_lehren={"L-ebbd22"})
    vorgaenger = "\"L-ebbd22, Schimmel-Lexikon\" was stand darin?"
    beschwerde = ('aber warum hast du "L-ebbd22, Schimmel-Lexikon" nicht gelesen '
                  'und ich müsste dich erste fragen was darin steht?')

    # 1) Beschwerde mit gueltiger Kennung UND Vorgaenger -> ein Fall, Aufgabentext
    #    ist die Vorgaengernachricht.
    f = faelle_aus_sitzung([vorgaenger, beschwerde], conn)
    assert len(f) == 1, f
    assert f[0]["prompt"] == vorgaenger, f
    assert f[0]["klasse"] == "rueckblick"
    assert f[0]["ziele"] == [{"art": "lehre", "id": "L-ebbd22"}], f

    # 2) dieselbe Beschwerde ohne Vorgaenger (erste Nachricht der Liste) -> kein Fall.
    assert faelle_aus_sitzung([beschwerde], conn) == []

    # 3) gewoehnliche Nachricht mit Kennung, ohne Beschwerdeform -> kein Fall.
    gewoehnlich = "Siehe L-ebbd22 zum Schimmel-Lexikon, das ist der Stand."
    assert faelle_aus_sitzung([vorgaenger, gewoehnlich], conn) == []

    # 4) erfundene Kennung -> kein Fall, obwohl Form passt.
    beschwerde_erfunden = beschwerde.replace("L-ebbd22", "L-ffffff")
    assert faelle_aus_sitzung([vorgaenger, beschwerde_erfunden], conn) == []

    # 5) automatische Fortsetzungs-Zusammenfassung wird nicht als Nachricht
    #    gezaehlt, auch wenn sie die Beschwerdeform zufaellig zitiert.
    import tempfile
    sitzung = Path(tempfile.mkdtemp()) / "s.jsonl"
    auto = ("This session is being continued from a previous conversation. "
            + "warum hast du L-ebbd22 nicht gelesen? " * 2)
    sitzung.write_text("\n".join(json.dumps(z) for z in [
        {"type": "user", "message": {"content": vorgaenger}},
        {"type": "user", "message": {"content": auto}},
    ]) + "\n")
    texte = _texte_geordnet(sitzung)
    assert texte == [vorgaenger], texte
    assert faelle_aus_sitzung(texte, conn) == []

    print("selftest ok (Gegenprobe Vorgaenger vorhanden/fehlend, Form ohne "
          "Kennung, erfundene Kennung, Auto-Zusammenfassung)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sammeln", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    with speicher.lesen() as conn:
        n_transkripte, n_kandidaten, faelle = sammeln(conn)

    print(f"{n_transkripte} Transkripte -> {n_kandidaten} Kandidaten (Beschwerdeform "
          f"+ Kennung im Text) -> {len(faelle)} Faelle (Kandidat mit Vorgaenger UND "
          f"echter Kennung)")
    for f in faelle:
        print(f"  {[z['id'] for z in f['ziele']]} <- {f['prompt'][:80]!r}")

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(
            {"verfahren": "Aufgabentext = Vorgaengernachricht vor einer rueckblickenden "
                          "Beschwerde ('warum hast du X nicht gelesen'); Ziel = die vom "
                          "Betreiber in der Beschwerde genannte Kennung, gegen die "
                          "Datenbank geprueft",
             "transkripte": n_transkripte,
             "kandidaten": n_kandidaten,
             "faelle": faelle},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
