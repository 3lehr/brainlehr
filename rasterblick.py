#!/usr/bin/env python3
"""Ein Rastervermerk je Ergebnisdatei -- WAS abgesucht wurde, nicht nur was gefunden wurde.

Anlass (S1c, docs/PLAN_DESTILLE_2026-08-09.md): Ein Raster ohne Vermerk ist
nicht wiederholbar, sondern nur wiederhol**bar von vorn** -- belegt an drei
gemessenen Faellen an einem Tag (NASA-Durchgang 40 von 1638 ohne Vermerk am
Knoten, ein Gitterlauf, der nur auf stdout stand und weg war, der
Fahrtenbuch-Fall: fuenf von sechs Befunden erneut untersucht, weil niemand
vermerkt hatte, dass das Raster schon abgesucht war).

UND ein Raster ohne den BLICK, der es absuchte, behauptet eine
Vollstaendigkeit, die es nicht hat (Einwand des Betreibers): derselbe
Durchgang liefert in einer anderen Sitzung ein anderes Ergebnis, weil sich
der Bestand bewegt (Beleg: ab_vergleich_abruf_2026-08-07 wuchs waehrend des
Laufs von 1971 auf 1974 Knoten -- von der Gegenprobe beanstandet), weil der
Abruf je nach Prompt anderes einspielt, und weil ein Sucher mit engem
Kontextfenster weniger halten kann als einer mit weitem.

BAUFORM: dieselbe Beistelldatei-Bauform wie gegenprobe.py (dort NUR gelesen,
nicht importiert -- dieses Modul braucht keinen Server und keine der
gepruefungsspezifischen Funktionen von dort, nur dasselbe Muster:
<ergebnis>.json bekommt ein <ergebnis>.json.rasterblick.json daneben).

WAS DER BLICK ENTHAELT, und warum jedes Feld GEMESSEN statt geraten ist:
  - session/actor/model: dieselben drei Spalten wie an jedem Knoten/jeder
    Lehre (Auftrag 2026-08-06) -- hier vom Aufrufer uebergeben, nicht neu
    erfunden.
  - bestand: Knoten-/Lehren-/Kantenzahl, LIVE aus knowledge.db gezaehlt in
    demselben Aufruf, der den Vermerk schreibt -- keine Konstante, die
    schon beim naechsten Schreibvorgang veraltet waere.
  - kontextfenster: MUSS der Aufrufer mitgeben. Dieses Modul misst es nicht
    selbst -- das waere ein zweites, staerker geratenes Werkzeug fuer eine
    Frage, die nur die suchende Sitzung selbst beantworten kann (siehe
    Memory-Lehre 'Kontextstand messen, nicht schaetzen': der Fuellstand
    steht in einer Transcript-Zeile, die nur der Sucher liest). Ein Aufruf
    ohne dieses Feld wird ABGEWIESEN, nicht mit None aufgefuellt -- gleiche
    Haltung wie annahme_erfassen: ein Pflichtfeld zwingt zur Aussage, ein
    optionales wuerde sie nur nahelegen.

Aufruf:
    python3 rasterblick.py --fehlende            # Ergebnisdateien ohne Vermerk
    python3 rasterblick.py --melder               # nur sprechen, wenn welche fehlen
    python3 rasterblick.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "haken"))
import ort  # noqa: E402

CET = timezone(timedelta(hours=2))
RUNS = ort.WURZEL / "runs"

# Unter dieser Zahl ist die Meldung Rauschen -- ein einzelner Rueckstand
# passiert waehrend jeder laufenden Auswertung (die Datei existiert, der
# Vermerk folgt Sekunden spaeter). Erst eine Haeufung zeigt eine echte
# Luecke. Kleiner als pruefer.MINDESTZAHL, weil hier keine Prozentquote
# gebildet wird, sondern schlicht gezaehlt -- 3 fehlende Vermerke sind 3
# nicht wiederholbare Suchen, unabhaengig davon, wie viele es insgesamt gibt.
MELDESCHWELLE = 3


def _jetzt() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S%z")


def _verbindung(db: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db or ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def bestandsstand(conn: sqlite3.Connection) -> dict:
    """Knoten-/Lehren-/Kantenzahl LIVE -- der Anker fuer 'welches Gelaende
    wurde damals abgesucht', siehe ab_vergleich_abruf_2026-08-07 (Bestand
    wuchs waehrend des Laufs, die Gegenprobe beanstandete es genau deshalb)."""
    knoten = conn.execute("SELECT COUNT(*) n FROM knowledge_nodes WHERE zurueckgezogen = 0").fetchone()["n"]
    lehren = conn.execute("SELECT COUNT(*) n FROM lessons_learned WHERE status = 'active'").fetchone()["n"]
    kanten = conn.execute("SELECT COUNT(*) n FROM knowledge_relations").fetchone()["n"]
    return {"knoten": knoten, "lehren": lehren, "kanten": kanten}


def blick(session: str, kontextfenster: int | str, *, actor: str = "unbekannt",
         model: str = "unbekannt", conn: sqlite3.Connection | None = None) -> dict:
    """Baut den Rastervermerk fuer EINEN Durchgang. Wirft ValueError, wenn
    Pflichtangaben fehlen -- ein Vermerk ohne session oder kontextfenster
    waere kein Blick, sondern eine Behauptung."""
    if not session:
        raise ValueError("rasterblick.blick: session fehlt -- wer suchte, muss benennbar sein")
    if kontextfenster in (None, "", 0):
        raise ValueError("rasterblick.blick: kontextfenster fehlt -- ohne diese Zahl behauptet "
                         "der Vermerk eine Vollstaendigkeit, die er nicht belegen kann")
    eigene_verbindung = conn is None
    conn = conn or _verbindung()
    try:
        b = bestandsstand(conn)
    finally:
        if eigene_verbindung:
            conn.close()
    return {
        "session": session,
        "actor": actor,
        "model": model,
        "kontextfenster": kontextfenster,
        "bestand": b,
        "erzeugt_am": _jetzt(),
    }


def sidecar(datei: Path) -> Path:
    return datei.with_suffix(datei.suffix + ".rasterblick.json")


def ablegen(ergebnisdatei: Path, blick_daten: dict, force: bool = False) -> Path:
    """Schreibt den Vermerk als Beistelldatei. Ohne --force keine
    Ueberschreibung -- ein Rastervermerk beschreibt den Blick VON DAMALS,
    ein spaeteres Ueberschreiben waere dieselbe stille Umschreibung, gegen
    die die Herkunftsschranke an Knoten baut."""
    ziel = sidecar(ergebnisdatei)
    if ziel.exists() and not force:
        raise FileExistsError(f"{ziel} existiert bereits -- --force fuer eine bewusste Ueberschreibung")
    ziel.write_text(json.dumps(blick_daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ziel


def verlust_vermerken(ergebnisdatei: Path, grund: str) -> Path:
    """Haelt fest, dass der Blick dieser Suche NICHT MEHR ZU HABEN ist.

    Anlass 2026-08-11: 30 Ergebnisdateien standen ohne Vermerk, der Melder
    schlug bei jedem Sitzungsstart an, und es gab genau zwei Auswege -- einen
    Vermerk erfinden oder den Melder ignorieren. Beide sind schlechter als das
    Dritte: aufschreiben, dass nichts aufgeschrieben wurde.

    Die naheliegende Erklaerung war zudem falsch und wurde gemessen statt
    geglaubt: 'die Dateien sind aelter als das Werkzeug' stimmt nicht --
    rasterblick.py kam am 2026-08-09T10:19:22+0200 ins Repo, die unvermerkten
    Ergebnisdateien danach (12:12, 16:30). Das Werkzeug war da und wurde nicht
    aufgerufen; das ist kein Altbestand, sondern eine gebaute Regel ohne
    Wirkung.

    Was hier NICHT passiert: session, actor, model, kontextfenster und
    Bestandsstand von damals werden nicht rekonstruiert. Sie sind weg. Ein
    nachtraeglich gefuellter Blick waere eine Behauptung ueber eine Sitzung,
    die niemand mehr befragen kann -- und der Vermerk existiert gerade, um
    solche Behauptungen zu verhindern.

    Preis: der Melder schweigt danach zu diesen Dateien. Genau richtig -- er
    hat seinen Zweck erfuellt, sobald der Verlust festgehalten ist. Neue
    Ergebnisdateien ohne Vermerk loesen ihn unveraendert aus.
    """
    return ablegen(ergebnisdatei, {
        "status": "nicht_rekonstruierbar",
        "grund": grund,
        "abgeschlossen_am": _jetzt(),
        "session": None, "actor": None, "model": None,
        "kontextfenster": None, "bestand": None,
    })


def fehlende(runs: Path = RUNS) -> list[Path]:
    """Ergebnisdateien unter runs/*.json ohne Rastervermerk -- dieselbe
    Grundgesamtheit wie gegenprobe.offene() (*.json, keine .jsonl/.log/.md,
    keine Beistelldateien selbst)."""
    if not runs.exists():
        return []
    return [f for f in sorted(runs.glob("*.json"))
            if not f.name.endswith((".gegenprobe.json", ".rasterblick.json"))
            and not sidecar(f).exists()]


def melden(runs: Path = RUNS) -> dict | None:
    """URTEIL im Sinne von pruefer.py: FEHLKLASSE 'Raster ohne Vermerk' --
    eine Suche, die niemand als abgesucht vermerkt hat, wird beim naechsten
    Mal von vorn gemacht, ohne dass es auffaellt.
    PREIS EINES FEHLALARMS: gering, aber nicht null -- nicht jede Datei
    unter runs/*.json ist eine Rastersuche im engen Sinn (Gitterlauf/
    Korpusdurchgang); ein einzelner Ad-hoc-Messlauf wird hier mitgezaehlt,
    obwohl 'von vorn suchen' fuer ihn wenig kostet. Wer das beurteilen will,
    sieht sich die Dateinamen an -- der Melder listet sie."""
    f = fehlende(runs)
    if len(f) < MELDESCHWELLE:
        return None
    return {
        "pruefung": "rasterblick:fehlende_vermerke",
        "befund": f"{len(f)} Ergebnisdatei(en) unter runs/ ohne Rastervermerk: "
                  + ", ".join(p.name for p in f[:5]) + (" ..." if len(f) > 5 else ""),
        "fehlklasse": "Raster ohne Vermerk -- eine Suche ohne festgehaltenes WAS abgesucht wurde "
                      "ist nicht wiederholbar, nur wiederholbar von vorn",
        "fehlalarm_kostet": "gering: ein einzelner Ad-hoc-Lauf ohne Gitter-/Korpuscharakter zaehlt "
                            "mit, obwohl ein erneuter Durchlauf fuer ihn wenig kostet",
    }


def _selftest() -> None:
    import tempfile

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE knowledge_nodes (zurueckgezogen INTEGER)")
    conn.execute("CREATE TABLE lessons_learned (status TEXT)")
    conn.execute("CREATE TABLE knowledge_relations (id INTEGER)")
    conn.executemany("INSERT INTO knowledge_nodes VALUES (?)", [(0,), (0,), (1,)])
    conn.executemany("INSERT INTO lessons_learned VALUES (?)", [("active",), ("zurueckgezogen",)])
    conn.execute("INSERT INTO knowledge_relations VALUES (1)")

    b = bestandsstand(conn)
    assert b == {"knoten": 2, "lehren": 1, "kanten": 1}, b

    # Negativfall zuerst: ohne kontextfenster/session wird ABGEWIESEN, nicht
    # mit einem Platzhalter aufgefuellt.
    try:
        blick("sess-1", None, conn=conn)
        assert False, "kontextfenster fehlt -- muss ValueError werfen"
    except ValueError:
        pass
    try:
        blick("", 4096, conn=conn)
        assert False, "session fehlt -- muss ValueError werfen"
    except ValueError:
        pass

    v = blick("sess-1", 8192, actor="test", model="claude/opus-5", conn=conn)
    assert v["bestand"] == b and v["kontextfenster"] == 8192 and v["session"] == "sess-1"

    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp)
        (runs / "a.json").write_text("{}")
        (runs / "b.json").write_text("{}")
        (runs / "b.json.gegenprobe.json").write_text("{}")  # keine Ergebnisdatei, kein Kandidat
        (runs / "c.jsonl").write_text("{}")                  # falsche Endung, kein Kandidat

        f = fehlende(runs)
        assert {p.name for p in f} == {"a.json", "b.json"}, f

        pfad = ablegen(runs / "a.json", v)
        assert pfad.name == "a.json.rasterblick.json" and pfad.exists()
        f2 = fehlende(runs)
        assert {p.name for p in f2} == {"b.json"}, "a.json hat jetzt einen Vermerk"

        # Ueberschreiben ohne --force ist verboten.
        try:
            ablegen(runs / "a.json", v)
            assert False, "ein bestehender Vermerk darf nicht klanglos ueberschrieben werden"
        except FileExistsError:
            pass
        ablegen(runs / "a.json", v, force=True)  # mit force geht es

        # Unter der Meldeschwelle schweigt der Melder.
        assert melden(runs) is None, "ein fehlender Vermerk unter der Schwelle ist kein Befund"
        (runs / "d.json").write_text("{}")
        (runs / "e.json").write_text("{}")
        m = melden(runs)
        assert m and "3 Ergebnisdatei" in m["befund"] and m["fehlklasse"] and m["fehlalarm_kostet"]

        # Verlustvermerk: bringt den Melder zum Schweigen, OHNE etwas zu erfinden.
        for name in ("b.json", "d.json", "e.json"):
            verlust_vermerken(runs / name, "Lauf beendet, Blick nicht mehr befragbar")
        assert fehlende(runs) == [], "nach dem Abschluss darf keine Datei mehr offen sein"
        assert melden(runs) is None, "der Melder muss danach schweigen"
        vermerkt = json.loads(sidecar(runs / "b.json").read_text())
        assert vermerkt["status"] == "nicht_rekonstruierbar"
        assert vermerkt["kontextfenster"] is None and vermerkt["bestand"] is None, \
            "ein Verlustvermerk darf keine Zahl behaupten, die niemand mehr kennt"
        assert vermerkt["grund"], "ohne Grund waere es ein stiller Abschluss"

        # Und eine NEUE Ergebnisdatei loest den Melder unveraendert aus --
        # der Abschluss gilt dem Bestand, nicht der Regel.
        for name in ("f.json", "g.json", "h.json"):
            (runs / name).write_text("{}")
        assert melden(runs), "neue Dateien ohne Vermerk muessen weiter anschlagen"

    print("selftest ok (16 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fehlende", action="store_true", help="Ergebnisdateien ohne Rastervermerk auflisten")
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn die Meldeschwelle erreicht ist")
    p.add_argument("--verlust-abschliessen", metavar="GRUND",
                    help="fuer JEDE Datei ohne Vermerk festhalten, dass der Blick verloren ist "
                         "(rekonstruiert nichts, siehe verlust_vermerken)")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--runs", type=Path, default=RUNS)
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.verlust_abschliessen:
        offen = fehlende(a.runs)
        for pfad in offen:
            verlust_vermerken(pfad, a.verlust_abschliessen)
            print(f"  verloren vermerkt: {pfad.name}")
        print(f"\n{len(offen)} Datei(en) als nicht rekonstruierbar abgeschlossen. "
              "Nichts erfunden -- der Verlust steht jetzt in der Akte.")
        return

    if a.melder:
        m = melden(a.runs)
        if m:
            print(f"⚠️ Rasterblick: {m['befund']} ({m['fehlklasse']})")
        return

    f = fehlende(a.runs)
    if f:
        print(f"{len(f)} Ergebnisdatei(en) ohne Rastervermerk:")
        for pfad in f:
            print(f"  {pfad.name}")
    else:
        print("Rasterblick: alle Ergebnisdateien unter runs/ haben einen Vermerk.")


if __name__ == "__main__":
    main()
