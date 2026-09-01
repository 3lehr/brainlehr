#!/usr/bin/env python3
"""Fremdbestände holen — mit einer Whitelist, nicht mit einer Säuberung.

ANLASS: Die Lizenzprüfung vom 2026-08-11 (Prüfspruch #7) ergab für FDA MAUDE
CC0 1.0 — urheberrechtlich frei — und trotzdem einen bestätigten Art.-9-Gehalt.
Der Betreiber schlug vor, den Bestand zu nehmen und hinterher zu
anonymisieren. Dagegen sprechen zwei Dinge, und beide sind hier eingebaut
statt bloß aufgeschrieben:

1. Nachträglich entfernen ändert nichts daran, dass es da war. Die
   Verarbeitung beginnt beim Abruf, nicht bei der Auswertung. Und
   pseudonymisierte Daten bleiben personenbezogen (Erwägungsgrund 26,
   Knoten 3e955504 sagt das für den eigenen Enigma-Proxy ausdrücklich).
2. Jede Blacklist hat ein Loch, und bei personenbezogenen Daten ist das Loch
   genau dort (Hausknoten zur Extraktion aus Dokumenten). Eine Whitelist hat
   diese Eigenschaft nicht: was nicht genannt ist, kommt nicht mit.

DER VORBILDFALL AUS DEM EIGENEN HAUS: wohlair hält vier Gesundheitsfelder aus
dem LAN-Abgleich heraus, und zwar nicht per Vorsatz, sondern per
test/privacy/health_fields_stay_local_test.dart — ein Test, der die Feldnamen
im Quelltext SUCHT und fehlschlägt, wenn sie auftauchen (L-e9aa47: ein
Entwurf hätte sie beinahe aufgenommen, ohne dass Compiler oder Analyzer
gemeckert hätten). Dieselbe Bauform hier, eine Ebene früher: die Felder
kommen gar nicht erst herein.

DREI STUFEN, die nacheinander greifen -- Verteidigung in der Tiefe, weil eine
einzelne Bedingung genau einmal falsch sein muss:

  1. PROJEKTION   Aus jedem Datensatz wird NUR gebaut, was in `erlaubt` steht.
                  Kein Filtern, kein Entfernen -- ein neuer Satz aus alten
                  Teilen. Fügt die Quelle morgen ein Feld hinzu, ist es
                  automatisch draußen.
  2. GEGENPROBE   Der gebaute Satz wird danach nach den verbotenen Namen
                  DURCHSUCHT, rekursiv. Findet sich einer, bricht der Import
                  ab -- das fängt den Fall, dass ein erlaubtes Feld ein
                  verbotenes verschachtelt enthält.
  3. GATTUNG      Alles landet als `nachschlagewerk`, nimmt also am
                  automatischen Abruf nicht teil (wie NASA LLIS). Ein
                  Fremdbestand drängt sich nicht auf, man schlägt darin nach.

WAS DAS NICHT LEISTET: Es macht keine Rechtsaussage. Ob der projizierte
Datensatz personenbezogen ist, entscheidet nicht dieses Programm --
kanonymitaet.py sagt aus gutem Grund denselben Satz über sich selbst. Es
stellt nur sicher, dass die Felder, die den Personenbezug tragen, den Rechner
nie erreichen.

Aufruf:
    python3 fremdimport.py --probe maude
    python3 fremdimport.py --lage
    python3 fremdimport.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))

import spracherkennung  # noqa: E402
import speicher  # noqa: E402
import zeitmarke  # noqa: E402

# Je Quelle: was hereindarf, was nie hereindarf, und wie es zu holen ist.
# Die verbotenen Namen stehen ausdrücklich DA, obwohl die Projektion sie schon
# ausschließt -- sie sind die Gegenprobe und zugleich die Dokumentation, wovor
# hier geschützt wird. Wer sie streicht, streicht sie sichtbar.
QUELLEN: dict[str, dict] = {
    "maude": {
        "titel": "FDA MAUDE (openFDA)",
        "lizenz": "CC0 1.0 — Weitergabe frei, Personenbezug bestätigt",
        "abruf": "https://api.fda.gov/device/event.json?limit={n}",
        "wurzel": "results",
        "erlaubt": ["report_number", "event_type", "date_of_event",
                     "date_received", "source_type", "product_problems",
                     "device"],
        # device ist eine Liste von Geräteangaben -- daraus wieder nur dieses:
        "erlaubt_tief": {"device": ["brand_name", "generic_name",
                                     "manufacturer_d_name", "device_report_product_code",
                                     "device_operator", "model_number"]},
        "verboten": ["patient", "patient_age", "patient_sex", "patient_weight",
                      "patient_race", "patient_ethnicity", "mdr_text",
                      "reporter_occupation_code", "sequence_number_outcome",
                      "sequence_number_treatment"],
    },
    "asrs": {
        "titel": "ASRS (NASA/FAA)",
        "lizenz": "de-identifiziert laut Betreiber, Weitergabe frei",
        "abruf": None,   # siehe --lage
        "wurzel": None,
        "erlaubt": [],
        "erlaubt_tief": {},
        "verboten": [],
    },
    "nist": {
        "titel": "NIST",
        "lizenz": "öffentlich, Auflage: Byline + Änderungshinweis",
        "abruf": None,
        "wurzel": None,
        "erlaubt": [],
        "erlaubt_tief": {},
        "verboten": [],
    },
}


# ---------------------------------------------------------------------------
# BDW-P12: der Import erfindet KEINE Herkunft (Auftrag C3, 2026-08-21)
# ---------------------------------------------------------------------------
# Ein fremder Eintrag hat keine Herkunft im Sinne von brainlehr -- keiner von
# acht verglichenen Wettbewerbern erzwingt ein solches Feld. Der Import traegt
# deshalb ein, WOHER ER IHN GEHOLT HAT, und sonst nichts. Die Aussage selbst
# bleibt unbelegt, nur ihr Weg ist bekannt; das ist der ehrliche Zustand und
# nicht der halbe.
#
# Warum das eine PRUEFUNG braucht und nicht bloss eine Konvention: source ist
# ein Pflichtfeld (Trigger knowledge_nodes_source_check_bi). Ein Importweg,
# der es bequem hat, schreibt das hinein, was in der Fremdquelle als "source"
# stand -- und aus einer fremden Behauptung wird eine Herkunft dieses Hauses.
# Genau diese Zeile ist die Stelle, an der BDW-P12 gebrochen wuerde.

IMPORTWEG_PRAEFIX = "importiert aus "

# Woerter, mit denen ein Text eine QUELLE behauptet statt einen WEG zu nennen.
# Bewusst kurz und auf Belegsprache beschraenkt: eine lange Liste faengt
# Dateinamen mit ('iso', 'din') und wuerde ehrliche Wege ablehnen.
_BEHAUPTUNG = ("laut ", "gemaess ", "gemäß ", "quelle:", "§", "bgbl",
               "aktenzeichen", "az.", "urteil", "nach din", "vgl.")


def importherkunft(weg: str, zeitpunkt: str | None = None) -> str:
    """Die einzige zulaessige Herkunft eines Fremdimports: der Weg und der
    Zeitpunkt. 'importiert aus holographic memory_store.db am <ISO>'."""
    if not weg or not weg.strip():
        raise ValueError("Importweg fehlt -- ohne ihn traegt der Eintrag gar nichts")
    ts = zeitpunkt or zeitmarke.jetzt()
    return f"{IMPORTWEG_PRAEFIX}{weg.strip()} am {ts}"


def pruefe_importherkunft(source: str | None) -> None:
    """Wirft ValueError, wenn die Herkunft eine Quelle BEHAUPTET statt den
    Importweg zu nennen. Der Negativfall ist hier der eigentliche Zweck --
    eine Pruefung, die nur Richtiges durchlaesst, ist keine."""
    text = (source or "").strip()
    if not text:
        raise ValueError("Herkunft leer -- ein Fremdimport muss seinen Weg nennen")
    if not text.startswith(IMPORTWEG_PRAEFIX):
        raise ValueError(
            f"Fremdimport behauptet eine Quelle statt seinen Weg zu nennen: {text!r}. "
            f"Zulaessig ist nur die Form '{IMPORTWEG_PRAEFIX}<Weg> am <Zeitpunkt>' "
            "(BDW-P12: die Aussage bleibt unbelegt, nur ihr Weg ist bekannt).")
    klein = text.lower()
    getroffen = [w for w in _BEHAUPTUNG if w in klein]
    if getroffen:
        raise ValueError(
            f"Herkunft traegt Belegsprache {getroffen} und behauptet damit eine "
            f"Quelle: {text!r}. Der Weg genuegt, mehr weiss der Import nicht.")


_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    roh = text.lower()
    for hin, her in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        roh = roh.replace(hin, her)
    return _SLUG.sub("-", roh).strip("-")[:60] or "eintrag"


def eintragen(eintraege, quelle: str, projekt: str, wurzel: str,
              db=None, gattung: str = "nachschlagewerk",
              norm_art: str | None = None, titel_wurzel: str | None = None) -> dict:
    """Schreibt Fremdeintraege als Nachschlagewerk in den Bestand.

    EIN Schreibweg fuer alle Importe (Kataloge wie Fremdsysteme) -- ein
    zweiter waere die Stelle, an der die Herkunftspruefung fehlt.

    `eintraege`: dicts mit titel, text, optional kennung/tags.
    `quelle`: MUSS aus importherkunft() stammen; wird geprueft, nicht geglaubt.
    `gattung`: 'nachschlagewerk' ist Vorgabe und der Grund, warum 951 fremde
    Controls die eigene Trefferquote nicht verduennen (haken/
    knowledge_recall_hook.py filtert ueber gattung_filter.py).
    """
    pruefe_importherkunft(quelle)
    if gattung not in ("nachschlagewerk", "arbeitsbestand"):
        raise ValueError(f"unbekannte Gattung: {gattung!r}")

    saetze = list(eintraege)
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Ein Fremdkatalog ist KEINE Hausnorm: ob und in welchem Rang er hier
    # gilt, entscheidet der Betreiber. 'keine_norm' ist deshalb nicht
    # Bequemlichkeit, sondern dieselbe Zurueckhaltung wie bei der Herkunft --
    # der Import behauptet nichts, auch keine Geltung.
    grund = ("Fremdbestand als Nachschlagewerk eingelesen; ob und in welchem Rang "
             "er hier gilt, entscheidet der Betreiber (BDW-P12)")
    spalten = ("id, path, parent_path, level, title, summary, content, tags, "
               "source, project_id, gattung, anlass, norm_entscheidung, "
               "norm_entschieden_von, norm_entschieden_grund, norm_art, sprache, "
               "created_at, updated_at")
    platz = ", ".join("?" * len(spalten.split(", ")))

    geschrieben = 0
    with speicher.schreiben(db) as conn:
        vorhanden = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
        if wurzel not in vorhanden:
            conn.execute(
                f"INSERT INTO knowledge_nodes ({spalten}) VALUES ({platz})",
                (_kennung(wurzel), wurzel, None, 0,
                 titel_wurzel or wurzel.strip("/"), quelle, "", "[]", quelle,
                 projekt, gattung, "skript", "keine_norm",
                 "skript:kern/fremdimport.py", grund, norm_art,
                 spracherkennung.erkenne(titel_wurzel or ""), jetzt, jetzt))
            vorhanden.add(wurzel)

        for satz in saetze:
            titel = (satz.get("titel") or "").strip() or "ohne Titel"
            text = (satz.get("text") or "").strip()
            pfad = f"{wurzel}/{_slug(satz.get('kennung') or titel)}"
            lauf = 2
            while pfad in vorhanden:
                pfad = f"{wurzel}/{_slug(satz.get('kennung') or titel)}-{lauf}"
                lauf += 1
            vorhanden.add(pfad)
            conn.execute(
                f"INSERT INTO knowledge_nodes ({spalten}) VALUES ({platz})",
                (_kennung(pfad), pfad, wurzel, 1, titel[:200],
                 (text.split("\n")[0] or titel)[:400], text,
                 json.dumps(satz.get("tags") or [], ensure_ascii=False),
                 quelle, projekt, gattung, "skript", "keine_norm",
                 "skript:kern/fremdimport.py", grund, norm_art,
                 spracherkennung.erkenne(f"{titel} {text}"), jetzt, jetzt))
            geschrieben += 1

    return {"knoten": geschrieben, "quelle": quelle, "wurzel": wurzel,
            "gattung": gattung, "projekt": projekt}


def _kennung(pfad: str) -> str:
    """Dieselbe Form wie die Bestands-IDs: 8 Hexstellen, aus dem Pfad
    abgeleitet und damit bei einem zweiten Lauf gleich."""
    return hashlib.sha256(pfad.encode("utf-8")).hexdigest()[:8]


def aus_holographic(memory_store: Path | str, ziel_db=None,
                    grenze: int | None = None) -> dict:
    """holographic (Hermes) haelt alles in EINER SQLite-Datei
    ($HERMES_HOME/memory_store.db, Tabelle `facts`) -- der billigste
    Fremdimport, den es gibt: kein Anbieter, kein Schluessel, keine API.

    Projiziert wie die HTTP-Quellen oben: nur die genannten Spalten entstehen.
    trust_score kommt als Marke MIT, aber nicht als Vertrauen dieses Hauses --
    er ist selbst gemeldet, und ein selbst gemeldeter Wert ist kein Beleg."""
    quelle_datei = Path(memory_store)
    if not quelle_datei.exists():
        raise FileNotFoundError(f"holographic-Speicher nicht gefunden: {quelle_datei}")
    sql = "SELECT content, category, tags, trust_score FROM facts"
    if grenze:
        sql += f" LIMIT {int(grenze)}"
    with speicher.lesen(quelle_datei) as conn:
        zeilen = conn.execute(sql).fetchall()

    eintraege = []
    for i, z in enumerate(zeilen):
        text = (z["content"] or "").strip()
        if not text:
            continue
        marken = [m for m in [z["category"]] if m]
        roh = z["tags"]
        if roh:
            try:
                marken += list(json.loads(roh))
            except (json.JSONDecodeError, TypeError):
                marken += [t.strip() for t in str(roh).split(",") if t.strip()]
        if z["trust_score"] is not None:
            marken.append(f"fremd-trust:{z['trust_score']}")
        eintraege.append({"titel": text.split("\n")[0][:120],
                          "text": text, "tags": marken, "kennung": f"fakt-{i}"})

    return eintragen(eintraege,
                     quelle=importherkunft("holographic memory_store.db"),
                     projekt="holographic", wurzel="/holographic", db=ziel_db,
                     titel_wurzel="holographic (Hermes) -- Fremdimport")


def aus_markdown_ordner(ordner: Path | str, ziel_db=None,
                        projekt: str = "notizen", wurzel: str = "/notizen") -> dict:
    """Ein Verzeichnis voller Notizen (Obsidian, Logseq, oder einfach ein
    Ordner). Kein Anbieter noetig und vermutlich der haeufigste reale Fall.

    Titel ist die erste Ueberschrift, sonst der Dateiname -- geraten wird
    nichts weiter. Unterordner kommen mit; alles andere als .md bleibt
    draussen (dieselbe Whitelist-Haltung wie die Projektion oben)."""
    pfad = Path(ordner)
    if not pfad.is_dir():
        raise NotADirectoryError(f"kein Ordner: {pfad}")
    eintraege = []
    for datei in sorted(pfad.rglob("*.md")):
        text = datei.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        erste = text.splitlines()[0].strip()
        titel = erste.lstrip("#").strip() if erste.startswith("#") else datei.stem
        eintraege.append({"titel": titel, "text": text,
                          "tags": ["markdown"],
                          "kennung": str(datei.relative_to(pfad).with_suffix(""))})
    return eintragen(eintraege,
                     quelle=importherkunft(f"Markdown-Ordner {pfad}"),
                     projekt=projekt, wurzel=wurzel, db=ziel_db,
                     titel_wurzel=f"Notizen aus {pfad.name}")


def projizieren(satz: dict, quelle: dict) -> dict:
    """Baut einen NEUEN Satz aus den erlaubten Teilen. Kein Entfernen: was
    nicht genannt ist, entsteht gar nicht erst."""
    tief = quelle.get("erlaubt_tief", {})
    neu: dict = {}
    for feld in quelle["erlaubt"]:
        if feld not in satz:
            continue
        wert = satz[feld]
        if feld in tief and isinstance(wert, list):
            neu[feld] = [{k: e[k] for k in tief[feld] if k in e}
                          for e in wert if isinstance(e, dict)]
        elif feld in tief and isinstance(wert, dict):
            neu[feld] = {k: wert[k] for k in tief[feld] if k in wert}
        else:
            neu[feld] = wert
    return neu


def _namen(gebilde) -> set[str]:
    """Alle Schlüsselnamen, rekursiv -- auch aus Listen und tiefen Ebenen."""
    raus: set[str] = set()
    if isinstance(gebilde, dict):
        for k, v in gebilde.items():
            raus.add(k)
            raus |= _namen(v)
    elif isinstance(gebilde, list):
        for e in gebilde:
            raus |= _namen(e)
    return raus


def gegenprobe(satz: dict, quelle: dict) -> None:
    """Zweite Stufe: der gebaute Satz darf keinen verbotenen Namen tragen,
    auf keiner Ebene. Bricht ab statt zu bereinigen -- eine Bereinigung an
    dieser Stelle wäre wieder die Blacklist, gegen die die Projektion steht."""
    gefunden = _namen(satz) & set(quelle["verboten"])
    if gefunden:
        raise RuntimeError(
            f"Import abgebrochen: der projizierte Satz traegt verbotene Felder "
            f"{sorted(gefunden)}. Das heisst, ein erlaubtes Feld enthaelt sie "
            "verschachtelt -- die Whitelist gehoert praezisiert, NICHT der Satz "
            "bereinigt.")


def holen(name: str, n: int = 3) -> list[dict]:
    quelle = QUELLEN[name]
    if not quelle["abruf"]:
        raise RuntimeError(f"{quelle['titel']}: kein maschineller Abrufweg hinterlegt "
                            "-- siehe --lage")
    with urllib.request.urlopen(quelle["abruf"].format(n=n), timeout=30) as antwort:
        daten = json.loads(antwort.read().decode("utf-8"))
    saetze = daten[quelle["wurzel"]] if quelle["wurzel"] else daten
    raus = []
    for satz in saetze:
        neu = projizieren(satz, quelle)
        gegenprobe(neu, quelle)
        raus.append(neu)
    return raus


def _selftest() -> None:
    quelle = QUELLEN["maude"]

    roh = {"report_number": "1", "event_type": "Injury",
           "patient": [{"patient_age": "72", "patient_sex": "F"}],
           "mdr_text": [{"text": "Patient verstarb ..."}],
           "device": [{"brand_name": "X", "manufacturer_d_name": "Y",
                        "openfda": {"device_name": "Z"}}]}

    # 1) Projektion: personenbezogene Zweige entstehen gar nicht erst.
    neu = projizieren(roh, quelle)
    assert "patient" not in neu and "mdr_text" not in neu, neu
    assert neu["report_number"] == "1" and neu["event_type"] == "Injury"

    # 2) Auch TIEF wird projiziert: openfda war nicht genannt, also weg.
    assert neu["device"] == [{"brand_name": "X", "manufacturer_d_name": "Y"}], neu["device"]

    # 3) Ein neues Feld der Quelle ist automatisch draussen -- das ist der
    #    ganze Unterschied zur Blacklist.
    neu2 = projizieren({**roh, "neues_feld_von_morgen": "irgendwas"}, quelle)
    assert "neues_feld_von_morgen" not in neu2

    # 4) Gegenprobe schlaegt an, wenn ein verbotener Name doch auftaucht --
    #    hier kuenstlich herbeigefuehrt, weil die Projektion ihn sonst nie
    #    durchliesse. Ohne diesen Fall waere Stufe 2 unbelegt.
    try:
        gegenprobe({"device": [{"brand_name": "X", "patient_age": "72"}]}, quelle)
        raise AssertionError("Gegenprobe liess ein verbotenes Feld durch")
    except RuntimeError as e:
        assert "patient_age" in str(e)

    # 5) Negativfall: ein sauberer Satz darf NICHT anschlagen.
    gegenprobe(neu, quelle)

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def _lage() -> None:
    print("Fremdbestaende -- Stand nach der Lizenzpruefung 2026-08-11:\n")
    for name, q in QUELLEN.items():
        weg = "maschinell abrufbar" if q["abruf"] else "KEIN maschineller Weg hinterlegt"
        print(f"  {name:6s} {q['titel']:22s} {weg}")
        print(f"         Lizenz: {q['lizenz']}")
        if q["verboten"]:
            print(f"         nie importiert: {', '.join(q['verboten'][:5])} ...")
    print("""
ASRS: die Datenbank hat nur eine Suchoberflaeche, keine Programmierschnittstelle
      und keine Massendatei. Der Weg fuehrt ueber einen Ausfuhrlauf der
      Oberflaeche -- eine Handlung, keine Automatik. Genau wie bei NASA LLIS,
      das nur ueber ein fremdes MIT-Repository zu bekommen war.
NIST: der Teilbestand ist im Register unbenannt. Ohne die Entscheidung, WELCHER
      Bestand gemeint ist, gibt es nichts zu holen -- das ist keine technische
      Luecke, sondern eine offene Frage an den Betreiber.""")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", choices=sorted(QUELLEN))
    p.add_argument("--anzahl", type=int, default=3)
    p.add_argument("--lage", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if a.lage:
        _lage()
        return
    if a.probe:
        saetze = holen(a.probe, a.anzahl)
        print(f"{len(saetze)} Satz/Saetze projiziert, Gegenprobe bestanden:\n")
        print(json.dumps(saetze[0], ensure_ascii=False, indent=2)[:900])
        return
    p.print_help()


if __name__ == "__main__":
    main()
