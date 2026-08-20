"""Wenn eine neue Achse dazukommt, welche Spalten werden dadurch zweiseitig?

DER ANLASS ist eine Betreiberfrage vom 2026-08-20: "Und was ist wenn uns in
3 Monaten etwas aehnliches auffaellt?" -- gestellt, nachdem an EINEM Tag
viermal dieselbe Fehlerklasse aufgetreten war (L-6af5ac): eine zweiseitige
Groesse einer Seite zugeschrieben. Alle vier Male hat sie der Betreiber
gefunden, nicht der Assistent.

DIE EINSICHT AUS DEM VIERTEN FALL: Eine Groesse kann HEUTE einseitig und
MORGEN zweiseitig sein, ohne dass sich an ihr etwas aendert -- es genuegt,
dass eine zweite Achse hinzukommt. `gilt_bis` ist als Spalte voellig richtig,
solange alle Regeln fuer alle gelten; sobald es Personenkreise gibt, ist
"gilt bis 31.12." unvollstaendig: bis wann FUER WEN?

WAS DIESER MELDER TUT und was nicht: Er beantwortet die Frage NICHT. Er
stellt sie -- an dem einen Punkt, an dem sie sich stellt, und ohne dass
jemand daran denken muss. melder/pruefer.py findet Spalten, die NICHTS
unterscheiden; dies ist die Umkehrung.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "melder"),
                str(Path(__file__).resolve().parent.parent)]
import neue_achse as na  # noqa: E402


def test_wenige_werte_ueber_viele_zeilen_ist_eine_achse():
    """Eine Achse gruppiert: wenige unterschiedliche Werte, viele Zeilen."""
    assert na.ist_achse(verschiedene=3, zeilen=5000)
    assert na.ist_achse(verschiedene=12, zeilen=5000)


def test_eine_kennung_ist_keine_achse():
    """NEGATIVFALL: Eine Spalte mit fast so vielen Werten wie Zeilen ist eine
    Kennung, keine Achse -- sie gruppiert nichts."""
    assert not na.ist_achse(verschiedene=4998, zeilen=5000)


def test_einwertige_spalte_ist_keine_achse():
    """NEGATIVFALL zur anderen Seite: Ein einziger Wert unterscheidet nichts.
    Das ist der Fall, den melder/pruefer.py bereits meldet -- hier waere es
    ein Doppelbefund."""
    assert not na.ist_achse(verschiedene=1, zeilen=5000)


def test_betroffene_spalten_sind_die_aussagenden():
    """Welche Spalten werden durch eine neue Achse zweiseitig? Die, die eine
    AUSSAGE ueber den Eintrag tragen -- Geltung, Rang, Freigabe. Nicht die
    technischen (id, Zeitstempel, Pruefsummen)."""
    betroffen = na.moeglich_zweiseitig(
        ["id", "path", "created_at", "gilt_bis", "norm_rang", "freigabe",
         "text_checksum", "access_count"])
    assert "gilt_bis" in betroffen and "norm_rang" in betroffen
    assert "freigabe" in betroffen and "access_count" in betroffen
    assert "id" not in betroffen and "created_at" not in betroffen
    assert "text_checksum" not in betroffen


def test_meldung_stellt_die_FRAGE_statt_sie_zu_beantworten():
    """Der Melder darf nicht behaupten, eine Spalte SEI zweiseitig -- das ist
    eine Aussage ueber die Fachlichkeit, die kein Zaehlwerk trifft. Er nennt
    die Achse, die Kandidaten und den Pruefsatz."""
    text = na.als_text([{"tabelle": "knowledge_nodes", "spalte": "kreis",
                         "verschiedene": 4, "zeilen": 5232,
                         "kandidaten": ["gilt_bis", "norm_rang"]}])
    assert "kreis" in text and "gilt_bis" in text
    assert "?" in text, "die Meldung muss eine Frage stellen"


def test_schweigt_ohne_neue_achse():
    assert na.als_text([]) == ""


def test_der_ausloeser_ist_die_NEUE_SPALTE_nicht_die_statistik(tmp_path):
    """DER UMBAU, nach dem ersten Lauf gegen den echten Bestand:

    Die statistische Erkennung (wenige Werte, viele Zeilen) meldete 21 Faelle
    -- darunter quell_hash, session und zurueckgezogen_am. Keine davon ist
    eine Achse; es sind Eigenschaften. Der Unterschied zwischen einer
    ZUGEHOERIGKEIT (Mandant, Kreis, Projekt) und einer EIGENSCHAFT (Hash,
    Zeitstempel, Zaehler) ist semantisch, nicht statistisch -- keine Zaehlung
    findet ihn. Und ein Melder mit 21 Zeilen wird ueberlesen.

    Der wirksame Ausloeser ist rauschfrei und braucht keine Heuristik: eine
    NEUE SPALTE im Schema. Sie ist ein Ereignis, kein Zustand -- genau dann
    stellt sich die Frage, und genau dann nur einmal."""
    zustand = tmp_path / "bekannt.json"
    alt = {"knowledge_nodes": ["id", "gilt_bis"]}
    neu = {"knowledge_nodes": ["id", "gilt_bis", "kreis"]}
    funde = na.neue_spalten(alt, neu)
    assert funde == [("knowledge_nodes", "kreis")]
    assert na.neue_spalten(neu, neu) == [], "ohne Aenderung keine Meldung"


def test_entfernte_spalte_meldet_nichts():
    """NEGATIVFALL: Eine WEGGEFALLENE Spalte stellt die Frage nicht -- sie
    nimmt hoechstens eine Achse zurueck."""
    assert na.neue_spalten({"t": ["a", "b"]}, {"t": ["a"]}) == []
