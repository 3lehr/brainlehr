#!/usr/bin/env python3
"""Ein Plan ist eine FOLGE, der Wissensspeicher eine MENGE (Auftrag
2026-08-09). Heute steht "S3 nach S1" nur als Prosa in docs/PLAN_*.md und ist
damit nicht pruefbar. Dieses Skript liest die Reihenfolge aus den Abschnitten
und legt sie -- auf Wunsch -- als Kanten in knowledge_relations ab, wo ein
Melder sie gegen die Wirklichkeit halten kann.

Zwei Kantenarten, unterschiedlich streng:

  entstand_nach -- Dokumentreihenfolge, immer gesetzt zwischen aufeinander-
      folgenden Abschnitten. Bedeutet ausdruecklich nur "so aufgeschrieben",
      kein Anspruch (Lehre L-dd61a0: die Nummer ist keine Abhaengigkeit).
  bindend_vor -- nur zwischen Abschnitten, zu denen der Text selbst eine
      Reihenfolge behauptet ("nach S1", "vor S4", ...). PFLICHT: ein
      woertliches Zitat als evidence, sonst darf die Kante nicht entstehen
      (siehe _kante_bindend_vor -- das ist die einzige Stelle in dieser
      Datei, die diesen Kantentyp schreiben kann).

ABWEICHUNG vom Auftrag, gemessen beim Nachsehen in knowledge_mcp_server.py:
RELATION_TYPES (dort Zeile ~142) enthaelt weder 'entstand_nach' noch
'bindend_vor' -- ein Aufruf von knowledge_relation_add() mit einem dieser
Typen wirft "Invalid relation type", unabhaengig vom DB-Schema. Der Bestand
selbst zeigt aber Kantentypen ausserhalb dieser Liste (aehnlich_bedeutung,
lesson_mentions_file) -- sie muessen ueber einen anderen Schreibweg entstanden
sein, direkt in der Tabelle. Da knowledge_mcp_server.py laut Auftrag nicht
angefasst werden darf, schreibt --schreiben deshalb direkt in
knowledge_relations (gleiche Spalten wie knowledge_relation_add), statt die
dortige Funktion aufzurufen. Knoten legt es dagegen ganz normal ueber
knowledge_add() an -- dort passt kein Typ-Whitelist-Konflikt entgegen.

Aufruf:
    python3 planordnung.py --vorschlag     # nur lesen, nichts schreiben
    python3 planordnung.py --schreiben     # Knoten + Kanten anlegen
    python3 planordnung.py --selftest
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

import argparse
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import planbindung  # reuse: _abschnitte() erkennt S-Kopf + Abschnittsgrenzen,
                     # inkl. der gehaerteten Regel "Grenze ist JEDE Ueberschrift"

WURZEL = _w

# Dateinamen, die ein Abschnitt nennt: endet auf .py/.md/.json/.jsonl, oder
# liegt in haken/ bzw. runs/ (auch ohne dieser Endungen, z.B. runs/2026...).
_DATEI_RE = re.compile(
    r"\b(?:[\w.-]+/)*[\w.-]+\.(?:py|md|json|jsonl)\b"
    r"|\b(?:haken|runs)/[\w./-]+"
)

# Anhaltspunkte fuer eine Reihenfolgeaussage (Auftrag, Punkt 1c). "nach S<n>"
# und "vor S<n>" liefern zusaetzlich eine LESBARE RICHTUNG; die uebrigen
# Trigger markieren nur, dass der Satz zur Sichtung gehoert.
_TRIGGER_RE = re.compile(
    r"Reihenfolge:|bindend|\bzuerst\b|\bzuletzt\b|\bnach\s+S\d|\bvor\s+S\d",
    re.IGNORECASE,
)
_NACH_RE = re.compile(r"\bnach\s+(S\d+[a-z]?)\b")
_VOR_RE = re.compile(r"\bvor\s+(S\d+[a-z]?)\b")

_SATZ_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Fund:
    zitat: str
    quelle: str | None = None  # Abschnittskennung, die VOR ziel liegen soll
    ziel: str | None = None


def _saetze(text: str) -> list[str]:
    return [s.strip() for s in _SATZ_RE.split(text) if s.strip()]


def _dateien_in(text: str) -> list[str]:
    return sorted(set(_DATEI_RE.findall(text)))


def _reihenfolge_funde(ab: "planbindung.Abschnitt") -> list[Fund]:
    """Ein Fund pro Satz, der einen Trigger enthaelt. 'nach S<n>' bzw.
    'vor S<n>' im selben Satz liefern die Richtung dazu; sonst bleibt sie
    unklar (quelle=ziel=None) und der Fund taugt nur zur Sichtung, nicht zur
    Kante."""
    funde: list[Fund] = []
    for satz in _saetze(ab.text):
        if not _TRIGGER_RE.search(satz):
            continue
        m_nach = _NACH_RE.search(satz)
        m_vor = _VOR_RE.search(satz)
        if m_nach:
            funde.append(Fund(zitat=satz, quelle=m_nach.group(1), ziel=ab.kennung))
        elif m_vor:
            funde.append(Fund(zitat=satz, quelle=ab.kennung, ziel=m_vor.group(1)))
        else:
            funde.append(Fund(zitat=satz))
    return funde


@dataclass
class DateiAnalyse:
    datei: Path
    abschnitte: list = field(default_factory=list)
    funde_je: list = field(default_factory=list)     # list[list[Fund]], parallel zu abschnitte
    dateien_je: list = field(default_factory=list)    # list[list[str]], parallel zu abschnitte


def _analysiere(datei: Path) -> DateiAnalyse:
    abschnitte = planbindung._abschnitte(datei)
    return DateiAnalyse(
        datei=datei,
        abschnitte=abschnitte,
        funde_je=[_reihenfolge_funde(ab) for ab in abschnitte],
        dateien_je=[_dateien_in(ab.text) for ab in abschnitte],
    )


def _gerichtete_indexpaare(a: DateiAnalyse) -> set[frozenset]:
    """Indexpaare (nicht Kennungspaare!) -- PLAN_DESTILLE_2026-08-09.md
    enthaelt 'S12' zweimal (zwei verschiedene Ueberschriften mit derselben
    Kennung), ein Kennungs-Dict wuerde die zweite stillschweigend
    verschlucken. Ist die referenzierte Kennung mehrdeutig, werden
    vorsichtshalber ALLE passenden Indexpaare als gerichtet markiert --
    lieber ein Paar zu wenig in der Parallel-Liste als ein falsches drin."""
    paare = set()
    for funde in a.funde_je:
        for f in funde:
            if not (f.quelle and f.ziel):
                continue
            quellen = [i for i, ab in enumerate(a.abschnitte) if ab.kennung == f.quelle]
            ziele = [i for i, ab in enumerate(a.abschnitte) if ab.kennung == f.ziel]
            for qi in quellen:
                for zi in ziele:
                    paare.add(frozenset((qi, zi)))
    return paare


def _parallel_indexpaare(a: DateiAnalyse) -> list[tuple[int, int]]:
    """Indexpaare ohne Reihenfolgeaussage UND ohne gemeinsame Datei --
    Pflichtfaelle (c)/(d) aus dem Auftrag. Index statt Kennung, aus
    demselben Grund wie bei _gerichtete_indexpaare (doppelte Kennungen in
    PLAN_DESTILLE_2026-08-09.md, siehe dort)."""
    gerichtet = _gerichtete_indexpaare(a)
    n = len(a.abschnitte)
    ergebnis = []
    for i in range(n):
        for j in range(i + 1, n):
            if frozenset((i, j)) in gerichtet:
                continue
            if set(a.dateien_je[i]) & set(a.dateien_je[j]):
                continue
            ergebnis.append((i, j))
    return ergebnis


def _parallel_paare(a: DateiAnalyse) -> list[tuple[str, str]]:
    """Wie _parallel_indexpaare, aber als Kennungspaare -- praktisch fuer
    Tests ohne doppelte Kennungen; fuer die Anzeige nimmt _drucke die
    index-basierte Variante direkt, um Duplikate zu unterscheiden."""
    return [(a.abschnitte[i].kennung, a.abschnitte[j].kennung) for i, j in _parallel_indexpaare(a)]


def _label(a: DateiAnalyse, index: int) -> str:
    """Kennung, mit Index ergaenzt, WENN sie in dieser Datei mehrfach
    vorkommt (PLAN_DESTILLE_2026-08-09.md hat 'S1b' und 'S12' je zweimal --
    zwei verschiedene Ueberschriften, dieselbe Kennung). Ohne diese
    Ergaenzung waere die Parallel-Liste nicht mehr auseinanderzuhalten,
    welches der beiden Vorkommen gemeint ist."""
    kennung = a.abschnitte[index].kennung
    mehrfach = sum(1 for ab in a.abschnitte if ab.kennung == kennung) > 1
    return f"{kennung}#{index}" if mehrfach else kennung


def _drucke(a: DateiAnalyse) -> int:
    """Gibt die Zahl der Reihenfolge-Funde in dieser Datei zurueck."""
    print(f"\n== {a.datei.name} ({len(a.abschnitte)} Abschnitte) ==")
    gesamt_funde = 0
    for idx, (ab, funde, dfiles) in enumerate(zip(a.abschnitte, a.funde_je, a.dateien_je)):
        print(f"\n{_label(a, idx)} · {ab.titel}")
        if dfiles:
            print(f"  Dateien: {', '.join(dfiles)}")
        for f in funde:
            gesamt_funde += 1
            if f.quelle and f.ziel:
                print(f"  Reihenfolge: {f.quelle} vor {f.ziel} -- \"{f.zitat}\"")
            else:
                print(f"  Reihenfolge (Richtung unklar): \"{f.zitat}\"")
    print("\n  Parallel moeglich:")
    paare = _parallel_indexpaare(a)
    if paare:
        for i, j in paare:
            print(f"    {_label(a, i)} <-> {_label(a, j)}")
    else:
        print("    (keine)")
    return gesamt_funde


def _vorschlag(plan_dir: Path) -> None:
    dateien = sorted(plan_dir.glob("PLAN_*.md"))
    if not dateien:
        print(f"keine Plandateien unter {plan_dir}")
        return
    gesamt_abschnitte = 0
    gesamt_funde = 0
    for datei in dateien:
        a = _analysiere(datei)
        gesamt_abschnitte += len(a.abschnitte)
        gesamt_funde += _drucke(a)
    print(f"\n{gesamt_abschnitte} Abschnitte insgesamt, {gesamt_funde} Reihenfolge-Funde.")


# ---------------------------------------------------------------------------
# --schreiben: Knoten ueber knowledge_add(), Kanten direkt in
# knowledge_relations (siehe Modul-Docstring, Abweichung vom Auftrag).
# ---------------------------------------------------------------------------

def _kante_vorhanden(conn, quelle_pfad: str, ziel_pfad: str, relation_type: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM knowledge_relations WHERE source_path=? AND target_path=? AND relation_type=?",
        (quelle_pfad, ziel_pfad, relation_type),
    ).fetchone() is not None


def _kante_insert(conn, quelle_pfad: str, ziel_pfad: str, relation_type: str,
                   weight: float, evidence: str) -> None:
    if _kante_vorhanden(conn, quelle_pfad, ziel_pfad, relation_type):
        return  # Pflichtfall (e): Wiederholungslauf erzeugt keine Dubletten.
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO knowledge_relations
           (id, source_path, target_path, relation_type, confidence, weight, evidence, source,
            creator, model, session, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (f"R-{uuid.uuid4().hex[:8]}", quelle_pfad, ziel_pfad, relation_type,
         1.0, float(weight), evidence, "planordnung.py", "skript", None, None, ts, ts),
    )


def _kante_entstand_nach(conn, quelle_pfad: str, ziel_pfad: str, nummer: int) -> None:
    """Nur Dokumentreihenfolge -- KEIN evidence noetig, wie im Auftrag
    verlangt."""
    _kante_insert(conn, quelle_pfad, ziel_pfad, "entstand_nach", weight=nummer, evidence="")


def _kante_bindend_vor(conn, quelle_pfad: str, ziel_pfad: str, zitat: str) -> None:
    """Die harte Grenze aus dem Auftrag: zitat ist ein PFLICHT-Parameter
    ohne Default, und wird VOR jeder DB-Beruehrung geprueft. Diese Funktion
    ist die einzige Stelle in dieser Datei, die eine 'bindend_vor'-Zeile
    schreiben kann -- es gibt keinen zweiten Pfad, der die Pruefung umgehen
    koennte. Eine echte Typpruefung (die einen leeren String zur
    Compile-Zeit ausschliesst) gaebe es nur mit einem eigenen Werttyp --
    fuer eine einzelne Pruefstelle overkill, die Laufzeitpruefung reicht."""
    zitat = zitat.strip()
    if not zitat:
        raise ValueError(
            "bindend_vor ohne Zitat -- keine Kante ohne Beleg (harte Grenze aus dem Auftrag)."
        )
    _kante_insert(conn, quelle_pfad, ziel_pfad, "bindend_vor", weight=1.0, evidence=zitat)


def _knoten_sicherstellen(kms, conn, ast: str, ab, plan_stem: str, datei: Path) -> str:
    """Legt den Knoten fuer diesen Abschnitt an, falls er noch nicht
    existiert (idempotent -- Pflichtfall e). Gibt den Knotenpfad zurueck."""
    slug = kms._slugify(f"{ab.kennung} {ab.titel}")
    node_path = f"{ast}/{slug}"
    vorhanden = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE path=?", (node_path,)
    ).fetchone()
    if vorhanden:
        return vorhanden[0]
    ergebnis = kms.knowledge_add(
        parent_path=ast,
        title=f"{ab.kennung} · {ab.titel}",
        summary=ab.titel,
        content=ab.text,
        neuer_ast=True,
        tags=["plan", plan_stem],
        source=f"erzeugt aus {datei} Abschnitt {ab.kennung} (planordnung.py)",
        anlass="skript",
        norm_entscheidung="keine_norm",
        norm_entschieden_grund=(
            "Plan-Abschnitt automatisch uebernommen -- die Reihenfolge ist die "
            "Aussage, die dieser Knoten traegt, kein eigener Normanspruch."
        ),
    )
    if "error" in ergebnis:
        raise RuntimeError(f"Knoten fuer {ab.kennung} in {datei.name} nicht angelegt: {ergebnis['error']}")
    return ergebnis["path"]


def _schreiben_datei(kms, conn, datei: Path) -> None:
    a = _analysiere(datei)
    plan_stem = datei.stem
    # kms.knowledge_add() normalisiert (lowercased/slugified) einen Astpfad,
    # der beim Anlegen noch nicht existiert (siehe _normalize_path dort,
    # ausgeloest ueber neuer_ast=True) -- OHNE dieselbe Normalisierung HIER
    # wuerde der Vorab-Check in _knoten_sicherstellen einen anderen Pfad
    # abfragen als tatsaechlich gespeichert wird, und ein zweiter Lauf haette
    # "Node already exists" auf einem Pfad geworfen, den er selbst nie
    # gefunden hat (gemessen: genau dieser rot-Fall im Selbsttest --
    # "Node already exists at path: /plaene/plan-test/s1-erster-schritt"
    # beim zweiten Lauf, ausgeloest durch den Case-Unterschied PLAN_TEST
    # gegen plan-test).
    ast = kms._normalize_path(f"/plaene/{plan_stem}")
    pfade: dict[str, str] = {}
    for ab in a.abschnitte:
        pfade[ab.kennung] = _knoten_sicherstellen(kms, conn, ast, ab, plan_stem, datei)
        conn.commit()

    for i in range(1, len(a.abschnitte)):
        vorher, jetzt = a.abschnitte[i - 1], a.abschnitte[i]
        _kante_entstand_nach(conn, pfade[vorher.kennung], pfade[jetzt.kennung], i)

    for funde in a.funde_je:
        for f in funde:
            if f.quelle and f.ziel and f.quelle in pfade and f.ziel in pfade:
                _kante_bindend_vor(conn, pfade[f.quelle], pfade[f.ziel], f.zitat)
    conn.commit()


def _schreiben(plan_dir: Path) -> None:
    import knowledge_mcp_server as kms  # lazy: DB_PATH wird erst BEIM IMPORT fixiert
    conn = kms.get_db()
    try:
        for datei in sorted(plan_dir.glob("PLAN_*.md")):
            _schreiben_datei(kms, conn, datei)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Selbsttest -- eigene Beispieldateien in einem temporaeren Verzeichnis,
# eigene temporaere DB, kein Zugriff auf den echten Plan oder die echte DB.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import io
    import os
    import sqlite3
    import tempfile
    from contextlib import redirect_stdout

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # --- Teil 1: --vorschlag (rein lesend) -----------------------------
        plan = tmp / "PLAN_TEST.md"
        plan.write_text(
            "### S1 · erster Schritt\nKein Verweis, keine Datei.\n\n"
            "### S2 · zweiter Schritt\nReihenfolge: nach S1. Siehe `a.py`.\n\n"
            "### S3 · dritter Schritt\nKeine Reihenfolgeaussage. Nutzt `a.py` mit.\n\n"
            "### S4 · vierter Schritt\nKeine Reihenfolgeaussage. Nutzt `a.py` ebenfalls.\n",
            encoding="utf-8",
        )
        a = _analysiere(plan)
        assert [ab.kennung for ab in a.abschnitte] == ["S1", "S2", "S3", "S4"]

        s2_funde = a.funde_je[1]
        assert len(s2_funde) == 1, f"S2 haette genau einen Fund haben sollen, hat {len(s2_funde)}"
        assert s2_funde[0].quelle == "S1" and s2_funde[0].ziel == "S2"
        assert "nach S1" in s2_funde[0].zitat

        assert a.funde_je[0] == [], "S1 hat keine Reihenfolgeaussage -- haette leer sein muessen"

        paare = _parallel_paare(a)
        assert ("S1", "S3") in paare, "S1/S3: keine Reihenfolge, keine gemeinsame Datei -- haette parallel sein muessen"
        assert ("S3", "S4") not in paare, "S3/S4 teilen a.py -- haetten NICHT parallel sein duerfen"
        assert ("S1", "S2") not in paare, "S1/S2 haben eine Reihenfolgeaussage -- haetten NICHT parallel sein duerfen"
        print("Pflichtfaelle a/b/c/d (Vorschlag): bestanden")

        # --- Teil 2: --schreiben (Knoten + Kanten in temporaerer DB) -------
        db_pfad = tmp / "test.db"
        os.environ["BEGOD_KNOWLEDGE_DB"] = str(db_pfad)
        for name in ("knowledge_mcp_server",):
            sys.modules.pop(name, None)  # frischer Import: DB_PATH wird beim Import fixiert
        import knowledge_mcp_server as kms

        conn = kms.get_db()
        _schreiben_datei(kms, conn, plan)

        knoten = conn.execute("SELECT path FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchall()
        assert len(knoten) == 4, f"erwartet 4 Knoten, bekommen {len(knoten)}"

        bindend = conn.execute("SELECT evidence FROM knowledge_relations WHERE relation_type='bindend_vor'").fetchall()
        assert len(bindend) == 1, f"Pflichtfall (a) verletzt: erwartet genau 1 bindend_vor-Kante, bekommen {len(bindend)}"
        assert "nach S1" in bindend[0][0], f"Zitat fehlt als evidence: {bindend[0][0]!r}"

        entstand = conn.execute("SELECT COUNT(*) FROM knowledge_relations WHERE relation_type='entstand_nach'").fetchone()[0]
        assert entstand == 3, f"erwartet 3 entstand_nach-Kanten (4 Abschnitte), bekommen {entstand}"
        print("Pflichtfall a (bindend_vor mit Zitat) + entstand_nach: bestanden")

        # Pflichtfall (b): S1 hat keinen bindend_vor als ZIEL oder QUELLE ausser dem einen S1->S2
        bindend_alle = conn.execute(
            "SELECT source_path, target_path FROM knowledge_relations WHERE relation_type='bindend_vor'"
        ).fetchall()
        assert len(bindend_alle) == 1, "S3/S4 ohne Reihenfolgeaussage haetten keine bindend_vor-Kante erzeugen duerfen"
        print("Pflichtfall b (keine Kante ohne Aussage): bestanden")

        # Pflichtfall (e): zweiter Lauf erzeugt keine Dubletten
        _schreiben_datei(kms, conn, plan)
        knoten2 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchone()[0]
        kanten2 = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
        assert knoten2 == 4, f"Wiederholungslauf haette keine neuen Knoten anlegen duerfen, hat jetzt {knoten2}"
        assert kanten2 == 4, f"Wiederholungslauf haette keine neuen Kanten anlegen duerfen, hat jetzt {kanten2}"
        print("Pflichtfall e (Wiederholungslauf ohne Dubletten): bestanden")

        # Negativfall der harten Grenze: bindend_vor ohne Zitat ist unmoeglich
        try:
            _kante_bindend_vor(conn, "/irgendwo/a", "/irgendwo/b", "   ")
            raise AssertionError("bindend_vor mit leerem Zitat haette scheitern muessen")
        except ValueError as exc:
            assert "Zitat" in str(exc)
        print("Harte Grenze (bindend_vor ohne Zitat unmoeglich): bestanden")

        conn.close()
        del os.environ["BEGOD_KNOWLEDGE_DB"]
        sys.modules.pop("knowledge_mcp_server", None)

    print("Selbsttest bestanden.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vorschlag", action="store_true", help="nur lesen, nichts schreiben")
    ap.add_argument("--schreiben", action="store_true", help="Knoten + Kanten anlegen")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan-dir", type=Path, default=WURZEL / "docs")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0
    if args.schreiben:
        _schreiben(args.plan_dir)
        return 0
    # --vorschlag ist die Vorgabe (Auftrag: "schreibt erst nach Sichtung")
    _vorschlag(args.plan_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
