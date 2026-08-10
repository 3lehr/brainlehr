#!/usr/bin/env python3
"""Ein Melder auf die BINDUNG zwischen Plan und Speicher -- S: Plandateien
(docs/PLAN_*.md), Beleg fuer diese eine: docs/PLAN_DESTILLE_2026-08-09.md.

Anlass: Der Plan legt in seinem eigenen Kopf fest, dass eine Entscheidung
erst bindend ist, wenn ihr Abschnitt eine Knotenkennung nennt -- fehlt sie,
ist die Entscheidung "noch nicht bindend abgelegt". Gemessen 2026-08-09:
nur 4 von 18 Abschnitten in PLAN_DESTILLE_2026-08-09.md nennen eine
Kennung. "Query-Rewriting" stand dreimal als bekannter Rueckstand im Plan,
ohne Knoten dazu -- der Speicher konnte nicht widersprechen, als dieselbe
Sache Stunden spaeter neu erfunden wurde. Ein Plan, der nur in einer Datei
steht, ist fuer das eigene System unsichtbar.

Zwei Fehlklassen, unterschiedlich schwer:

  1. FEHLENDE KENNUNG -- ein Abschnitt behauptet nichts, was der Speicher
     pruefen koennte. Leichter Befund: der Plan hat es (noch) nicht
     abgelegt, das ist der Normalfall vor der Bindung.
  2. PHANTOM-KENNUNG -- ein Abschnitt nennt eine Kennung, zu der KEIN
     Knoten existiert. Schwerer Befund: der Plan behauptet eine Ablage,
     die es nicht gibt -- das ist kein fehlender Schritt, sondern eine
     falsche Angabe.

Dieselben drei Auflagen wie `pruefer.py` und `arbeitsmelder.py`:

  1. MESSBAR aus dem Bestand: ein Abschnitt zaehlt als geprueft, wenn eine
     im Text stehende 8-stellige Hexfolge tatsaechlich als `id` in
     `knowledge_nodes` existiert (Abgleich per Praefix, `id LIKE
     '<kennung>%'`) -- keine Stimmung, ein SQL-Ergebnis.
  2. FEHLKLASSE benannt: "fehlende Kennung" (leicht) und "Phantom-Kennung"
     (schwer), siehe oben -- kein Befund ohne diese Zuordnung.
  3. PREIS EINES FEHLALARMS: fuer "fehlende Kennung" gering -- der
     Abschnitt wird zurecht so lange genannt, bis jemand die Kennung
     eintraegt, kein Handeln erzwungen. Fuer "Phantom-Kennung" hoeher --
     eine falsch gelesene Kennung (z.B. abgeschnittene Backtick-Markierung)
     erzeugt einen Befund, der nach geloeschtem Knoten aussieht, obwohl nur
     der Regex daneben lag. Darum wird die Kennung im Befund IMMER woertlich
     mitgenannt -- der Leser kann sie in Sekunden selbst nachschlagen.

Und er schweigt, wenn nichts anschlaegt.

Aufruf:
    python3 planbindung.py             # alle Plandateien, ausfuehrlich
    python3 planbindung.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 planbindung.py --selftest
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
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = _w

# Abschnittskopf laut Plan-Konvention: "### S<zahl><buchstabe?> · <titel>".
# Zwei der 18 gemessenen Abschnitte in PLAN_DESTILLE_2026-08-09.md weichen
# davon ab (kein " · ", z.B. "### S1b wird konkreter: ..."). Darum der
# Trenner optional -- sonst wuerden genau diese beiden unbeobachtet durchs
# Raster fallen, und das waere der schlechteste Fehler fuer einen Melder:
# schweigen, wo eigentlich etwas zu pruefen ist.
_HEADER_RE = re.compile(r"^### (S\d+[a-z]?)(?:\s*·\s*|\s+)(.*)$")

# Knotenkennung: 8-stellige Hexfolge. \b reicht als Grenze -- Lehren-IDs
# ("L-502be0") haben nur 6 Hexstellen nach dem Praefix und passen nicht,
# Commit-Hashes im Kurzformat ("577a774") haben 7.
_KENNUNG_RE = re.compile(r"\b[0-9a-fA-F]{8}\b")


@dataclass
class Abschnitt:
    datei: str
    kennung: str  # "S1", "S1b", ...
    titel: str
    text: str


@dataclass
class Befund:
    art: str  # "fehlende_kennung" | "phantom_kennung"
    datei: str
    abschnitt: str
    titel: str
    kennungen: list[str] = field(default_factory=list)


_JEDE_UEBERSCHRIFT_RE = re.compile(r"^#{2,3} ")


def _abschnitte(datei: Path) -> list[Abschnitt]:
    """Ein S-Abschnitt endet an der naechsten UEBERSCHRIFT jeder Art, nicht
    erst am naechsten S-Kopf. Sonst schluckt ein S-Abschnitt jede
    Zwischenueberschrift ohne "S<zahl>"-Praefix (z.B. "### Einwand des
    Betreibers ...") samt ihres Texts -- gemessen an
    PLAN_DESTILLE_2026-08-09.md: ohne diese Grenze haengt `b6305304` aus
    einem sechs Abschnitte spaeter liegenden Unterkapitel faelschlich am
    zweiten "S12"-Kopf."""
    zeilen = datei.read_text(encoding="utf-8").splitlines()
    grenzen = [i for i, z in enumerate(zeilen) if _JEDE_UEBERSCHRIFT_RE.match(z)]
    treffer = [(i, m) for i in grenzen if (m := _HEADER_RE.match(zeilen[i]))]
    ergebnis = []
    for start, m in treffer:
        folgende = [g for g in grenzen if g > start]
        ende = folgende[0] if folgende else len(zeilen)
        text = "\n".join(zeilen[start:ende])
        ergebnis.append(Abschnitt(datei=datei.name, kennung=m.group(1),
                                   titel=m.group(2).strip(), text=text))
    return ergebnis


def _vorhandene_ids(conn: sqlite3.Connection) -> list[str]:
    return [r[0].lower() for r in conn.execute("SELECT id FROM knowledge_nodes").fetchall()]


def _existiert(kennung: str, ids: list[str]) -> bool:
    k = kennung.lower()
    return any(i.startswith(k) for i in ids)


def pruefen(plan_dateien: list[Path], conn: sqlite3.Connection) -> list[Befund]:
    ids = _vorhandene_ids(conn)
    befunde: list[Befund] = []
    for datei in plan_dateien:
        for ab in _abschnitte(datei):
            gefunden = list(dict.fromkeys(_KENNUNG_RE.findall(ab.text)))
            if not gefunden:
                befunde.append(Befund("fehlende_kennung", ab.datei, ab.kennung, ab.titel))
                continue
            phantome = [k for k in gefunden if not _existiert(k, ids)]
            if phantome:
                befunde.append(Befund("phantom_kennung", ab.datei, ab.kennung, ab.titel, phantome))
            # sonst: mindestens eine gueltige Kennung -> still (Pflichtfall a)
    return befunde


DECKEL = 5


def _melden(befunde: list[Befund]) -> None:
    if not befunde:
        return
    # Phantom-Kennungen zuerst -- der schwerere Befund soll nicht vom
    # Deckel abgeschnitten werden, wenn es zu viele leichte gibt.
    schwer = [b for b in befunde if b.art == "phantom_kennung"]
    leicht = [b for b in befunde if b.art == "fehlende_kennung"]
    geordnet = schwer + leicht

    gesamt = len(geordnet)
    gezeigt = geordnet[:DECKEL]
    for b in gezeigt:
        if b.art == "phantom_kennung":
            print(f"PHANTOM-KENNUNG  {b.datei} · {b.abschnitt} · {b.titel}  "
                  f"-- nennt {', '.join(b.kennungen)}, kein Knoten dazu")
        else:
            print(f"fehlende Kennung {b.datei} · {b.abschnitt} · {b.titel}")
    rest = gesamt - len(gezeigt)
    if rest > 0:
        print(f"... und {rest} weitere Abschnitt(e) ohne bindende Ablage")


def _ausfuehrlich(befunde: list[Befund], anzahl_abschnitte: int) -> None:
    if not befunde:
        print(f"{anzahl_abschnitte} Abschnitte geprueft, alle mit gueltiger Kennung oder ohne Anspruch.")
        return
    print(f"{len(befunde)} von {anzahl_abschnitte} Abschnitten ohne bindende Ablage:")
    for b in befunde:
        if b.art == "phantom_kennung":
            print(f"  PHANTOM  {b.datei} · {b.abschnitt} · {b.titel} -- "
                  f"nennt {', '.join(b.kennungen)}, kein Knoten dazu")
        else:
            print(f"  fehlt    {b.datei} · {b.abschnitt} · {b.titel}")


def _connection(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _echte_db_pfad() -> Path:
    sys.path.insert(0, str(WURZEL / "haken"))
    import ort  # noqa: E402
    return ort.DB


# ---------------------------------------------------------------------------
# Selbsttest -- eigene Beispieldateien in einem temporaeren Verzeichnis,
# kein Zugriff auf den echten Plan, keine Schreibung in die echte DB.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_pfad = tmp / "test.db"
        conn_rw = sqlite3.connect(db_pfad)
        conn_rw.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY)")
        conn_rw.executemany(
            "INSERT INTO knowledge_nodes (id) VALUES (?)",
            [("aaaa1111",), ("bbbb2222",)],
        )
        conn_rw.commit()
        conn_rw.close()
        conn = _connection(db_pfad)

        plan = tmp / "PLAN_TEST.md"
        plan.write_text(
            "### S1 · hat gueltige Kennung\n"
            "Text mit Knoten `aaaa1111` belegt.\n\n"
            "### S2 · hat keine Kennung\n"
            "Nur Prosa, nichts abgelegt.\n\n"
            "### S3 · hat Phantom-Kennung\n"
            "Verweist auf `ffffffff`, den es nicht gibt.\n",
            encoding="utf-8",
        )

        # ROT: vor dem Bau existierte `pruefen` nicht -- der Aufruf haette
        # mit AttributeError/NameError abgebrochen. Hier woertlich als
        # Kommentar festgehalten, weil ein rot gelaufener Aufruf sich nicht
        # nachtraeglich reproduzieren laesst, ohne den Code zu entfernen:
        #   NameError: name 'pruefen' is not defined
        # Ab hier die GRUEN-Probe gegen den fertigen Code.
        befunde = pruefen([plan], conn)

        arten = {(b.abschnitt, b.art) for b in befunde}
        assert ("S1", "fehlende_kennung") not in arten, "Pflichtfall (a) verletzt: S1 haette schweigen muessen"
        assert ("S1", "phantom_kennung") not in arten, "Pflichtfall (a) verletzt: S1 haette schweigen muessen"
        assert ("S2", "fehlende_kennung") in arten, "Pflichtfall (b) verletzt: S2 haette gemeldet werden muessen"
        assert ("S3", "phantom_kennung") in arten, "Pflichtfall (c) verletzt: S3 haette als Phantom gemeldet werden muessen"
        assert len(befunde) == 2, f"erwartet 2 Befunde (S2, S3), bekommen {len(befunde)}"
        print("Pflichtfaelle a/b/c: bestanden")

        # (d) Deckel: 6 fehlende Abschnitte -> 5 genannt, Rest ausgewiesen
        viele = "\n\n".join(f"### S{i} · Abschnitt {i}\nkein Beleg" for i in range(6))
        plan_deckel = tmp / "PLAN_DECKEL.md"
        plan_deckel.write_text(viele, encoding="utf-8")
        befunde_deckel = pruefen([plan_deckel], conn)
        assert len(befunde_deckel) == 6, f"erwartet 6 fehlende Abschnitte, bekommen {len(befunde_deckel)}"

        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            _melden(befunde_deckel)
        ausgabe = puffer.getvalue()
        gezeigte_zeilen = [z for z in ausgabe.splitlines() if z.startswith("fehlende Kennung")]
        assert len(gezeigte_zeilen) == 5, f"Deckel haette 5 zeigen sollen, zeigte {len(gezeigte_zeilen)}"
        assert "1 weitere" in ausgabe, f"Restzahl fehlt in Ausgabe: {ausgabe!r}"
        print("Pflichtfall d (Deckel bei 6): bestanden")

        # (e) Negativfall: alle Abschnitte mit gueltiger Kennung -> keine Ausgabe
        plan_ok = tmp / "PLAN_OK.md"
        plan_ok.write_text(
            "### S1 · alles belegt\nSiehe `aaaa1111`.\n\n"
            "### S2 · auch belegt\nSiehe `bbbb2222`.\n",
            encoding="utf-8",
        )
        befunde_ok = pruefen([plan_ok], conn)
        assert befunde_ok == [], f"Negativfall haette leer sein muessen, bekommen {befunde_ok}"
        puffer2 = io.StringIO()
        with redirect_stdout(puffer2):
            _melden(befunde_ok)
        assert puffer2.getvalue() == "", "Negativfall haette --melder stumm lassen muessen"
        print("Pflichtfall e (Negativfall): bestanden")

        conn.close()

    print("Selbsttest bestanden.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan-dir", type=Path, default=WURZEL / "docs")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0

    plan_dateien = sorted(args.plan_dir.glob("PLAN_*.md"))
    if not plan_dateien:
        if not args.melder:
            print(f"keine Plandateien unter {args.plan_dir}")
        return 0

    conn = _connection(_echte_db_pfad())
    try:
        anzahl_abschnitte = sum(len(_abschnitte(d)) for d in plan_dateien)
        befunde = pruefen(plan_dateien, conn)
    finally:
        conn.close()

    if args.melder:
        _melden(befunde)
    else:
        _ausfuehrlich(befunde, anzahl_abschnitte)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
