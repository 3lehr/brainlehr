"""Ein Zeitstempel entsteht an EINER Stelle -- kern/zeitmarke.jetzt().

Aufgabe 111 Schritt 2. Diese Ratsche ist der Teil, der dem Beschluss vom
2026-08-06 gefehlt hat.

DER BEFUND, der sie noetig macht (gemessen 2026-08-14): 104 Stellen in 74
Dateien bauen ihren Zeitstempel selbst, in vier verschiedenen Bauarten. Ein
Beschluss, der sich an 104 Stellen wiederholen muss, wird an einer davon
gebrochen -- nicht aus Nachlaessigkeit, sondern weil niemand 104 Stellen im
Kopf hat. Genau so kam die Form '+0200' ohne Doppelpunkt zurueck, an der
schon am 2026-08-06 der Wecker still gescheitert war.

WAS DIESE RATSCHE VERBIETET, und was ausdruecklich NICHT:

  verboten   ein fest verdrahteter Versatz ('+01:00' im Format, oder
             timezone(timedelta(hours=2))) -- er ist ein halbes Jahr lang
             richtig und danach ein halbes Jahr lang falsch.
  verboten   '%z' in einem Zeitstempelformat -- liefert '+0200' ohne
             Doppelpunkt und macht Textvergleiche still falsch.
  erlaubt    datetime.now(BERLIN) fuer ANZEIGE und Dateinamen. Innen UTC,
             aussen Ortszeit; ein Dateiname mit Ortszeit ist kein
             gespeicherter Zeitpunkt.
  erlaubt    kern/zeitmarke.py selbst -- dort steht die Bauart, die alle
             anderen benutzen sollen.

Rot vor gruen: gegen den Stand vor dieser Umstellung meldet
test_kein_fester_versatz 16 Fundstellen mit '%z' und zwei mit festem Versatz.
"""
from __future__ import annotations

import ast
import re
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w

# Wo Produktivcode liegt. tests/ und docs/ duerfen die alten Formen nennen --
# dieser Test tut es selbst.
ORDNER = ("kern", "haken", "melder", "migrationen", "messungen",
          "schreibpruefstand", "pruefstand")

# Die eine erlaubte Ausnahme, namentlich statt als Muster: dort steht die
# Bauart, die alle anderen benutzen.
QUELLE = "kern/zeitmarke.py"

# Nur EINE Ausnahme, und sie ist strukturell unvermeidbar: in zeitmarke.py
# steht die Bauart selbst. Die Umstellungsmigrationen brauchen keine mehr --
# sie nennen den alten Wert in ihrem Docstring, und ein Docstring ist im
# Syntaxbaum kein Aufruf (siehe _fundstellen).
AUSNAHMEN = {QUELLE}

# GEMESSEN und danach verschaerft: Das erste Muster ('+01:00' irgendwo in
# einer Zeichenkette) lieferte 143 Treffer, fast alle Fehlalarme -- feste
# Zeitstempel in Testdaten, Beispielwerte in Messskripten, Zeitpunkte in
# Vergleichen. Eine Wache mit dieser Quote wird binnen einer Woche ignoriert.
#
# Gesucht ist die ERZEUGUNG eines Zeitstempels mit festem Versatz, nicht jedes
# Vorkommen eines Versatzes. Zwei Bauarten treffen das:
FESTER_VERSATZ = re.compile(
    r"""strftime\([^)]*[+-]\d{2}:?\d{2}   # strftime("...+01:00") -- Format mit Versatz
      | timezone\(\s*timedelta\(          # timezone(timedelta(hours=2))
    """, re.X)
PROZENT_Z = re.compile(r"strftime\([^)]*%z")


def _dateien():
    for ordner in ORDNER:
        p = WURZEL / ordner
        if not p.exists():
            continue
        for f in sorted(p.rglob("*.py")):
            if str(f.relative_to(WURZEL)) in AUSNAHMEN:
                continue
            yield f


def _fundstellen(muster: re.Pattern) -> list[str]:
    """Sucht in AUFRUFEN, nicht in Zeilen.

    Zeilenweise Textsuche hat zweimal Prosa beanstandet: kern/zeitfenster.py:18
    (eine Doku-Zeile) und den Kopf der Umstellungsmigration, die den alten
    Vorgabewert nennen MUSS, um ihn zu suchen. Beide Male war die naheliegende
    Antwort eine Ausnahmeliste -- und eine wachsende Ausnahmeliste ist das
    Kennzeichen einer Wache, die am falschen Gegenstand misst.

    Ueber den Syntaxbaum entfaellt die Frage: ein Docstring ist kein Aufruf,
    ein Kommentar auch nicht. Was bleibt, ist genau das, was zur Laufzeit
    einen Zeitstempel BAUT.
    """
    treffer = []
    for f in _dateien():
        quelle = f.read_text(encoding="utf-8")
        try:
            baum = ast.parse(quelle)
        except SyntaxError:
            continue
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call):
                continue
            abschnitt = ast.get_source_segment(quelle, knoten) or ""
            if muster.search(abschnitt):
                treffer.append(f"{f.relative_to(WURZEL)}:{knoten.lineno}")
    return sorted(set(treffer))


def test_kein_prozent_z_in_zeitstempeln():
    """'%z' liefert '+0200' ohne Doppelpunkt. Ein Textvergleich dagegen
    scheitert still -- kein Fehler, nur ein leeres Ergebnis. So wurde der
    Fehler am 2026-08-06 ueberhaupt erst gefunden."""
    treffer = _fundstellen(PROZENT_Z)
    assert not treffer, (
        f"{len(treffer)} Stelle(n) bauen einen Zeitstempel mit '%z': "
        + ", ".join(treffer)
        + " -- kern/zeitmarke.jetzt() benutzen (UTC mit 'Z')")


def test_kein_fester_versatz():
    """Ein fest verdrahteter Versatz ist ein Fehler mit Verzoegerung: ein
    halbes Jahr richtig, ein halbes Jahr falsch."""
    treffer = _fundstellen(FESTER_VERSATZ)
    assert not treffer, (
        f"{len(treffer)} Stelle(n) nageln einen Zeitversatz fest: "
        + ", ".join(treffer)
        + " -- kern/zeitmarke.jetzt() benutzen; fuer Anzeige "
        "kern/zeitmarke.als_ortszeit()")


def test_die_quelle_selbst_ist_ausgenommen_und_liefert_die_zielform():
    """Gegenprobe zur Ausnahme: ohne sie waere die Ratsche gruen zu bekommen,
    indem man die Quelle mitverbietet und gar keinen Zeitstempel mehr baut."""
    _sys.path.insert(0, str(WURZEL / "kern"))
    import zeitmarke
    assert zeitmarke.UTC_MUSTER.match(zeitmarke.jetzt())


def test_ortszeit_fuer_anzeige_bleibt_erlaubt():
    """Sonst schlaegt die Ratsche auch dort zu, wo Ortszeit richtig ist --
    Anzeige und Dateinamen. 'Innen UTC, aussen Ortszeit' war schon am
    2026-08-06 die Entscheidung, nicht 'ueberall UTC'."""
    assert not FESTER_VERSATZ.search('datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")')
    assert not PROZENT_Z.search('datetime.now(BERLIN).isoformat(timespec="seconds")')


def test_kein_now_iso_klon_baut_ortszeit():
    """DIE LUECKE, die diese Ratsche zunaechst NICHT hatte -- gefunden von
    tests/test_zeitstempel_versatz.py, nicht von hier.

    datetime.now(BERLIN).isoformat(timespec="seconds") ist weder '%z' noch ein
    fester Versatz. Die beiden Muster oben gehen daran vorbei, und genau so
    blieben vier now_iso()-Klone stehen (build_embeddings, lesson_recorder,
    fix_namensraum_knoten, migrate_knowledge), nachdem alle 40 gemeldeten
    Stellen umgestellt waren.

    Die Lehre steckt im Ablauf, nicht im Muster: Eine Wache findet nur, wonach
    sie sucht. Dass die vier Klone auffielen, verdankt sich einem ZWEITEN Test
    mit einem anderen Massstab -- der eine prueft die Bauform im Text, der
    andere das Ergebnis zur Laufzeit. Keiner von beiden haette gereicht.
    """
    treffer = []
    for f in _dateien():
        text = f.read_text(encoding="utf-8")
        for nr, zeile in enumerate(text.splitlines(), 1):
            if zeile.lstrip().startswith("#"):
                continue
            if "now(BERLIN).isoformat" in zeile or "now(CET).isoformat" in zeile:
                treffer.append(f"{f.relative_to(WURZEL)}:{nr}")
    assert not treffer, (
        f"{len(treffer)} Stelle(n) bauen einen gespeicherten Zeitstempel als "
        "Ortszeit: " + ", ".join(treffer)
        + " -- kern/zeitmarke.jetzt() benutzen. Fuer ANZEIGE ist Ortszeit "
        "richtig, dann aber ueber kern/zeitmarke.als_ortszeit().")
