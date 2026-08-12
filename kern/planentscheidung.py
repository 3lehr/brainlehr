#!/usr/bin/env python3
"""Erzeugt Knoten aus ENTSCHEIDENDEN Planabschnitten und schreibt die
Kennung in die Plandatei zurueck, damit `planbindung.py` sie findet.

Anlass (Auftrag 2026-08-12): `planbindung.py` misst nur, ob eine Kennung
dasteht -- es legt keine an. 4 von 18 Abschnitten in
PLAN_DESTILLE_2026-08-09.md trugen eine, weil ein FREIWILLIG gefuelltes
Feld leer bleibt (L-480c87). "Query-Rewriting" stand dreimal als bekannter
Rueckstand im Plan, ohne Knoten dazu -- der Speicher konnte nicht
widersprechen, als dieselbe Sache Stunden spaeter neu erfunden wurde
(L-33aae1).

NICHT jeder Abschnitt wird Knoten -- das waere `planordnung.py` (legt fuer
JEDEN Abschnitt einen Knoten an, um REIHENFOLGE als Kanten abzulegen, ein
anderer Zweck). Hier zaehlt nur, ob ein Abschnitt etwas ENTSCHEIDET: 1641
von 2132 Knoten im Bestand sind bereits `gattung=nachschlagewerk`, der
ARBEITSBESTAND ist 491 -- alle 139 Planabschnitte als Knoten waeren +28 %
auf diesen Nenner, 39 entscheidende (28 % der Abschnitte nach der
Wortliste des Auftrags) sind +8 % und vertretbar. Beschreibende Abschnitte
bleiben Text in der .md-Datei, wie im Kopf von PLAN_DESTILLE_2026-08-09.md
selbst festgelegt: "gehoert in den Speicher: die ENTSCHEIDUNG selbst".

ERKENNUNG "entscheidend" -- gemessen gegen die Wortliste des Auftrags
(verworfen, entschieden, gewaehlt, Alternative, Ablehnungsgrund, bindend),
NICHT unveraendert uebernommen. Gegen PLAN_DESTILLE_2026-08-09.md (23
S-Abschnitte, Stand 2026-08-12) trifft die Auftragsliste 11 von 23 -- und
lässt dabei Abschnitte durch, die unstrittig entscheiden: S1b legt fest
"Nachschlagewerke werden als Gattung gekennzeichnet und nehmen am
automatischen Abruf NICHT teil", S9 "Zu bauen ist deshalb keine zweite
Einstellung, sondern eine Zusammenfuehrung", S18 "VORSCHLAGEN JA, STARTEN
NEIN" -- keines davon enthaelt eines der sechs Woerter. Ergaenzt um
`entscheidung` (als Wort, nicht nur `entschieden`), `beschlossen`,
`vorgabe ist` (die Standardregel-Formel, mehrfach im Plan: "Vorgabe ist
`intern`, nicht `offen`"), `nicht gebaut` (bewusste Ablehnung ohne das Wort
"verworfen", z.B. S8 "Bewusst NICHT gebaut") und `ab sofort` (Regel-Einsatz
ohne Ruecksprache, S1c "Regel, ab sofort"). Damit: 16 von 23. Bleibt
UNTER-erkannt: S11 hat schon eine gueltige Kennung aus frueherer Handarbeit
und enthaelt eine echte Entscheidung ("er meldet nur zu Code, der in
DIESER Sitzung geaendert wurde"), die auch diese erweiterte Liste nicht
trifft -- kein Wortkatalog erreicht Praezision und Trefferquote zugleich,
darum ist `--vorschlag` PFLICHT vor `--schreiben`, nicht Kuer.

REICHWEITE, gemessen statt angenommen: `planbindung._abschnitte()` findet
Abschnitte nur ueber den Kopf "### S<zahl><buchstabe?>". Von den 139
Ueberschriften in docs/PLAN_*.md + docs/SPRINTS.md (`grep -c '^##'`)
erfuellen NUR die 23 in PLAN_DESTILLE_2026-08-09.md dieses Muster -- alle
anderen Plandateien gliedern mit "## 1. ..." oder "### B4.1" und liefern
0 Abschnitte. Dieses Werkzeug verarbeitet deshalb zwangslaeufig nur Dateien
in genau dieser Kopf-Konvention; andere Plandateien sind NICHT stillschweigend
leer geprueft, sondern strukturell ausserhalb dessen, was `planbindung.py`
ueberhaupt sehen kann. Das ist eine Abweichung wert, sie zu melden statt
still zu uebergehen -- siehe Bericht am Ende dieses Laufs.

Idempotenz: ein Abschnitt bekommt GENAU EINEN Knoten. Die Kennung wird als
eigene Zeile ("*Kennung: `xxxxxxxx`*") direkt nach der Ueberschrift in die
Datei geschrieben; ein zweiter Lauf findet diese Zeile, legt nichts neu an
und schreibt den Knoteninhalt nur fort, wenn sich der Abschnittstext seit
dem letzten Lauf geaendert hat.

Aufruf:
    python3 planentscheidung.py --vorschlag DATEI   # nur lesen, Trockenlauf
    python3 planentscheidung.py --schreiben DATEI   # Knoten anlegen/fortschreiben + Datei schreiben
    python3 planentscheidung.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql, wie alle Geschwister-Skripte hier.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import planbindung  # reuse: _abschnitte(), _HEADER_RE, _JEDE_UEBERSCHRIFT_RE

WURZEL = _w

# Wortliste aus dem Auftrag plus die vier Ergaenzungen, siehe Modul-Docstring
# fuer die Messung, die diese Erweiterung rechtfertigt.
_ENTSCHEIDEND_RE = re.compile(
    r"verworfen|entschieden|entscheidung|gewaehlt|gewählt|alternative|"
    r"ablehnungsgrund|bindend|beschlossen|vorgabe ist|nicht gebaut|ab sofort",
    re.IGNORECASE,
)

_KENNUNG_ZEILE_RE = re.compile(r"^\*Kennung:\s*`([0-9a-fA-F]{8})`\*\s*$")


def ist_entscheidend(text: str) -> bool:
    return bool(_ENTSCHEIDEND_RE.search(text))


@dataclass
class Bericht:
    kennung: str
    titel: str
    aktion: str  # "angelegt" | "fortgeschrieben" | "unveraendert" | "beschreibend" | "phantom"
    knoten_id: str | None = None


def _abschnitt_positionen(zeilen: list[str]) -> list[tuple[int, int, str, str]]:
    """(start, ende, kennung, titel) je S-Abschnitt -- dieselbe Grenzlogik
    wie planbindung._abschnitte(), aber mit Zeilenindizes statt fertigem
    Text, damit an genau der richtigen Stelle eingefuegt werden kann."""
    grenzen = [i for i, z in enumerate(zeilen) if planbindung._JEDE_UEBERSCHRIFT_RE.match(z)]
    treffer = [(i, m) for i in grenzen if (m := planbindung._HEADER_RE.match(zeilen[i]))]
    ergebnis = []
    for start, m in treffer:
        folgende = [g for g in grenzen if g > start]
        ende = folgende[0] if folgende else len(zeilen)
        ergebnis.append((start, ende, m.group(1), m.group(2).strip()))
    return ergebnis


def _bestehende_kennung(block_zeilen: list[str]) -> str | None:
    for z in block_zeilen[1:]:
        m = _KENNUNG_ZEILE_RE.match(z.strip())
        if m:
            return m.group(1)
    return None


def _ohne_kennungszeile(text: str) -> str:
    """Der Knoteninhalt ist die PROSA des Abschnitts, nie die eigene
    Buchfuehrungszeile -- sonst vergleicht ein zweiter Lauf den gespeicherten
    Inhalt (ohne Zeile, zum Anlegezeitpunkt gab es sie noch nicht) gegen den
    aktuellen Abschnittstext (MIT Zeile, seit dem ersten Lauf in der Datei)
    und haelt jeden Abschnitt faelschlich fuer geaendert."""
    return "\n".join(z for z in text.splitlines() if not _KENNUNG_ZEILE_RE.match(z.strip()))


def _node_gehalt(conn, node_id: str) -> str | None:
    row = conn.execute("SELECT content FROM knowledge_nodes WHERE id LIKE ?", (f"{node_id}%",)).fetchone()
    return row[0] if row else None


def _fremd_gebunden(ab_text: str, ids: list[str]) -> str | None:
    """Ein Abschnitt kann schon VOR diesem Werkzeug eine gueltige Kennung
    tragen -- als Fliesstext-Zitat (z.B. 'Entscheidung `b6305304`'), nicht
    als unsere eigene Buchfuehrungszeile. planbindung.py haelt das bereits
    fuer gebunden (siehe dortiges pruefen()); dieses Werkzeug darf dann
    KEINEN zweiten Knoten daneben anlegen -- sonst haette derselbe
    Abschnitt zwei Kennungen, eine davon verwaist. Gleiche Pruefung wie
    planbindung._existiert(), hier direkt wiederverwendet."""
    for k in planbindung._KENNUNG_RE.findall(ab_text):
        if planbindung._existiert(k, ids):
            return k
    return None


def verarbeiten(kms, conn, datei: Path, schreiben: bool) -> list[Bericht]:
    zeilen = datei.read_text(encoding="utf-8").splitlines()
    positionen = _abschnitt_positionen(zeilen)
    abschnitte = planbindung._abschnitte(datei)
    assert len(positionen) == len(abschnitte), "Positions- und Textliste muessen 1:1 uebereinstimmen"

    plan_stem = datei.stem
    ast = kms._normalize_path(f"/plaene/{plan_stem}")
    vorhandene_ids = planbindung._vorhandene_ids(conn)

    berichte: list[Bericht] = []
    einfuegungen: list[tuple[int, str]] = []  # (Zeilenindex NACH der Ueberschrift, Zeile)

    for (start, ende, kennung, titel), ab in zip(positionen, abschnitte):
        block = zeilen[start:ende]
        bestehende = _bestehende_kennung(block)

        if not bestehende:
            fremd = _fremd_gebunden(ab.text, vorhandene_ids)
            if fremd:
                # Schon vor diesem Werkzeug gebunden (Fliesstext-Zitat,
                # nicht unsere Buchfuehrungszeile) -- nichts anlegen, nichts
                # schreiben, planbindung.py sieht diesen Abschnitt bereits
                # als erledigt an.
                berichte.append(Bericht(kennung, titel, "bereits_gebunden", fremd))
                continue

        if bestehende:
            prosa = _ohne_kennungszeile(ab.text)
            gehalt = _node_gehalt(conn, bestehende)
            if gehalt is None:
                berichte.append(Bericht(kennung, titel, "phantom", bestehende))
                continue
            if gehalt == prosa:
                berichte.append(Bericht(kennung, titel, "unveraendert", bestehende))
                continue
            if schreiben:
                kms.knowledge_update(bestehende, content=prosa, summary=titel[:200])
            berichte.append(Bericht(kennung, titel, "fortgeschrieben", bestehende))
            continue

        if not ist_entscheidend(ab.text):
            berichte.append(Bericht(kennung, titel, "beschreibend"))
            continue

        if not schreiben:
            berichte.append(Bericht(kennung, titel, "wuerde_anlegen"))
            continue

        slug = kms._slugify(f"{kennung} {titel}")
        node_path = f"{ast}/{slug}"
        vorhanden = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (node_path,)).fetchone()
        if vorhanden:
            node_id = vorhanden[0]
        else:
            ergebnis = kms.knowledge_add(
                parent_path=ast, title=f"{kennung} · {titel}", summary=titel[:200],
                content=ab.text, neuer_ast=True, tags=["plan-entscheidung", plan_stem],
                # ab.text hat an dieser Stelle noch KEINE Kennungszeile (die
                # entsteht erst gleich danach) -- deckungsgleich mit
                # _ohne_kennungszeile(ab.text) im Fortschreibungs-Zweig oben,
                # damit der naechste Lauf nicht faelschlich "geaendert" liest.
                source=f"entschieden in {datei} Abschnitt {kennung} (planentscheidung.py)",
                anlass="skript", norm_entscheidung="keine_norm",
                norm_entschieden_grund=(
                    "Der Planabschnitt entscheidet etwas (Wortliste in "
                    "planentscheidung.py) -- der Knoten macht diese "
                    "Entscheidung im Speicher auffindbar, kein eigener "
                    "Normanspruch."
                ),
            )
            if "error" in ergebnis:
                raise RuntimeError(f"Knoten fuer {kennung} in {datei.name} nicht angelegt: {ergebnis['error']}")
            node_id = ergebnis["id"]
        einfuegungen.append((start, f"*Kennung: `{node_id}`*"))
        berichte.append(Bericht(kennung, titel, "angelegt", node_id))

    if schreiben and einfuegungen:
        for idx, zeile in sorted(einfuegungen, key=lambda t: -t[0]):
            zeilen.insert(idx + 1, zeile)
        datei.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    return berichte


def _drucken(datei: Path, berichte: list[Bericht], schreiben: bool) -> None:
    kopf = "SCHREIBLAUF" if schreiben else "TROCKENLAUF (--vorschlag, nichts geschrieben)"
    print(f"\n== {datei.name} -- {kopf} ==")
    for b in berichte:
        zusatz = f" ({b.knoten_id})" if b.knoten_id else ""
        print(f"  {b.aktion:16} {b.kennung:5} {b.titel[:60]}{zusatz}")
    zaehl = {}
    for b in berichte:
        zaehl[b.aktion] = zaehl.get(b.aktion, 0) + 1
    print("  --")
    print("  " + ", ".join(f"{k}={v}" for k, v in sorted(zaehl.items())))


def _lauf(datei: Path, schreiben: bool) -> list[Bericht]:
    import knowledge_mcp_server as kms  # lazy: DB_PATH wird erst beim Import fixiert
    conn = kms.get_db()
    try:
        berichte = verarbeiten(kms, conn, datei, schreiben)
    finally:
        conn.close()
    _drucken(datei, berichte, schreiben)
    return berichte


# ---------------------------------------------------------------------------
# Selbsttest -- eigene Beispieldatei, eigene temporaere DB.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import os
    import sqlite3
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        plan = tmp / "PLAN_TEST.md"
        plan.write_text(
            "# Testplan\n\n"
            "### S1 · reine Messung ohne Beschluss\n"
            "Nur eine Messung: 3 von 10 Faellen trafen.\n\n"
            "### S2 · entscheidend, klarer Marker\n"
            "Verworfen wurde Ansatz X. Bindend ist Ansatz Y.\n\n"
            "### S3 · entscheidend ohne Auftrags-Wortliste\n"
            "Vorgabe ist `intern`, nicht `offen`.\n",
            encoding="utf-8",
        )

        db_pfad = tmp / "test.db"
        os.environ["BEGOD_KNOWLEDGE_DB"] = str(db_pfad)  # knowledge_mcp_server.DB_PATH
                                                          # liest NUR diesen Namen (siehe
                                                          # dortige Zeile bei DB_PATH), nicht
                                                          # BRAINLEHR_DB -- planordnung.py's
                                                          # Selbsttest nutzt denselben Namen.
        for name in ("knowledge_mcp_server",):
            sys.modules.pop(name, None)
        import knowledge_mcp_server as kms

        conn = kms.get_db()

        # ROT: vor dem Bau existierte verarbeiten() nicht -- der Aufruf
        # haette mit NameError abgebrochen (woertlich, nicht reproduzierbar
        # ohne den fertigen Code zu entfernen):
        #   NameError: name 'verarbeiten' is not defined
        # Ab hier die GRUEN-Probe.

        # --- Trockenlauf: nichts geschrieben ---------------------------------
        vor = plan.read_text(encoding="utf-8")
        berichte = verarbeiten(kms, conn, plan, schreiben=False)
        nach = plan.read_text(encoding="utf-8")
        assert vor == nach, "Trockenlauf haette die Datei nicht anfassen duerfen"
        arten = {b.kennung: b.aktion for b in berichte}
        assert arten["S1"] == "beschreibend", f"S1 haette beschreibend sein muessen, war {arten['S1']}"
        assert arten["S2"] == "wuerde_anlegen", f"S2 haette wuerde_anlegen sein muessen, war {arten['S2']}"
        assert arten["S3"] == "wuerde_anlegen", f"S3 (nur Ergaenzungs-Marker) haette wuerde_anlegen sein muessen, war {arten['S3']}"
        knoten_vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchone()[0]
        assert knoten_vorher == 0, "Trockenlauf haette keinen Knoten anlegen duerfen"
        print("Pflichtfall a (Trockenlauf schreibt nichts, S1 beschreibend, S2/S3 entscheidend): bestanden")

        # --- Erster Schreiblauf ----------------------------------------------
        berichte1 = verarbeiten(kms, conn, plan, schreiben=True)
        arten1 = {b.kennung: b.aktion for b in berichte1}
        assert arten1["S1"] == "beschreibend"
        assert arten1["S2"] == "angelegt"
        assert arten1["S3"] == "angelegt"
        knoten1 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchone()[0]
        assert knoten1 == 2, f"erwartet 2 Knoten (S2, S3), bekommen {knoten1}"

        text_nach_lauf1 = plan.read_text(encoding="utf-8")
        assert "### S1" in text_nach_lauf1 and "*Kennung:" not in text_nach_lauf1.split("### S2")[0].split("### S1")[1], \
            "S1 (beschreibend) haette KEINE Kennungszeile bekommen duerfen"
        assert text_nach_lauf1.count("*Kennung:") == 2, "S2 und S3 haetten je eine Kennungszeile bekommen muessen"
        print("Pflichtfall b (Negativfall: beschreibender Abschnitt wird NICHT zum Knoten): bestanden")

        # --- Zweiter Lauf: idempotent -----------------------------------------
        berichte2 = verarbeiten(kms, conn, plan, schreiben=True)
        arten2 = {b.kennung: b.aktion for b in berichte2}
        assert arten2["S2"] == "unveraendert", f"zweiter Lauf haette S2 unveraendert lassen muessen, war {arten2['S2']}"
        assert arten2["S3"] == "unveraendert"
        knoten2 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchone()[0]
        assert knoten2 == 2, f"zweiter Lauf haette KEINE neuen Knoten anlegen duerfen, hat jetzt {knoten2}"
        text_nach_lauf2 = plan.read_text(encoding="utf-8")
        assert text_nach_lauf2 == text_nach_lauf1, "zweiter Lauf haette die Datei nicht veraendern duerfen (Grenzfall Verdopplung)"
        print("Pflichtfall c (zweiter Lauf erzeugt null neue Knoten, Datei unveraendert): bestanden")

        # --- Abschnitt aendert sich: Fortschreibung statt Verdopplung ---------
        text = plan.read_text(encoding="utf-8")
        text = text.replace(
            "Verworfen wurde Ansatz X. Bindend ist Ansatz Y.",
            "Verworfen wurde Ansatz X. Bindend ist Ansatz Z, nach erneuter Pruefung.",
        )
        plan.write_text(text, encoding="utf-8")
        berichte3 = verarbeiten(kms, conn, plan, schreiben=True)
        arten3 = {b.kennung: b.aktion for b in berichte3}
        assert arten3["S2"] == "fortgeschrieben", f"geaenderter Abschnitt haette fortgeschrieben werden muessen, war {arten3['S2']}"
        assert arten3["S3"] == "unveraendert"
        knoten3 = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path LIKE '/plaene/plan-test/%'").fetchone()[0]
        assert knoten3 == 2, f"Fortschreibung haette KEINEN neuen Knoten anlegen duerfen, hat jetzt {knoten3}"
        gehalt_s2 = conn.execute(
            "SELECT content FROM knowledge_nodes WHERE id LIKE ?", (f"{berichte1[1].knoten_id}%",)
        ).fetchone()[0]
        assert "Ansatz Z" in gehalt_s2, "Fortschreibung haette den neuen Text im Knoten ablegen muessen"
        print("Pflichtfall d (geaenderter Abschnitt wird fortgeschrieben, nicht verdoppelt): bestanden")

        conn.close()
        del os.environ["BEGOD_KNOWLEDGE_DB"]
        sys.modules.pop("knowledge_mcp_server", None)

    print("Selbsttest bestanden.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gruppe = ap.add_mutually_exclusive_group()
    gruppe.add_argument("--vorschlag", type=Path, help="Trockenlauf auf EINER Plandatei")
    gruppe.add_argument("--schreiben", type=Path, help="Knoten anlegen/fortschreiben + Datei schreiben")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0
    if args.schreiben:
        _lauf(args.schreiben, schreiben=True)
        return 0
    if args.vorschlag:
        _lauf(args.vorschlag, schreiben=False)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
