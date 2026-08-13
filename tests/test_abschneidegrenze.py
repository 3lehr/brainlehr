"""Aufgabe 69: Ein zu langer Eintrag verliert beim Einbetten seinen hinteren
Teil -- still. Eine Abrufzahl kann daran scheitern, ohne dass jemand die
Ursache sieht. Diese Datei prueft, dass die Grenze BEKANNT ist (Funktion
statt Messprotokoll), MITWANDERT (Quotient statt Zahl) und beim Schreiben
GEMELDET wird (Hinweis statt Sperre).

Gemessen 2026-08-13, runs/abschneidegrenze_bge_m3_2026-08-13.json, Commit
0b1ab4c: Ab 8000 Zeichen ist der Vektor EXAKT gleich, unabhaengig vom
angehaengten Suffix -- Gleichheit, nicht blosse Aehnlichkeit, ist der Beweis
fuers Abschneiden. Ollama meldete dafuer 2048 Token, also Ollamas
Vorgabewert num_ctx, nicht die 8192-Token-Grenze von bge-m3.

Rot vor gruen: Vor dem Fix gab es weder zeichengrenze() noch wird_gekappt()
-- alle Proben unten brachen mit AttributeError ab; der Kappungshinweis in
knowledge_add fehlte ebenfalls.

BEWUSST NICHT GEPRUEFT, weil es die Aussage nicht traegt: dass genau bei
8000 gekappt wird. Die Grenze ist eine Schaetzung aus einem gemessenen
Quotienten (Zeichen je Token haengt am Text -- deutsche Komposita brauchen
mehr Token je Zeichen als englische Prosa). Ein Test auf den exakten Wert
wuerde eine Genauigkeit behaupten, die die Groesse nicht hat.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


def test_grenze_waechst_mit_num_ctx():
    """Der Kern der Entscheidung: als Quotient hinterlegt, nicht als 8000.
    Wer num_ctx anhebt, bekommt die neue Grenze ohne Suchen-und-Ersetzen --
    eine festgeschriebene Zahl waere ab der ersten Aenderung falsch und
    wuerde trotzdem geglaubt."""
    assert embeddings.zeichengrenze(4096) == 2 * embeddings.zeichengrenze(2048)
    assert embeddings.zeichengrenze(8192) == 4 * embeddings.zeichengrenze(2048)


def test_grenze_trifft_die_messung():
    """Bei num_ctx=2048 muss die gerechnete Grenze den gemessenen Wert
    ergeben -- sonst stimmt der Quotient nicht mit dem Lauf ueberein, aus
    dem er stammt."""
    assert embeddings.zeichengrenze(2048) == 8000


def test_wird_gekappt_grenzwert():
    """Schwelle-1, Schwelle, Schwelle+1: genau AUF der Grenze wird noch
    nicht gekappt, erst darueber."""
    g = embeddings.zeichengrenze()
    assert not embeddings.wird_gekappt("x" * (g - 1))
    assert not embeddings.wird_gekappt("x" * g)
    assert embeddings.wird_gekappt("x" * (g + 1))


def test_wird_gekappt_negativfall():
    """Gegenprobe: ohne sie bestuende der Test darueber auch bei einer
    Funktion, die schlicht immer True liefert."""
    assert not embeddings.wird_gekappt("")
    assert not embeddings.wird_gekappt("ein kurzer Satz")
    assert not embeddings.wird_gekappt(None)


def test_textformel_liegt_an_einer_stelle():
    """L-361755: Eine kopierte Formel laeuft frueher oder spaeter
    auseinander -- dann meldete der Kappungshinweis eine Laenge, die gar
    nicht eingebettet wurde. Beide Nutzer muessen durch _embedding_text().
    """
    quelle = (_w / "knowledge_mcp_server.py").read_text(encoding="utf-8")
    # Die rohe Formel darf genau EINMAL vorkommen: in _embedding_text selbst.
    assert quelle.count('f"{path}\\n{title}\\n{summary}\\n{content') == 1, (
        "Die Textformel des Knoten-Vektors steht mehr als einmal im Quelltext "
        "-- sie gehoert ausschliesslich in _embedding_text()"
    )
    assert kms._embedding_text("/p", "T", "S", "C") == "/p\nT\nS\nC"
    assert kms._embedding_text("/p", "T", "S", None) == "/p\nT\nS\n"


def test_kappungshinweis_haengt_am_selben_text_wie_die_rechnung():
    """Der Hinweis muss ueber DENSELBEN Text urteilen, der eingebettet wird
    -- Pfad und Titel zaehlen mit. Ein Hinweis, der nur `content` misst,
    laege bei einem langen Pfad daneben."""
    lang = "x" * (embeddings.zeichengrenze() - 5)
    # content allein noch unter der Grenze, mit Pfad/Titel/Zusammenfassung darueber
    assert not embeddings.wird_gekappt(lang)
    assert embeddings.wird_gekappt(
        kms._embedding_text("/ein/langer/pfad", "Titel", "Zusammenfassung", lang))


def test_hinweis_statt_sperre():
    """Bewusst KEINE Abweisung: eine harte Schranke wuerde laufende fremde
    Sitzungen blockieren (am 2026-08-13 mit norm_art genau so passiert), und
    die neun Bestandsknoten waeren damit nicht mehr aenderbar. Dieser Test
    haelt die Entscheidung fest -- wer sie umdreht, faellt hier auf.
    """
    quelle = (_w / "knowledge_mcp_server.py").read_text(encoding="utf-8")
    stelle = quelle[quelle.index('result["kappung"]') - 1200:
                    quelle.index('result["kappung"]') + 200]
    assert "raise" not in stelle, (
        "Der Kappungshinweis darf nicht zur Ablehnung werden -- er ist ein "
        "Hinweis, weil die Grenze eine Schaetzung ist und eine Sperre "
        "laufende Sitzungen brechen wuerde"
    )
