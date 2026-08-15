"""Domaenenpaket-Importer (PLAN_OPENLEHR_2026-08-14.md H8a).

Ein Paket ist eine JSON-Datei mit Regeln und ihren Quellen -- das Format ist
kern/belegvertrag.pruefe_regeln in Dateiform (siehe H8-Abschnitt des Plans):
{"domaene", "bezeichnung", "herkunft", "stand", "quellen", "regeln"}.

Ein Paket ist reine Daten. Es wird nie ausgefuehrt, nie als Code geladen --
importiere()/pruefe() lesen JSON und pruefen, sonst nichts.

Eine Regel ohne belegte Fundstelle wird abgewiesen, nicht stillschweigend
uebernommen (ADR-007). Der Grund ist ein Satz fuer den Menschen, der das
Paket ausgewaehlt hat -- keine Ausnahme, kein Dateiname, keine Zeilennummer.

WIRKUNG NULL (ADR-018, Sperre in docs/PLAN_GESAMT_2026-08-13.md): speichere()
ist die erste Stelle in dieser Datei, die tatsaechlich in den Bestand
schreibt. Vorbild ist kern/regelpaket.py TEIL 3 -- genau dieselben zwei
Felder, genau derselbe Grund:
    norm_rang = NULL, norm_entscheidung = 'keine_norm'
Eine importierte Regel WIRKT NICHT STAERKER als jede andere Notiz
(rangfolge.norm_score(None) == 0.0) und darf nie hoeher als Rang 1/2 ohne
menschlichen Entscheider herein (schema.sql-Trigger
knowledge_nodes_normrang_herkunft_bi/_bu) -- diese Datei fuegt der
bestehenden Schranke nichts hinzu, sie geht ihr nur nicht aus dem Weg (kein
Rang-Feld aus dem Paket wird je gelesen, ganz gleich was darin steht).
Quellen (Belegtexte) bekommen NIE einen Rang -- ein Beleg ist keine Norm.
setze_in_kraft() ist der einzige Weg aus der Wirkung Null heraus: ein
ausdruecklicher, protokollierter Aufruf mit Menschenname und Grund, nie ein
Nebeneffekt von speichere() oder einem zweiten Import desselben Pakets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kern import speicher, zeitmarke
from kern.belegvertrag import pruefe_regeln

_PFLICHTSCHLUESSEL = ("domaene", "quellen", "regeln")

# -- Wirkung Null: Ort und Kennung importierter Domaenenknoten -----------
PARENT_PREFIX = "/domaenen"
PROJECT_ID = "domaenenpaket-import"
_SUMMARY_MAXLEN = 400

# Identisches Muster wie kern/regelpaket.py INSERT_SQL (TEIL 3 dort): kein
# Rang-Feld in der Spaltenliste, kein Weg, ihn ueber ein Paket zu setzen.
_INSERT_SQL = """
INSERT OR IGNORE INTO knowledge_nodes
    (id, path, parent_path, project_id, title, summary, content, level, tags,
     source, confidence, created_at, updated_at, anlass, actor,
     norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:domaene.py',
        'Import aus Domaenenpaket -- Rang muss ein Mensch der Zielinstanz vergeben')
"""


def importiere(pfad: str | Path) -> dict[str, Any]:
    """Liest und prueft ein Domaenenpaket. Liefert immer ein Ergebnis, wirft
    nie: {"angenommen": bool, "anzahl_regeln": int | None, "grund": str | None}."""
    try:
        rohtext = Path(pfad).read_text(encoding="utf-8")
    except OSError:
        return _abgelehnt("Die Paketdatei laesst sich nicht oeffnen.")

    try:
        paket = json.loads(rohtext)
    except json.JSONDecodeError:
        return _abgelehnt("Die Paketdatei ist beschaedigt und laesst sich nicht lesen.")

    return pruefe(paket)


def pruefe(paket: Any) -> dict[str, Any]:
    """Dieselbe Pruefung fuer ein bereits gelesenes Paket. Das atelier waehlt
    die Datei aus und schickt ihren INHALT -- so muss der Dienst nie im
    Dateisystem des Nutzers lesen. Gleiche Rueckgabe wie importiere()."""
    if not isinstance(paket, dict):
        return _abgelehnt("Die Paketdatei enthaelt kein gueltiges Paket.")

    fehlend = [schluessel for schluessel in _PFLICHTSCHLUESSEL if schluessel not in paket]
    if fehlend:
        return _abgelehnt(f"Der Paketdatei fehlen Angaben: {', '.join(fehlend)}.")

    regeln = paket["regeln"]
    quellen = paket["quellen"]
    if not isinstance(regeln, list) or not isinstance(quellen, dict):
        return _abgelehnt("Die Paketdatei ist falsch aufgebaut.")

    try:
        pruefe_regeln(regeln, quellen)
    except (ValueError, KeyError, TypeError):
        return _abgelehnt(_grund_fuer_ablehnung(regeln, quellen))

    # Die Bezeichnung steht im Paket und wird dem Menschen gezeigt ("... gilt
    # jetzt"). Fehlt sie, traegt die Kennung -- nie ein leerer Name.
    bezeichnung = paket.get("bezeichnung") or paket.get("domaene")
    return {
        "angenommen": True,
        "anzahl_regeln": len(regeln),
        "bezeichnung": bezeichnung,
        "grund": None,
    }


def speichere(paket: Any, db: str | Path | None = None) -> dict[str, Any]:
    """Prueft das Paket (siehe pruefe()) und schreibt es NUR bei Annahme in
    den Bestand -- Wirkung Null (ADR-018): jede Zeile bekommt norm_rang=NULL,
    norm_entscheidung='keine_norm'. Ein "norm_rang"-Feld im Paket wird nie
    gelesen, ganz gleich ob es existiert -- dieselbe Entscheidung wie in
    kern/regelpaket.py: das Format traegt kein Rang-Feld, damit nichts zu
    ignorieren ist. Erst setze_in_kraft() macht eine Regel wirksam.

    Idempotent ueber die Primaerschluessel-id (INSERT OR IGNORE): ein
    zweiter Import desselben Pakets legt nichts doppelt an und veraendert
    eine bereits in Kraft gesetzte Regel nicht.

    Rueckgabe: das Ergebnis von pruefe(), erweitert um 'gespeichert' (Anzahl
    neu angelegter Zeilen) und 'uebersprungen' (schon vorhanden). Bei
    Ablehnung sind beide 0 -- ein abgelehntes Paket schreibt nichts."""
    ergebnis = pruefe(paket)
    if not ergebnis["angenommen"]:
        return {**ergebnis, "gespeichert": 0, "uebersprungen": 0}

    domaene_id = paket["domaene"]
    herkunft = paket.get("herkunft") or domaene_id
    bezeichnung = ergebnis["bezeichnung"]
    ts = zeitmarke.jetzt()
    zeilen = [_wurzel_zeile(domaene_id, bezeichnung, ts)]
    zeilen += [_quelle_zeile(domaene_id, herkunft, qid, q, ts) for qid, q in paket["quellen"].items()]
    zeilen += [_regel_zeile(domaene_id, herkunft, r, ts) for r in paket["regeln"]]

    gespeichert = uebersprungen = 0
    with speicher.schreiben(db) as conn:
        for z in zeilen:
            cur = conn.execute(_INSERT_SQL, z)
            if cur.rowcount:
                gespeichert += 1
            else:
                uebersprungen += 1
    return {**ergebnis, "gespeichert": gespeichert, "uebersprungen": uebersprungen}


def setze_in_kraft(
    domaene_id: str,
    wer: str,
    grund: str,
    norm_rang: int,
    *,
    befristet_bis: str | None = None,
    db: str | Path | None = None,
) -> int:
    """Der einzige Weg aus der Wirkung Null heraus (ADR-018): ein
    ausdruecklicher Willensakt eines Menschen der Zielinstanz, protokolliert
    in genau den Feldern, die dafuer vorgesehen sind (norm_entschieden_von,
    norm_entschieden_grund). Betrifft NUR die Regel-Knoten dieser Domaene
    (Tag "art:regel"), nie die Quellen -- eine Quelle ist ein Beleg, keine
    Norm, und bekommt nie einen Rang.

    `norm_rang` ist PFLICHT (kein Vorgabewert): schema.sql verlangt bei
    norm_entscheidung IN ('norm_befristet','norm_unbefristet') einen
    gesetzten Rang (Trigger knowledge_nodes_norm_entscheidung_rang_bi/_bu) --
    ohne diese Pruefung hier wuerde die Datenbank denselben Fehler erst
    spaeter und unleserlicher melden.

    Nur Regeln, die noch 'keine_norm' tragen, werden angefasst -- eine
    bereits in Kraft gesetzte Regel wird von einem zweiten Aufruf nicht
    stillschweigend ueberschrieben (wer das will, aendert norm_rang direkt).
    Wirft nichts fuer eine Domaene ohne (passende) Regeln -- das ist ein
    leeres Ergebnis, kein Fehler. Gibt die Anzahl geaenderter Zeilen zurueck."""
    if norm_rang is None:
        raise ValueError("setze_in_kraft() braucht einen Rang -- keine_norm wird nie automatisch wirksam.")
    if not wer or not wer.strip():
        raise ValueError("setze_in_kraft() braucht einen Menschen, der entscheidet (wer).")
    if not grund or not grund.strip():
        raise ValueError("setze_in_kraft() braucht einen Grund.")

    ts = zeitmarke.jetzt()
    entscheidung = "norm_befristet" if befristet_bis else "norm_unbefristet"
    with speicher.schreiben(db) as conn:
        cur = conn.execute(
            "UPDATE knowledge_nodes SET norm_rang=?, gilt_ab=?, gilt_bis=?, "
            "norm_entscheidung=?, norm_entschieden_von=?, norm_entschieden_grund=?, "
            "updated_at=? WHERE parent_path=? AND norm_entscheidung='keine_norm' "
            "AND tags LIKE '%\"art:regel\"%'",
            (norm_rang, ts, befristet_bis, entscheidung, wer, grund, ts,
             f"{PARENT_PREFIX}/{domaene_id}"),
        )
    return cur.rowcount


def _kuerzen(text: str) -> str:
    text = text or ""
    return text if len(text) <= _SUMMARY_MAXLEN else text[:_SUMMARY_MAXLEN].rstrip() + " [...]"


def _zeile(
    id_: str, path: str, parent_path: str, title: str, summary: str,
    content: str, level: int, tags: list[str], source: str, ts: str,
) -> tuple:
    return (
        id_, path, parent_path, PROJECT_ID, title, summary or title, content,
        level, json.dumps(tags, ensure_ascii=False), source, 0.5, ts, ts,
        "skript", "domaene.py",
    )


def _wurzel_zeile(domaene_id: str, bezeichnung: str, ts: str) -> tuple:
    # parent_path=None statt PARENT_PREFIX: ein eigener globaler "/domaenen"-
    # Wurzelknoten existiert nicht (derselbe Grund wie bei den Blattknoten
    # oben -- ein Ordnerknoten fuer nichts als Hierarchie). NULL ist laut
    # Trigger immer zulaessig, "/" waere die einzige Alternative gewesen.
    return _zeile(
        id_=f"domaene-{domaene_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}",
        parent_path=None,
        title=bezeichnung or domaene_id,
        summary=f"Importierte Domaene '{domaene_id}'.",
        content=None,
        level=0,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}"],
        source=f"domaenenpaket:{domaene_id}",
        ts=ts,
    )


def _quelle_zeile(domaene_id: str, herkunft: str, quelle_id: str, quelle: Any, ts: str) -> tuple:
    # parent_path zeigt auf die Domaenen-Wurzel selbst, nicht auf einen
    # eigenen "quellen"-Ordnerknoten -- schema.sql verlangt (Trigger
    # knowledge_nodes_parent_check_bi/_bu), dass JEDER parent_path auf einen
    # VORHANDENEN Knoten zeigt. Ein Ordnerknoten je Domaene waere ein
    # weiterer Schreibvorgang fuer nichts als Hierarchie -- die Unterscheidung
    # Quelle/Regel traegt bereits das Tag "art:quelle"/"art:regel" (siehe
    # setze_in_kraft(), das genau danach filtert).
    bezeichnung = (quelle.get("bezeichnung") if isinstance(quelle, dict) else None) or quelle_id
    return _zeile(
        id_=f"domaenenquelle-{domaene_id}-{quelle_id}",
        path=f"{PARENT_PREFIX}/{domaene_id}/quellen/{quelle_id}",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=bezeichnung,
        summary=_kuerzen(bezeichnung),
        content=json.dumps(quelle, ensure_ascii=False, sort_keys=True),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "art:quelle"],
        source=f"domaenenpaket:{herkunft}/{domaene_id}/quellen/{quelle_id}",
        ts=ts,
    )


def _regel_zeile(domaene_id: str, herkunft: str, regel: dict[str, Any], ts: str) -> tuple:
    rid = regel["id"]
    fundstelle = regel.get("fundstelle") or rid
    return _zeile(
        id_=f"domaenenregel-{domaene_id}-{rid}",
        path=f"{PARENT_PREFIX}/{domaene_id}/regeln/{rid}",
        parent_path=f"{PARENT_PREFIX}/{domaene_id}",
        title=rid,
        summary=_kuerzen(fundstelle),
        content=json.dumps(regel, ensure_ascii=False, sort_keys=True),
        level=1,
        tags=["domaenenpaket-import", f"domaene:{domaene_id}", "art:regel"],
        source=f"domaenenpaket:{herkunft}/{domaene_id}/regeln/{rid}",
        ts=ts,
    )


def _grund_fuer_ablehnung(regeln: list[dict[str, Any]], quellen: dict[str, Any]) -> str:
    """Findet die erste Regel, die alleine gegen den Vertrag scheitert, und
    benennt sie -- statt die Ausnahme von pruefe_regeln() weiterzureichen."""
    for regel in regeln:
        if not isinstance(regel, dict):
            return "Eine Regel im Paket ist falsch aufgebaut."
        try:
            pruefe_regeln([regel], quellen)
        except (ValueError, KeyError, TypeError):
            name = regel.get("id", "?")
            return f"Die Regel '{name}' nennt keine Quelle, die zu ihrer Fundstelle passt."
    return "Eine Regel im Paket nennt keine passende Quelle."


def _abgelehnt(grund: str) -> dict[str, Any]:
    return {"angenommen": False, "anzahl_regeln": None, "bezeichnung": None, "grund": grund}


__all__ = ["importiere", "pruefe", "speichere", "setze_in_kraft"]
