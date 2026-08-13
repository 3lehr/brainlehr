#!/usr/bin/env python3
"""Prueft kern/fundstelle.py -- vor allem den Fall, in dem NICHTS behauptet wird.

Die teure Fehlerklasse ist nicht "findet zu wenig", sondern "markiert die
falsche Zeile": eine gesetzte Markierung sieht aus wie ein Beleg. Darum
prueft jeder Positivtest hier einen Negativtest als Gegenprobe mit.

Die Tests am ECHTEN Korpus werden uebersprungen, wenn buckeberg nicht liegt --
die reinen Funktionen laufen immer, auch auf einem fremden Rechner.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kern import fundstelle as F  # noqa: E402

KORPUS = F.korpus_wurzel()
echt = pytest.mark.skipif(not KORPUS.is_dir(), reason=f"Korpus {KORPUS} liegt hier nicht")


# ─── Seitenrechnung: reine Funktion, laeuft ueberall ──────────────────────

VOLLTEXT = ("--- Seite 1 ---\nEinleitung ohne Zahlen\n"
            "--- Seite 2 ---\nGrundverguetung 50,00 EUR je Wohneinheit\n"
            "--- Seite 3 ---\nSchluss der Abrechnung\n")


@pytest.mark.parametrize("nadel,erwartet", [
    ("Einleitung ohne Zahlen", 1),
    ("Grundverguetung 50,00", 2),
    ("Schluss der Abrechnung", 3),
])
def test_seite_wird_getroffen(nadel, erwartet):
    assert F.seite_aus_volltext(VOLLTEXT, nadel) == erwartet


@pytest.mark.parametrize("nadel", ["Hausmeisterkosten", "", "   "])
def test_kein_treffer_gibt_keine_seite_und_nicht_seite_eins(nadel):
    # DER Test dieses Moduls. Seite 1 waere hier eine erfundene Fundstelle.
    assert F.seite_aus_volltext(VOLLTEXT, nadel) is None


def test_auszug_beginnt_nicht_bei_seite_eins():
    # Grenzwert: wer Marken ZAEHLT statt die letzte zu NEHMEN, liefert hier 1.
    assert F.seite_aus_volltext("--- Seite 7 ---\nnur hier\n", "nur hier") == 7


def test_zeilenumbruch_im_wortlaut_trifft_trotzdem():
    # Der Normalfall in PDF-Auszuegen -- eine wortgetreue Suche scheitert hier.
    vt = "--- Seite 4 ---\nGrundver-\nguetung   50,00\n"
    assert F.seite_aus_volltext(vt, "Grundver- guetung 50,00") == 4


def test_grossschreibung_ist_egal():
    assert F.seite_aus_volltext(VOLLTEXT, "GRUNDVERGUETUNG 50,00") == 2


def test_alle_seiten_statt_nur_der_ersten():
    vt = ("--- Seite 1 ---\nKopfzeile Musterfirma\nInhalt A\n"
          "--- Seite 2 ---\nKopfzeile Musterfirma\nInhalt B\n"
          "--- Seite 3 ---\nKopfzeile Musterfirma\nInhalt C\n")
    assert F.seiten_aus_volltext(vt, "Kopfzeile Musterfirma") == [1, 2, 3]
    assert F.seiten_aus_volltext(vt, "Inhalt B") == [2]
    assert F.seiten_aus_volltext(vt, "gibt es nicht") == []
    # seite_aus_volltext bleibt die erste -- aber sie ist jetzt nachweislich
    # nur EINE von mehreren, und genau das war vorher nicht sichtbar.
    assert F.seite_aus_volltext(vt, "Kopfzeile Musterfirma") == 1


@pytest.mark.parametrize("seiten,gesamt,erwartet", [
    ([1, 2, 3], 3, True),      # 3 von 3
    ([1, 2, 3], 5, True),      # 3 von 5 = 60 %, genau auf der Schwelle
    ([1, 2, 3], 6, False),     # 3 von 6 = 50 %, darunter
    ([1, 2], 2, False),        # Grenzwert: 2 von 2 ist keine Kopfzeile
    ([1], 10, False),
    ([], 10, False),
    ([1, 2, 3], 0, False),     # Negativfall: kein Nenner, keine Aussage
])
def test_laufender_kopf_grenzwerte(seiten, gesamt, erwartet):
    assert F.ist_laufender_kopf(seiten, gesamt) is erwartet


def test_format_erkennung():
    assert F.format_von("a.PDF") == "pdf"
    assert F.format_von("a.html") == "html" and F.format_von("a.htm") == "html"
    assert F.format_von("a.jpg") == "bild"
    # Was wir nicht kennen, geht an Quick Look -- und heisst darum "unbekannt",
    # nicht "nicht unterstuetzt".
    assert F.format_von("a.docx") == "unbekannt"
    assert F.format_von("ohneendung") == "unbekannt"


# ─── markierbar: aufschlagen und markieren sind zwei Aussagen ─────────────

def test_mehrdeutig_kennt_drei_werte():
    """Ohne Seitenmarken ist die Antwort unbekannt, nicht 'eindeutig'.

    9 von 367 Volltexten tragen keine Marken. Ein zweiwertiges Feld haette
    dort 'eindeutig' gemeldet -- eine Aussage aus einer Nichtmessung.
    """
    assert F.Fundstelle(True, "gerechnet", seiten=[4], suchtext="x").mehrdeutig is False
    assert F.Fundstelle(True, "gerechnet", seiten=[4, 9], suchtext="x").mehrdeutig is True
    assert F.Fundstelle(True, "gerechnet", seiten=[], suchtext="x").mehrdeutig is None
    # Wo nichts belegt ist, gibt es auch nichts Mehrdeutiges -- kein None.
    assert F.Fundstelle(False, "keine").mehrdeutig is False


def test_markierbar_haengt_am_suchtext_nicht_an_belegt():
    nur_seite = F.Fundstelle(True, "gepflegt", seite=4, datei="x.pdf")
    assert nur_seite.belegt is True and nur_seite.markierbar is False
    voll = F.Fundstelle(True, "gepflegt", seite=4, suchtext="50,00", datei="x.pdf")
    assert voll.markierbar is True


def test_als_dict_traegt_markierbar_mit():
    d = F.Fundstelle(False, "keine").als_dict()
    assert d["markierbar"] is False and d["belegt"] is False


# ─── ohne Angabe wird nichts behauptet ────────────────────────────────────

def test_ohne_angabe_keine_fundstelle():
    f = F.loese()
    assert f.belegt is False and f.seite is None and f.grund


def test_zu_kurzer_wortlaut_gilt_nicht_als_treffer():
    # Drei Zeichen finden ueberall etwas, und "ueberall" ist wie "nirgends".
    assert F.loese_text("ab").belegt is False


def test_unbekannte_quelle_stuerzt_nicht_ab():
    f = F.loese_quelle("999999")
    assert f.belegt is False and f.seite is None and "nicht verzeichnet" in f.grund


# ─── am echten Korpus ─────────────────────────────────────────────────────

@echt
def test_verwaltungszeilen_sind_keine_quellen():
    """Die Fehlerklasse, die diese Datei schon zweimal getroffen hat.

    quellen.json traegt Verwaltungszeilen mit fuehrendem Unterstrich. `_hinweis`
    ist eine Zeichenkette und faellt durch jeden Filter; `_rang` ist ein OBJEKT
    und rutschte durch `isinstance(v, dict)` -- gezaehlt wurden dadurch 49 statt
    48 Quellen, und die falsche Zahl stand bereits im Plandokument.
    """
    roh = json.loads((KORPUS / "dossier" / "quellen.json").read_text(encoding="utf-8"))
    verwaltung = [k for k in roh if k.startswith("_")]
    assert verwaltung, "kein Gegenbeispiel im Bestand -- dieser Test prueft dann nichts"
    # Mindestens eine Verwaltungszeile MUSS ein Objekt sein, sonst waere ein
    # Typfilter ausreichend und der Test bewacht die falsche Regel.
    assert any(isinstance(roh[k], dict) for k in verwaltung), \
        "keine objektwertige Verwaltungszeile mehr -- Test gegen die echte Falle neu bauen"

    e = F._quellenverzeichnis(KORPUS)
    assert all(k.isdigit() for k in e), f"Verwaltungszeile als Quelle gezaehlt: {sorted(set(e) - set(roh))}"
    for k in verwaltung:
        assert k not in e
        assert F.loese_quelle(k).belegt is False

    # Die Nummern laufen lueckenlos -- sonst stimmt der Nenner trotzdem nicht.
    nummern = sorted(int(k) for k in e)
    assert nummern == list(range(1, len(nummern) + 1)), f"Luecke in den Quellennummern: {nummern}"


# Stand der Abdeckung, gegen den die Ratsche laeuft. Erhoehen, wenn mehr
# Fundstellen gepflegt sind -- nie senken, um einen roten Test gruen zu machen.
# 2026-08-13: von 14 auf 30 gestiegen, nachdem kern/normfundstelle.py die
# HTML-Quellen aufgeloest hat (vorher 0 von 20, jetzt 16 von 20).
MINDESTENS_MARKIERBAR = 30
MINDESTENS_HTML = 16


@echt
def test_abdeckung_faellt_nicht_zurueck():
    """Ratsche auf die Zahl der markierbaren Quellen.

    Der Vorgaenger dieses Tests behauptete "jede markierbare Quelle ist ein
    PDF" -- richtig gemessen am 2026-08-13 vormittags, und noch am selben Tag
    ueberholt. Er trug seine eigene Ausserdienststellung im Docstring ("wird
    das falsch, ist es die Nachricht, dass HTML gepflegt wurde") und wurde
    genau dadurch rot. Was bleibt, ist nicht die Momentaufnahme, sondern die
    Richtung: die Abdeckung darf nicht sinken.
    """
    b = F.bestand()
    assert b["mit_fundstelle"] >= MINDESTENS_MARKIERBAR, (
        f"Abdeckung gesunken: {b['mit_fundstelle']} von {b['quellen']}, "
        f"erwartet mindestens {MINDESTENS_MARKIERBAR}")
    html = b["format_gegen_stelle"].get("html", {}).get("markierbar", 0)
    assert html >= MINDESTENS_HTML, f"HTML-Abdeckung gesunken: {html}"


@echt
def test_kein_format_bleibt_unbeachtet():
    """Jedes Format im Bestand taucht in der Kreuztabelle auf -- sonst zaehlt
    die Summenprobe zwar auf, verschweigt aber eine ganze Gattung."""
    b = F.bestand()
    assert set(b["formate"]) == set(b["format_gegen_stelle"])
    for f, zeile in b["format_gegen_stelle"].items():
        assert sum(zeile.values()) == b["formate"][f], f"{f}: {zeile} gegen {b['formate'][f]}"


@echt
def test_bestand_zaehlt_vollstaendig():
    b = F.bestand()
    assert b["erreichbar"] is True
    assert b["quellen"] > 0
    # Der Nenner geht auf: jede Quelle faellt in genau einen der drei Toepfe.
    assert b["mit_fundstelle"] + b["nur_seite"] + b["ohne_stelle"] == b["quellen"]
    assert b["volltexte"] > 0


@echt
def test_jede_gepflegte_fundstelle_loest_auf():
    """Rot vor gruen: ohne fundstelle.py loest keine einzige auf."""
    b = F.bestand()
    assert b["nummern_mit_fundstelle"], "keine gepflegte Fundstelle im Bestand"
    for nr in b["nummern_mit_fundstelle"]:
        f = F.loese_quelle(nr)
        assert f.belegt, f"Quelle {nr}: {f.grund}"
        assert f.markierbar, f"Quelle {nr} traegt Suchtext, ist aber nicht markierbar"
        # Die Seite ist OPTIONAL: Quelle 48 traegt nur den Suchtext, und die
        # Seite dazu findet PDFKit beim Anzeigen. Eine hier erfundene Seite
        # waere schlechter als keine. Nur unbrauchbare Werte sind verboten.
        assert f.seite is None or f.seite >= 1, f"Quelle {nr}: unbrauchbare Seite {f.seite}"
        assert Path(f.absolut).is_file(), f"Quelle {nr}: Datei fehlt -- {f.absolut}"


@echt
def test_quellen_ohne_stelle_schweigen():
    """Die Gegenprobe in die andere Richtung -- die wichtigere."""
    b = F.bestand()
    gepflegt = set(b["nummern_mit_fundstelle"])
    roh = json.loads((KORPUS / "dossier" / "quellen.json").read_text(encoding="utf-8"))
    andere = [k for k, v in roh.items() if isinstance(v, dict) and k not in gepflegt]
    assert andere, "kein Gegenbeispiel im Bestand -- dann prueft dieser Test nichts"
    for nr in andere:
        f = F.loese_quelle(nr)
        assert not f.markierbar, f"Quelle {nr} wird markiert, obwohl keine Stelle erfasst ist"
        assert f.grund, f"Quelle {nr} schweigt ohne Begruendung"


@echt
def test_volltextsuche_findet_und_rechnet_die_seite():
    f = F.loese_text("Feuchtigkeit und Schadstoffe")
    assert f.belegt and f.herkunft == "gerechnet"
    assert f.seite is not None and f.seite >= 1
    # Die Anzeige bekommt das Original, nicht die Textbeidatei.
    assert not f.absolut.endswith(".txt")
    assert Path(f.absolut).is_file()


@echt
@pytest.mark.parametrize("vordruck", [
    "Fax: 07231 58993150",          # Briefkopf, quer ueber 7 Dokumente
    "Basisversion Mustervertrag",   # laufender Kopf, 12 von 15 Seiten
])
def test_vordruck_wird_nicht_als_fundstelle_ausgegeben(vordruck):
    """Die Fehlerklasse, die das Konsil aufgedeckt hat.

    Vorher: belegt=True, Seite 1 -- weil der erste Treffer auf Seite 1 lag.
    Das ist woertlich das, wogegen dieses Modul gebaut wurde, nur eine Ebene
    tiefer: nicht eine erfundene Stelle, sondern eine echte, die nichts sagt.
    """
    f = F.loese_text(vordruck)
    assert f.belegt is False, f"{vordruck!r} als Fundstelle gemeldet: Seite {f.seite}"
    assert f.seite is None
    assert "grenzt die Stelle nicht ein" in f.grund


@echt
def test_eindeutige_stelle_ueberlebt_die_vordruck_regel():
    """Gegenprobe: die Regel darf nicht alles wegfiltern."""
    f = F.loese_text("Feuchtigkeit und Schadstoffe")
    assert f.belegt and f.seite is not None and f.mehrdeutig is False


@echt
def test_volltextsuche_erfindet_nichts():
    f = F.loese_text("Kernfusionsreaktor im Kellergeschoss der Anlage")
    assert f.belegt is False and f.seite is None and f.grund


@echt
def test_korpus_wird_nur_gelesen(tmp_path):
    """Die harte Grenze: buckeberg gehoert einem anderen Projekt."""
    vorher = {p: p.stat().st_mtime for p in (KORPUS / "dossier").glob("*.json")}
    F.loese_quelle("2")
    F.loese_text("Feuchtigkeit und Schadstoffe")
    nachher = {p: p.stat().st_mtime for p in (KORPUS / "dossier").glob("*.json")}
    assert vorher == nachher
