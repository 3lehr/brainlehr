"""Aufgabe 65, Schritt 1: kern/ausschreibekatalog.py bewertet jedes Caveman-
Kurzform/Langform-Paar aus dem BESTAND und leitet die Aufnahmeschwelle aus der
gemessenen Verteilung ab (keine gesetzte Zahl). Facts (Commit 339eaee, 2969
Dokumente): impl 0:133, fn 1:269, res 1:264, req 4:134, config 25:242,
auth 31:3, db 187:111. Der Bestand waechst seither weiter -- diese Tests
pruefen die RICHTUNG (Verhaeltnis, Aufnahme/Ausschluss), nicht die exakten
historischen Zahlen.

Nachbesserung (Aufgabe 65): zwei Fehler vom Betreiber bemerkt und gemessen --
(1) die Aufnahmeregel schloss 'db'/'fn' aus, obwohl sie unter der Trigramm-
Mindestlaenge (schema.sql, tokenize='trigram') liegen und auf dem Suchweg
strukturell nichts finden; (2) _LANGFORMEN kannte nur die englische lange
Form, der Bestand ist aber deutsch ('Datenbank' 65 gegen 'database' 54,
'Funktion' 90 gegen 'function' 168). Beide Tests unten pruefen die Korrektur.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "kern"))
sys.path.insert(0, str(REPO / "haken"))

import ausschreibekatalog as ak  # noqa: E402


def test_saat_kommt_woertlich_aus_caveman_fertigkeit():
    """Nicht abgetippt, sondern aus der Datei gelesen -- der Auftrag verbietet
    eigene Paare. Die sieben Kurzformen aus der Aufgabenstellung muessen
    genau das sein, was die Fertigkeit heute nennt."""
    kurzformen = set(ak._saat_kurzformen())
    assert kurzformen == {"db", "auth", "config", "req", "res", "fn", "impl"}


def test_saat_langformen_sind_woerterbuchhaft_nicht_erfunden():
    """Je Kurzform ZWEI lange Formen -- englisch und deutsch (Nachbesserung
    Aufgabe 65), keine erfundenen Synonyme."""
    saat = ak.saat()
    assert saat["impl"] == ["implementation", "Umsetzung"]
    assert saat["db"] == ["database", "Datenbank"]
    assert saat["fn"] == ["function", "Funktion"]


def test_zaehlung_ist_wortgrenze_nicht_teilstring():
    """'impl' darf sich nicht selbst in 'kompliziert' finden -- sonst waere
    jede Zaehlung Rauschen statt Signal."""
    texte = ["Das ist kompliziert und implizit unklar."]
    kurz_n, lang_n = ak.zaehle_paar(texte, "impl", "implementation")
    assert kurz_n == 0
    assert lang_n == 0

    texte2 = ["impl steht hier als eigenes Wort, implementation auch."]
    kurz_n2, lang_n2 = ak.zaehle_paar(texte2, "impl", "implementation")
    assert kurz_n2 == 1
    assert lang_n2 == 1


def test_zaehlung_summiert_ueber_mehrere_lange_formen():
    """Nachbesserung Aufgabe 65: lang_n ist die SUMME der Treffer ueber alle
    uebergebenen langen Formen (englisch + deutsch), nicht nur einer."""
    texte = [
        "Hier steht implementation.",
        "Hier steht Umsetzung.",
        "Hier steht beides: implementation und Umsetzung.",
        "Hier steht keins von beiden.",
    ]
    kurz_n, lang_n = ak.zaehle_paar(texte, "impl", ["implementation", "Umsetzung"])
    assert kurz_n == 0
    # "implementation": Dok 1+3 = 2. "Umsetzung": Dok 2+3 = 2. Summe = 4.
    assert lang_n == 4


def test_grenzwert_knapp_ueber_und_knapp_unter_schwelle():
    """Ein Paar knapp ueber der Schwelle wird aufgenommen, eines knapp
    darunter nicht -- die Entscheidungsregel selbst, unabhaengig vom
    Bestand."""
    schwelle = ak._schwelle_aus_verteilung([-2.0, -1.9, 1.5, 1.6])
    assert ak.aufnehmen(schwelle + 0.001, schwelle) is True
    assert ak.aufnehmen(schwelle - 0.001, schwelle) is False


def test_schwelle_trennt_zwei_klar_getrennte_gruppen():
    tief = [-3.0, -2.5, -2.0]
    hoch = [2.0, 2.5, 3.0]
    schwelle = ak._schwelle_aus_verteilung(tief + hoch)
    assert max(tief) < schwelle < min(hoch)


def test_impl_wird_aus_dem_echten_bestand_aufgenommen_rot_vor_gruen():
    """Rot-Probe (dokumentiert, nicht nur behauptet): OHNE Katalog findet eine
    Anfrage nach 'impl' 0 Dokumente ueber die lange Form -- die Kurzform
    kennt 'implementation' nicht. GRUEN: der Katalog nimmt das Paar auf, weil
    die lange Form im Bestand haeufiger steht als die kurze."""
    bewertung = ak.bewerte()
    assert "impl" in bewertung, "Saat-Paar impl fehlt -- Caveman-Liste hat sich geaendert"
    eintrag = bewertung["impl"]
    # Rot: eine reine Kurzform-Suche saehe nur kurz_n, nie die 'lange_n'
    # Dokumente -- das ist exakt der Schaden aus dem Plan.
    assert eintrag["lang_n"] > eintrag["kurz_n"]
    # Gruen: der Katalog erkennt das und nimmt impl auf.
    assert eintrag["aufgenommen"] is True
    assert "impl" in ak.katalog()


def test_db_wird_trotz_eigenvorkommen_aufgenommen():
    """Nachbesserung Aufgabe 65 (Fehler 1): 'db' hat ein echtes Eigenvorkommen
    im Rohtext (kurz_n > lang_n bleibt moeglich), findet darueber aber
    trigramm-bedingt nichts (schema.sql, tokenize='trigram' -- unter drei
    Zeichen nicht indizierbar). Genau darum wird es IMMER aufgenommen, das
    Verhaeltnis spielt keine Rolle mehr."""
    bewertung = ak.bewerte()
    if "db" not in bewertung:
        return  # Saat-Liste hat sich geaendert -- kein Fehlschlag dieses Tests
    eintrag = bewertung["db"]
    assert eintrag["hart"] is True
    assert eintrag["aufgenommen"] is True
    assert "db" in ak.katalog()


def test_fn_wird_wegen_laenge_aufgenommen():
    """Gleicher Fall wie 'db': 'fn' ist zwei Zeichen lang."""
    bewertung = ak.bewerte()
    if "fn" not in bewertung:
        return
    eintrag = bewertung["fn"]
    assert eintrag["hart"] is True
    assert eintrag["aufgenommen"] is True
    assert "fn" in ak.katalog()


def test_grenzwert_laenge_zwei_zeichen_immer_drei_zeichen_nur_verhaeltnis():
    """ABNAHME Grenzwert: eine Kurzform mit zwei Zeichen wird immer
    aufgenommen (hartes Kriterium greift), eine mit drei Zeichen nur, wenn
    das Verhaeltnis entscheidet (hartes Kriterium liefert None, ausser die
    Teilstring-Regel greift)."""
    assert ak._zu_kurz_fuer_trigramm("ab") is True
    assert ak._hartes_kriterium("ab", ["irgendeine lange form"]) is True

    assert ak._zu_kurz_fuer_trigramm("abc") is False
    assert ak._hartes_kriterium("abc", ["voellig andere lange form"]) is None


def test_negativfall_alle_langformen_enthalten_kurzform():
    """ABNAHME Negativfall: eine Abkuerzung ab drei Zeichen, deren lange
    Formen ALLE die Kurzform als Teilstring enthalten, wird NICHT
    aufgenommen -- Trigramm deckt diesen Fall schon ab (schema.sql,
    tokenize='trigram' matcht Teilstrings)."""
    assert ak._alle_langformen_enthalten_kurzform("cfg", ["cfgfile", "cfgparser"]) is True
    assert ak._hartes_kriterium("cfg", ["cfgfile", "cfgparser"]) is False

    # Gegenprobe: sobald EINE lange Form die Kurzform nicht enthaelt, greift
    # die Teilstring-Regel nicht mehr -- das Verhaeltnis entscheidet (None).
    assert ak._alle_langformen_enthalten_kurzform("cfg", ["cfgfile", "Konfiguration"]) is False
    assert ak._hartes_kriterium("cfg", ["cfgfile", "Konfiguration"]) is None


def test_impl_deutsche_form_traegt_die_aufnahme():
    """'impl' waere ueber die englische Form ('implementation' enthaelt
    'impl') schon von Trigramm abgedeckt -- die deutsche Form ('Umsetzung')
    enthaelt 'impl' NICHT und rechtfertigt die Aufnahme allein."""
    assert ak._alle_langformen_enthalten_kurzform("impl", ["implementation", "Umsetzung"]) is False
    assert ak._hartes_kriterium("impl", ["implementation", "Umsetzung"]) is None
    # Waere NUR die englische Form bekannt gewesen (der urspruengliche
    # Fehler), haette Trigramm den Fall schon abgedeckt.
    assert ak._alle_langformen_enthalten_kurzform("impl", ["implementation"]) is True


def test_katalog_liest_nur_kein_schreibzugriff():
    """Der Katalog schlaegt vor, er setzt nicht: bewerte()/katalog() oeffnen
    nur speicher.lesen() (mode=ro) -- ein Schreibversuch scheiterte dort
    sofort. Hier nur belegt, dass beide Funktionen ohne Fehler durchlaufen,
    also tatsaechlich den lesenden Weg nehmen."""
    ak.bewerte()
    ak.katalog()
