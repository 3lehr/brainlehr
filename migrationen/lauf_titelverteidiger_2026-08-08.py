"""Einmal-Laufskript: heutigen Stand als Titelverteidiger festhalten (Auftrag
2026-08-08). Fahrt pruefkorpus_v3.run_repeated() gegen eine KOPIE von
knowledge.db (Umlenkung von hook.DB, wie bereits in knowledge_recall_replay.py
vorgemacht -- s. dessen _replay()), NIE gegen die Live-DB (L-ecf08c).

Nur lesen/aufrufen von pruefkorpus_v3.py, keine Aenderung dort.
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

import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# Die Repo-WURZEL, nicht der Ordner dieses Skripts. Bis zum
# Wurzelordnungs-Umzug am 2026-08-10 lagen beide am selben Ort und
# der Unterschied fiel nicht auf; seither zeigte der Pfad auf
# messungen/ bzw. migrationen/ und die Datenablage runs/ war weg.
# _w wird oben bereits an schema.sql ermittelt -- an einem Merkmal
# der Wurzel statt an einer Ebenenzahl, damit der naechste Umzug
# nicht dieselbe Stille erzeugt.
SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))

import knowledge_recall_hook as hook  # noqa: E402
import messparameter  # noqa: E402
import pruefkorpus_v3 as pk  # noqa: E402
from meisterschaft import titelverteidiger_festhalten, titelverteidiger_lesen, herausforderer_bewerten  # noqa: E402

LIVE_DB = SHARED_KNOWLEDGE / "knowledge.db"
SCRATCH_DB = Path("/private/tmp/claude-501/-Volumes-daten-Begod2026-fahrtenbuch/"
                   "43459d92-9f7a-4fca-b8cb-3f4ed6709f30/scratchpad/knowledge_meisterschaft_kopie.db")
N_RUNS = 5


def _bestand(db_path: Path) -> int:
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    finally:
        con.close()


def main() -> None:
    live_vorher = (LIVE_DB.stat().st_size, LIVE_DB.stat().st_mtime)
    print("LIVE-DB vorher:", live_vorher)

    # Umlenkung -- Modul-globale DB-Konstanten auf die Kopie zeigen lassen,
    # exakt das Muster aus knowledge_recall_replay.py._replay().
    saved_hook_db, saved_mp_db = hook.DB, messparameter.DB
    hook.DB = str(SCRATCH_DB)
    messparameter.DB = SCRATCH_DB
    print("Umlenkung: hook.DB =", hook.DB)
    print("Umlenkung: messparameter.DB =", messparameter.DB)
    assert hook.DB == str(SCRATCH_DB) and str(messparameter.DB) == str(SCRATCH_DB), "Umlenkung griff nicht"

    try:
        bestand_vorher = _bestand(SCRATCH_DB)
        print("Bestand Kopie vorher:", bestand_vorher)

        t0 = time.time()
        out = pk.run_repeated(
            model=pk.CAL_MODEL,
            out_path=SHARED_KNOWLEDGE / "runs" / "titelverteidiger_2026-08-08.json",
            n_runs=N_RUNS,
        )
        dauer = time.time() - t0
        print(f"Gesamtdauer {N_RUNS} Laeufe: {dauer:.1f}s ({dauer / N_RUNS:.1f}s/Lauf im Schnitt)")

        bestand_nachher = _bestand(SCRATCH_DB)
        print("Bestand Kopie nachher:", bestand_nachher)
        print("Bestand Kopie unveraendert:", bestand_vorher == bestand_nachher)
        print("run_repeated vorher/nachher/entfernt:", out["vorher"], out["nachher"], out["entfernt"])

        live_nach_messung = (LIVE_DB.stat().st_size, LIVE_DB.stat().st_mtime)
        print("LIVE-DB nach der Messphase (vor Titel-Schreibvorgang):", live_nach_messung)
        print("LIVE-DB durch Messphase unveraendert:", live_vorher == live_nach_messung)

        if out.get("aborted"):
            print("ABGEBROCHEN:", out.get("grund"))
            (SHARED_KNOWLEDGE / "runs" / "titelverteidiger_2026-08-08_roh.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            return

        # Rohe Tabelle je Lauf.
        laeufe_roh = []
        print("\nje Lauf: n, trefferquote, schweigequote, kosten(s)")
        for l in out["laeufe"]:
            rows = l["rows"]
            loesbar = [r for r in rows if r["erwartete_zahl"] is not None]
            eich = [r for r in rows if r["erwartete_zahl"] is None]
            treffer = sum(1 for r in loesbar if r["mit_bestanden"]) / len(loesbar) if loesbar else None
            schweigen = sum(1 for r in eich if r["mit_bestanden"]) / len(eich) if eich else None
            print(f"  lauf {l['lauf_nr']}: n_loesbar={len(loesbar)} n_eich={len(eich)} "
                  f"trefferquote={treffer} schweigequote={schweigen}")
            laeufe_roh.append({"lauf_nr": l["lauf_nr"], "trefferquote": treffer, "schweigequote": schweigen})

        # kosten-Proxy: Gesamtdauer gleichmaessig auf n_runs verteilt (kein
        # Token-Kosten-Zaehler vorhanden -- Sekunden sind der einzige echte
        # Messwert, den dieser Lauf liefert).
        kosten_je_lauf = dauer / N_RUNS
        laeufe_fuer_titel = [
            {"trefferquote": lr["trefferquote"], "schweigequote": lr["schweigequote"], "kosten": kosten_je_lauf}
            for lr in laeufe_roh if lr["trefferquote"] is not None and lr["schweigequote"] is not None
        ]
        print("\nLaeufe fuer Titelverteidiger (trefferquote/schweigequote/kosten):")
        for l in laeufe_fuer_titel:
            print(" ", l)

        werte_tq = [l["trefferquote"] for l in laeufe_fuer_titel]
        werte_sq = [l["schweigequote"] for l in laeufe_fuer_titel]
        print(f"\nSpannweite trefferquote: {max(werte_tq) - min(werte_tq):.4f} "
              f"(min={min(werte_tq):.4f} max={max(werte_tq):.4f})")
        print(f"Spannweite schweigequote: {max(werte_sq) - min(werte_sq):.4f} "
              f"(min={min(werte_sq):.4f} max={max(werte_sq):.4f})")

        if bestand_vorher != bestand_nachher:
            print("\nABBRUCH TITEL: Bestand der Kopie hat sich veraendert -- "
                  "Streuung waere nicht von Mechanik trennbar.")
            return

        einstellung = messparameter.schnappschuss()
        rec = titelverteidiger_festhalten(
            einstellung=einstellung,
            laeufe=laeufe_fuer_titel,
            pruefmenge="pruefkorpus_v3",
            bereich="abruf",
            db_path=LIVE_DB,  # knowledge_config liegt in der LIVE-DB (Konfig-Tabelle, kein Bestand)
        )
        print("\nTitelverteidiger festgehalten, roh zurueckgelesen:")
        gelesen = titelverteidiger_lesen(bereich="abruf", db_path=LIVE_DB)
        print(json.dumps(gelesen, ensure_ascii=False, indent=2))

        # Gegenprobe: Titelverteidiger gegen sich selbst -- darf NIE gewinnen.
        gegenprobe = herausforderer_bewerten(
            einstellung=einstellung, laeufe=laeufe_fuer_titel,
            an_pruefmenge_nicht_angepasst=True, bereich="abruf", db_path=LIVE_DB)
        print("\nGEGENPROBE (Titelverteidiger vs. sich selbst):")
        print(json.dumps(gegenprobe, ensure_ascii=False, indent=2))
        print("\nGEGENPROBE-URTEIL:", gegenprobe["urteil"],
              "(muss 'unentschieden' oder 'verloren' sein, NIE 'gewonnen')")

    finally:
        hook.DB, messparameter.DB = saved_hook_db, saved_mp_db

    live_nachher = (LIVE_DB.stat().st_size, LIVE_DB.stat().st_mtime)
    print("\nLIVE-DB nach ALLEM (inkl. Titel-Schreibvorgang in knowledge_config):", live_nachher)
    print("LIVE-DB Groesse unveraendert ggue. vorher:", live_vorher[0] == live_nachher[0])
    print("LIVE-DB mtime unveraendert ggue. vorher:", live_vorher[1] == live_nachher[1],
          "-- Aenderung falls False ist der ERWARTETE, gezielte knowledge_config-Schreibvorgang "
          "von titelverteidiger_festhalten(), kein Bestand-Nebeneffekt (siehe Bestand-Zeilen oben)")


if __name__ == "__main__":
    main()
