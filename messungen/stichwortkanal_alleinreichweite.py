#!/usr/bin/env python3
"""MESSAUFTRAG 2026-08-12 (Widerspruch d84b6b64 vs. Positivkontrolle 45/31).

Beantwortet GENAU EINE Frage mit Zahl+Nenner: in wie vielen Ziel-Instanzen
ist der beste gelieferte Treffer NUR ueber den Stichwortkanal erreichbar
gewesen -- in der Bedeutungsliste (Vektor allein) also gar nicht oder so
weit hinten, dass er ohne den Stichwortkanal nicht in die Lieferung
gekommen waere?

KEIN UMBAU: rrf_fuse() und fuse_semantic_led() in kern/embeddings.py bleiben
unangetastet. Die Semantik-allein-Lieferung entsteht durch einen
LAUFZEIT-Monkeypatch von embeddings.rrf_fuse in DIESEM Skript (fts-Liste vor
dem Aufruf geleert) -- kein File in kern/ oder haken/ wird geschrieben, die
echte Fusionsfunktion bleibt Zeile fuer Zeile identisch. Nach jedem Lauf wird
zurueckgesetzt.

WIEDERVERWENDET, nicht neu gebaut (Ponytail-Leiter Stufe 2):
- kern/abrufguete.py::abrufen() -- der echte Abrufweg (MIT_PROMPT, Deckel
  MAX_NODES=10/MAX_LESSONS=7 aus dem Betrieb).
- messungen/ausgangsmessung_s12.py::messe() -- Ziel-Instanz-Zaehlung ueber
  einen Korpus mit 1..n Zielen je Fall, exakt der Aufbau, der die 45/205 und
  31/205 der Positivkontrolle vom 2026-08-12 erzeugt hat.
- messungen/hybridvergleich.py::messen() -- liefert fuer den 35-Fall-Korpus
  (pruefkorpus_v2.json) das Feld 'lexikalisch_rettet' bereits fertig: genau
  die Faelle, in denen die Verschmelzung den Fall liefert, aber die
  Vektor-Rangliste allein ihn NICHT enthaelt -- das ist per Definition
  dieselbe Groesse wie hier gefragt.

Aufruf:
    python3 messungen/stichwortkanal_alleinreichweite.py --out runs/<name>.json
    python3 messungen/stichwortkanal_alleinreichweite.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]
_sys.path.insert(0, str(_w / "messungen"))

import argparse
import json
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import embeddings
import speicher
import ausgangsmessung_s12 as _s12mod
from ausgangsmessung_s12 import messe as s12_messe

WURZEL = _w
TZ = timezone(timedelta(hours=2))

# BEFUND WAEHREND DES BAUS, nicht Teil der Fusionslogik, nur diesen
# Beobachtungspunkt betreffend: seit SUCHPFAD_ABRUF=True (haken/
# knowledge_recall_hook.py, Vorgabe seit 2026-08-09) laeuft der echte Abruf
# NICHT mehr durch den einfachen Zwei-Kanal-Kombinierer _combine_channels
# dieser Datei, sondern durch haken/suchpfad_abruf.py::kandidaten(), die
# embeddings.rrf_fuse DREIMAL je Aufruf benutzt: (1) Stichwort-Knoten mit
# Stichwort-Lehren verschmelzen, (2) Bedeutung-Knoten mit Bedeutung-Lehren
# verschmelzen, (3) die eigentliche Stichwort-gegen-Bedeutung-Fusion. Ein
# Monkeypatch, der pauschal das erste Argument jedes rrf_fuse-Aufrufs leert,
# zerstoert damit auch (1) und (2) -- beide haben KEIN Stichwortargument im
# eigentlichen Sinn, ihr erstes Argument ist bei (2) sogar eine
# Bedeutungsliste. Nur der DRITTE Aufruf je abrufen()-Invocation ist die
# gesuchte Stelle. Erstmals bemerkt an einem Ergebnis von 0/44 -- siehe
# Bericht.
_NTER_AUFRUF_IST_DIE_FUSION = 3


@contextmanager
def stichwortkanal_stumm():
    """Waehrend des Kontexts liefert embeddings.rrf_fuse identisch zum
    Original, aber beim DRITTEN rrf_fuse-Aufruf je abrufen()-Invocation
    (die eigentliche Stichwort-gegen-Bedeutung-Fusion, s. Modulkopf) wird
    dessen erstes Argument (keyword_ordered_ids) geleert. Der Zaehler wird
    vor JEDEM abrufen()-Aufruf auf 0 zurueckgesetzt (Patch auf
    ausgangsmessung_s12.abrufen, den Namen, den messe() tatsaechlich
    aufruft -- 'from abrufguete import abrufen' bindet lokal, ein Patch auf
    das abrufguete-Modul selbst haette messe() nicht erreicht). Nach dem
    Kontext ist alles exakt zurueckgesetzt."""
    original_rrf = embeddings.rrf_fuse
    original_abrufen = _s12mod.abrufen
    zaehler = {"n": 0}

    def rrf_patch(fts_ordered_ids, embedding_ordered_ids, **kw):
        zaehler["n"] += 1
        if zaehler["n"] % _NTER_AUFRUF_IST_DIE_FUSION == 0:
            return original_rrf([], embedding_ordered_ids, **kw)
        return original_rrf(fts_ordered_ids, embedding_ordered_ids, **kw)

    def abrufen_patch(task_text):
        zaehler["n"] = 0
        embeddings.rrf_fuse = rrf_patch
        try:
            return original_abrufen(task_text)
        finally:
            embeddings.rrf_fuse = original_rrf

    _s12mod.abrufen = abrufen_patch
    try:
        yield
    finally:
        _s12mod.abrufen = original_abrufen
        embeddings.rrf_fuse = original_rrf


def vergleiche(faelle: list[dict], conn) -> dict:
    """Ein Lauf mit dem echten Betrieb (rrf_fuse, beide Kanaele), ein Lauf
    mit stumm geschaltetem Stichwortkanal -- gleicher Korpus, gleicher
    Deckel, gleiche Vektorrangfolge (die Vektor-Query wird pro Aufruf neu
    an Ollama geschickt, aber dieselbe Anfrage liefert bei bge-m3
    deterministisch dieselbe Einbettung; einzige Fehlerquelle waere ein
    zwischenzeitlich veraenderter Bestand -- siehe Bericht)."""
    basis = s12_messe(faelle, conn)
    with stichwortkanal_stumm():
        semantik_allein = s12_messe(faelle, conn)

    basis_je_ziel = {(e["art"], e["id"], e["haelfte"], e["satzart"]): e["treffer"]
                      for e in basis["einzel"]}
    nur_kanal_faelle = []
    for e in semantik_allein["einzel"]:
        schluessel = (e["art"], e["id"], e["haelfte"], e["satzart"])
        basis_treffer = basis_je_ziel.get(schluessel)
        if basis_treffer is True and e["treffer"] is False:
            nur_kanal_faelle.append(
                {"art": e["art"], "id": e["id"], "satzart": e["satzart"]})

    gesamt_basis = sum(1 for v in basis_je_ziel.values() if v is True)
    return {
        "ziel_instanzen_gesamt": len(basis["einzel"]),
        "treffer_betrieb_rrf_fuse": gesamt_basis,
        "treffer_semantik_allein": sum(1 for e in semantik_allein["einzel"] if e["treffer"]),
        "nur_ueber_stichwortkanal_erreichbar": len(nur_kanal_faelle),
        "nur_ueber_stichwortkanal_erreichbar_faelle": nur_kanal_faelle,
    }


def _selftest() -> None:
    """Netzloser Selbsttest: nur der DRITTE rrf_fuse-Aufruf je abrufen()-
    Invocation wird geleert, Aufrufe 1+2 bleiben unangetastet (Mutationsprobe:
    ein Patch, der pauschal jeden Aufruf leert, wuerde hier durchfallen --
    genau der Fehler, der beim echten Lauf 0/44 statt eines plausiblen Werts
    ergab, s. Modulkopf)."""
    aufrufe = []
    original_rrf = embeddings.rrf_fuse
    original_abrufen = _s12mod.abrufen

    def spion(fts_ordered_ids, embedding_ordered_ids, **kw):
        aufrufe.append(list(fts_ordered_ids))
        return original_rrf(fts_ordered_ids, embedding_ordered_ids, **kw)

    def fake_orig(task_text):
        # Simuliert haken/suchpfad_abruf.py::kandidaten(): drei rrf_fuse-
        # Aufrufe je abrufen()-Invocation, genau wie im echten Betrieb --
        # (1) Stichwort-Knoten+Lehren, (2) Bedeutung-Knoten+Lehren,
        # (3) die eigentliche Stichwort-gegen-Bedeutung-Fusion.
        embeddings.rrf_fuse(["kw-node"], ["x"], embedding_weight=1.0)
        embeddings.rrf_fuse(["x"], ["emb-node"], embedding_weight=1.0)
        embeddings.rrf_fuse(["kw-final"], ["emb-final"], embedding_weight=1.0)
        return [], []

    _s12mod.abrufen = fake_orig
    embeddings.rrf_fuse = spion
    try:
        with stichwortkanal_stumm():
            _s12mod.abrufen("aufgabe-1")
            _s12mod.abrufen("aufgabe-2")
    finally:
        _s12mod.abrufen = original_abrufen
        embeddings.rrf_fuse = original_rrf

    erwartet = [["kw-node"], ["x"], [], ["kw-node"], ["x"], []]
    assert aufrufe == erwartet, f"nur der 3./6. Aufruf haette geleert werden duerfen, war {aufrufe}"
    assert embeddings.rrf_fuse is original_rrf, "rrf_fuse wurde nicht zurueckgesetzt"
    assert _s12mod.abrufen is original_abrufen, "abrufen wurde nicht zurueckgesetzt"

    # vergleiche(): Ziel wird in beiden Laeufen gefunden -> nicht gezaehlt;
    # Ziel nur im Betrieb gefunden -> gezaehlt.
    import unittest.mock as mock
    faelle = [{"prompt": "p1", "satzart": "auftrag",
               "ziele": [{"art": "knoten", "id": "/x/a"}]},
              {"prompt": "p2", "satzart": "auftrag",
               "ziele": [{"art": "knoten", "id": "/x/b"}]}]

    rufe = {"n": 0}

    def fake_messe(faelle_, conn_):
        rufe["n"] += 1
        # Erster Aufruf = Betrieb (beide Kanaele): beide Ziele gefunden.
        # Zweiter Aufruf = Stichwort stumm: /x/a verliert seinen einzigen Treffer.
        treffer_a = True
        treffer_b = True if rufe["n"] == 1 else False
        return {"einzel": [
            {"art": "knoten", "id": "/x/a", "haelfte": "behandelt", "satzart": "auftrag", "treffer": treffer_a},
            {"art": "knoten", "id": "/x/b", "haelfte": "behandelt", "satzart": "auftrag", "treffer": treffer_b},
        ]}

    with mock.patch("__main__.s12_messe", fake_messe):
        ergebnis = vergleiche(faelle, conn=None)
    assert ergebnis["nur_ueber_stichwortkanal_erreichbar"] == 1, ergebnis
    assert ergebnis["nur_ueber_stichwortkanal_erreichbar_faelle"][0]["id"] == "/x/b", ergebnis

    # Gegenprobe: kein Unterschied zwischen den Laeufen -> 0 gezaehlt.
    rufe["n"] = 0

    def fake_messe_gleich(faelle_, conn_):
        return {"einzel": [
            {"art": "knoten", "id": "/x/a", "haelfte": "behandelt", "satzart": "auftrag", "treffer": True},
        ]}

    with mock.patch("__main__.s12_messe", fake_messe_gleich):
        ergebnis2 = vergleiche(faelle, conn=None)
    assert ergebnis2["nur_ueber_stichwortkanal_erreichbar"] == 0, ergebnis2

    print("selftest ok (Monkeypatch leert fts-Liste + Rueckweg belegt, "
          "vergleiche() zaehlt Verlust und Gegenprobe zaehlt nicht)", file=_sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=_Path,
                    default=WURZEL / "runs" / "echtkorpus_2026-08-12T1000.json")
    p.add_argument("--out", type=_Path)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--limit", type=int, default=None,
                    help="nur die ersten N Faelle der Korpusdatei (Zeitbudget) -- "
                         "kein Zufallszug, Reihenfolge der Datei, im Bericht als "
                         "Teilmenge auszuweisen.")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    faelle = json.loads(a.korpus.read_text(encoding="utf-8"))["faelle"]
    if a.limit is not None:
        faelle = faelle[:a.limit]
    with speicher.lesen() as conn:
        ergebnis = vergleiche(faelle, conn)

    print(f"Korpus: {a.korpus.name}  ({len(faelle)} Faelle)")
    print(f"Ziel-Instanzen gesamt: {ergebnis['ziel_instanzen_gesamt']}")
    print(f"Treffer Betrieb (rrf_fuse, beide Kanaele): {ergebnis['treffer_betrieb_rrf_fuse']}")
    print(f"Treffer Semantik allein (Stichwortkanal stumm): {ergebnis['treffer_semantik_allein']}")
    print(f"NUR ueber Stichwortkanal erreichbar: "
          f"{ergebnis['nur_ueber_stichwortkanal_erreichbar']} von "
          f"{ergebnis['ziel_instanzen_gesamt']}")

    if a.out:
        ausgabe = {
            "frage": "In wie vielen Ziel-Instanzen ist der beste gelieferte Treffer NUR "
                     "ueber den Stichwortkanal erreichbar (Vektor allein liefert ihn nicht "
                     "innerhalb des Betriebsdeckels)?",
            "verfahren": "kern/abrufguete.py::abrufen() zweimal je Fall: einmal unveraendert "
                         "(Betrieb, rrf_fuse), einmal mit embeddings.rrf_fuse per "
                         "Laufzeit-Monkeypatch auf leere fts-Liste -- kern/, haken/ unveraendert "
                         "auf der Platte. Zaehlung je Ziel-Instanz wie "
                         "messungen/ausgangsmessung_s12.py::messe().",
            "korpus": a.korpus.name,
            "korpus_limit": a.limit,
            "korpus_faelle_gesamt_in_datei": len(json.loads(a.korpus.read_text(encoding="utf-8"))["faelle"]),
            "code_stand": "51927d1 (Zweig brainlehr/b4-ausweis)",
            "erzeugt_am": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z"),
            **ergebnis,
        }
        a.out.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\ngeschrieben: {a.out}")


if __name__ == "__main__":
    main()
