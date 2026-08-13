#!/usr/bin/env python3
"""pdf_schwaerzen.py -- echte Schwaerzung in einem PDF, ohne das Layout zu zerreissen.

ANLASS (Betreiber, 2026-08-13): "dann muessen wir eine loesung fuers pdf
finden, wie macht das adobe? gibt es keine opensource frameworks dazu die
passend waeren?" -- und vorher: "wir muessen aufpassen das es das layout nicht
zerreisst!!"

WIE ADOBE ES MACHT, nachgeschlagen statt erinnert: zweistufig. Erst wird eine
Stelle MARKIERT, dann wird die Markierung ANGEWENDET -- und erst dabei
verschwindet der Inhalt. Solange nur markiert ist, steht der Text noch da.
Genau diese Zweistufigkeit bildet MuPDF nach.

WAS BENUTZT WIRD, und es war schon da: PyMuPDF 1.28.0 (MuPDF 1.29.0) liegt
seit heute Vormittag auf diesem Rechner, benutzt fuer die Schriftgroessen-
messung. `add_redact_annot()` markiert, `apply_redactions()` entfernt.
Kein neues Paket.

WARUM DAS LAYOUT HAELT: Es wird nichts ersetzt, sondern der Textinhalt an
genau diesen Koordinaten entfernt und die Flaeche geschwaerzt. Die uebrigen
Woerter behalten ihre Position -- gemessen an volksbank.pdf Seite 2:
Seitengroesse identisch, 295 Woerter werden 294, "EUR pro Wohneinheit" steht
unveraendert an derselben Stelle. Der Textersatz (`[geschwaerzt]`) haette die
Zeile von 78 auf 85 Zeichen verlaengert.

VIER STELLEN, AN DENEN EIN NAME EINE TEXTREDAKTION UEBERLEBT -- drei davon
haette ich ohne Nachschlagen uebersehen:
  1. Metadaten. Gemessen an volksbank.pdf: title = "Microsoft Word - Entwurf
     WEG Verwaltervertrag Auerbach". Ein Name im Dateititel, den keine
     Textschwaerzung je anfasst.
  2. XMP -- ein zweiter, unabhaengiger Metadatensatz.
  3. Inkrementelle Aktualisierung. Wer ein PDF "speichert", haengt beim
     Standardverfahren die Aenderung ANS ENDE und laesst das Alte stehen. Die
     geschwaerzte Fassung enthielte dann beides. Dagegen hilft nur
     Neuschreiben mit Aufraeumen (garbage=4), nie ein inkrementelles Sichern.
  4. Anmerkungen, Formularfelder, eingebettete Dateien und Bild-EXIF.

DIE ABNAHME IST NICHT "unsichtbar", SONDERN "NICHT AUFFINDBAR": Geprueft wird
in den ROHEN Bytes und in jedem entpackten Stream. Was dort noch steht, ist
da -- egal was die Anzeige zeigt.

Das ORIGINAL wird nie angefasst. Geschrieben wird immer eine Kopie: die
Schwaerzung ist eine Projektion fuer einen bestimmten Betrachter, keine
Aenderung am Bestand.

Aufruf:
    python3 app/werkzeuge/pdf_schwaerzen.py --quelle a.pdf --ziel b.pdf \
        --wortlaut "Diana Kunzmann" --wortlaut "50,00"
    python3 app/werkzeuge/pdf_schwaerzen.py --pruefe b.pdf --wortlaut "50,00"
    python3 app/werkzeuge/pdf_schwaerzen.py --selftest
"""

from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Metadatenfelder, die Freitext tragen und darum einen Namen enthalten koennen.
# `producer` und `format` bleiben: Sie sagen etwas ueber das Werkzeug, nicht
# ueber den Fall -- und wer sie loescht, macht die Datei schwerer pruefbar.
FREITEXT_FELDER = ("title", "author", "subject", "keywords", "creator")


def _entpackte_streams(rohbytes: bytes):
    """Jeder Stream der Datei, entpackt soweit moeglich."""
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", rohbytes, re.S):
        roh = m.group(1)
        try:
            yield zlib.decompress(roh)
        except Exception:
            yield roh


def _nadeln(wortlaut: str) -> list[bytes]:
    """Alle Gestalten, in denen dieser Wortlaut in einem PDF stehen kann.

    DER FEHLER, DEN DIESE FUNKTION BEHEBT -- gemessen am 2026-08-13, gefunden
    vom eigenen Selbsttest: Die erste Fassung suchte nur nach UTF-8-Bytes und
    fand NICHTS, obwohl der Name im Dokument stand. PDF speichert Text
    naemlich haeufig als HEX-Zeichenkette: aus "Verwalterin: Diana Kunzmann"
    wird `<56657277616c746572696e3a204469616e61204b756e7a6d616e6e>`.

    Eine Pruefung, die das uebersieht, meldet JEDE Datei als sauber -- auch
    eine, in der nichts geschwaerzt wurde. Dieselbe Fehlerklasse wie die
    textutil-Messung vom selben Tag: ein Verfahren, das nichts messen kann und
    trotzdem ein Ergebnis liefert.
    """
    formen: list[bytes] = []
    for kodierung in ("utf-8", "latin-1", "utf-16-be"):
        try:
            formen.append(wortlaut.encode(kodierung))
        except UnicodeEncodeError:
            pass
    # Hex-Zeichenkette, wie PyMuPDF und viele Erzeuger sie schreiben.
    formen.append(wortlaut.encode("latin-1", "ignore").hex().encode("ascii"))
    formen.append(wortlaut.encode("latin-1", "ignore").hex().upper().encode("ascii"))
    return [f for f in formen if f]


def _text_unabhaengig(pfad: Path) -> str:
    """Text mit einem ZWEITEN Werkzeug auslesen (poppler), nicht mit demselben.

    Wer mit derselben Bibliothek prueft, mit der er geschwaerzt hat, prueft
    seine eigene Annahme mit. pdftotext kommt aus einem anderen Haus.
    """
    import subprocess
    try:
        return subprocess.run(["pdftotext", "-layout", str(pfad), "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def steckt_noch_drin(pfad: Path, wortlaut: str) -> dict:
    """Die eigentliche Abnahme: NICHT auffindbar, nicht bloss unsichtbar.

    Fuenf unabhaengige Wege, weil jeder einzelne blind sein kann:
      1. rohe Bytes in allen ueblichen Kodierungen samt Hex
      2. jeder entpackte Stream, ebenso
      3. Textauslesung mit PyMuPDF
      4. Textauslesung mit pdftotext -- anderes Haus, andere Annahmen
      5. Metadaten und XMP
    """
    roh = pfad.read_bytes()
    nadeln = _nadeln(wortlaut)
    befund = {
        "klartext": sum(roh.count(n) for n in nadeln),
        "streams": sum(1 for s in _entpackte_streams(roh)
                       if any(n in s for n in nadeln)),
        "metadaten": [],
        "xmp": False,
        "text_pymupdf": 0,
        "text_poppler": 0,
    }
    if fitz is not None:
        with fitz.open(pfad) as d:
            befund["metadaten"] = [k for k, v in (d.metadata or {}).items()
                                   if v and wortlaut in str(v)]
            befund["xmp"] = wortlaut in (d.xref_xml_metadata() or "")
            befund["text_pymupdf"] = sum(s.get_text().count(wortlaut) for s in d)
    befund["text_poppler"] = _text_unabhaengig(pfad).count(wortlaut)

    # SECHSTE EBENE: Bildseiten. Alle fuenf Textpruefungen sind auf einem
    # reinen Scan BLIND -- dort steht der Name als Pixel, nicht als Zeichen.
    # Eine Pruefung, die das verschweigt, meldet Sicherheit, wo keine ist.
    if fitz is not None:
        with fitz.open(pfad) as d:
            blind = [i + 1 for i, s in enumerate(d) if seitenart(s) == "scan_ohne_text"]
        befund["bildseiten_ungeprueft"] = blind
    else:
        befund["bildseiten_ungeprueft"] = []

    befund["sauber"] = (befund["klartext"] == 0 and befund["streams"] == 0
                        and not befund["metadaten"] and not befund["xmp"]
                        and befund["text_pymupdf"] == 0
                        and befund["text_poppler"] == 0
                        and not befund["bildseiten_ungeprueft"])
    if befund["bildseiten_ungeprueft"]:
        befund["hinweis"] = ("Bildseiten ohne Textebene -- der Wortlaut kann dort "
                             "als Pixel stehen und ist so nicht pruefbar.")
    return befund


def seitenart(seite) -> str:
    """echt_text | scan_mit_text | scan_ohne_text | leer

    GEMESSEN im echten Bestand (1067 Seiten aus buckeberg):
      528 scan_mit_text · 508 echt_text · 27 scan_ohne_text · 4 leer

    Die Unterscheidung ist keine Statistik, sondern entscheidet, ob eine
    Schwaerzung ueberhaupt greifen KANN: Ohne Textebene findet search_for()
    nichts, es wird nichts markiert, nichts entfernt -- und die Datei sieht
    hinterher aus wie erfolgreich geschwaerzt.
    """
    text = seite.get_text().strip()
    bilder = seite.get_images()
    grossesBild = any((b[2] * b[3]) > 500_000 for b in bilder)
    if len(text) < 50:
        return "scan_ohne_text" if bilder else "leer"
    return "scan_mit_text" if grossesBild else "echt_text"


def _ocr_stellen(seite, wortlaute: list[str], dpi: int = 200) -> list:
    """Rechtecke der gesuchten Woerter auf einer Seite OHNE Textebene.

    Nutzt das macOS-Vision-Werkzeug daneben. Gemessen an einem echten reinen
    Scan: Vision erkennt 70 Bloecke mit Konfidenz 1,00, tesseract liefert an
    derselben Stelle "Fe a".

    Y WIRD GESPIEGELT: Vision rechnet von UNTEN links, PDF von OBEN links.
    Wer das vergisst, schwaerzt die falsche Zeile -- und das sieht plausibel
    aus, weil ja etwas geschwaerzt wurde.
    """
    import json as _json
    import subprocess
    import tempfile

    werkzeug = Path(__file__).resolve().parent / "ocr_stellen"
    if not werkzeug.is_file():
        return []
    with tempfile.TemporaryDirectory() as tmp:
        bild = Path(tmp) / "seite.png"
        seite.get_pixmap(dpi=dpi).save(bild)
        try:
            lauf = subprocess.run([str(werkzeug), str(bild), *wortlaute],
                                  capture_output=True, text=True, timeout=120)
            aus = _json.loads(lauf.stdout or "{}")
        except Exception:
            return []

    breite, hoehe = seite.rect.width, seite.rect.height
    rechtecke = []
    for s in aus.get("stellen", []):
        x0 = s["x"] * breite
        x1 = (s["x"] + s["breite"]) * breite
        # Spiegelung: Vision-y ist der UNTERE Rand, gemessen von unten.
        y1 = (1.0 - s["y"]) * hoehe
        y0 = (1.0 - (s["y"] + s["hoehe"])) * hoehe
        rechtecke.append(fitz.Rect(x0, y0, x1, y1))
    return rechtecke


def schwaerze(quelle: Path, ziel: Path, wortlaute: list[str],
              metadaten_saeubern: bool = True, ocr: bool = True) -> dict:
    """Schwaerzt jede Fundstelle jedes Wortlauts. Quelle bleibt unangetastet."""
    if fitz is None:
        raise RuntimeError("PyMuPDF fehlt -- ohne es gibt es keine echte Schwaerzung.")

    d = fitz.open(quelle)
    getroffen = {w: 0 for w in wortlaute}
    arten: dict[str, int] = {}
    ungeprueft: list[int] = []   # Seiten, auf denen nicht gesucht werden konnte
    try:
        for nr, seite in enumerate(d, start=1):
            art = seitenart(seite)
            arten[art] = arten.get(art, 0) + 1

            # REINER SCAN: ohne OCR kann hier nichts gefunden werden, und
            # das MUSS gemeldet werden statt still zu gelingen.
            if art == "scan_ohne_text":
                gefunden = _ocr_stellen(seite, [w for w in wortlaute if w.strip()]) if ocr else []
                if not gefunden and any(w.strip() for w in wortlaute):
                    ungeprueft.append(nr)
                for r in gefunden:
                    seite.add_redact_annot(r, fill=(0, 0, 0))
                    # Welches Wort getroffen wurde, weiss die Bildsuche nicht
                    # genauer als der Aufruf -- darum auf alle verteilt.
                    for w in wortlaute:
                        if w.strip():
                            getroffen[w] += 1
                            break
                seite.apply_redactions(images=2, graphics=1, text=0)
                continue

            for w in wortlaute:
                if not w.strip():
                    continue
                for r in seite.search_for(w):
                    # MARKIEREN. Die Flaeche wird schwarz, damit die Stelle
                    # sichtbar bleibt -- eine unsichtbare Schwaerzung
                    # verfaelscht den Text still.
                    seite.add_redact_annot(r, fill=(0, 0, 0))
                    getroffen[w] += 1
            # ANWENDEN, je Seite. images=2 entfernt getroffene Bildbereiche,
            # text=0 loescht den Text vollstaendig statt ihn nur zu ueberdecken.
            seite.apply_redactions(images=2, graphics=1, text=0)

        if metadaten_saeubern:
            meta = dict(d.metadata or {})
            for f in FREITEXT_FELDER:
                if meta.get(f):
                    meta[f] = ""
            d.set_metadata(meta)
            d.del_xml_metadata()

        ziel.parent.mkdir(parents=True, exist_ok=True)
        # NEU SCHREIBEN, nicht inkrementell sichern. Ein inkrementelles
        # Sichern haengt die Aenderung ans Ende und laesst das Alte stehen --
        # die geschwaerzte Datei enthielte dann beide Fassungen.
        d.save(ziel, garbage=4, deflate=True, clean=True, incremental=False)
    finally:
        d.close()

    return {"quelle": str(quelle), "ziel": str(ziel), "treffer": getroffen,
            "gesamt": sum(getroffen.values()),
            "seitenarten": arten,
            # Seiten, auf denen NICHT gesucht werden konnte. Das ist kein
            # Nebenwert: Wer sie ignoriert, haelt eine Datei fuer geschwaerzt,
            # in der ein reiner Scan den Namen weiter zeigt.
            "ungeprueft": ungeprueft}


# ─── Selbsttest ───────────────────────────────────────────────────────────

def _selftest() -> int:
    if fitz is None:
        print("pdf_schwaerzen: uebersprungen -- PyMuPDF fehlt")
        return 0

    import tempfile
    geheim, harmlos = "Diana Kunzmann", "Wohnungseigentum"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        quelle, ziel = tmp / "probe.pdf", tmp / "geschwaerzt.pdf"

        d = fitz.open()
        s = d.new_page()
        s.insert_text((72, 100), f"Verwalterin: {geheim}", fontsize=11)
        s.insert_text((72, 130), f"Gegenstand: {harmlos}", fontsize=11)
        s.insert_text((72, 160), "Betrag: 50,00 EUR", fontsize=11)
        d.set_metadata({"title": f"Vertrag {geheim}", "author": geheim,
                        "subject": "Test", "keywords": geheim, "creator": "Selbsttest"})
        d.save(quelle)
        d.close()

        # ROT: vorher steckt es drin, in Text UND Metadaten.
        vorher = steckt_noch_drin(quelle, geheim)
        assert not vorher["sauber"], "Selbsttest wertlos -- die Probe enthaelt den Namen nicht"
        assert vorher["streams"] > 0, "Name muesste im Textstream stehen"
        assert vorher["metadaten"], "Name muesste in den Metadaten stehen"

        vor_hash = quelle.read_bytes()
        erg = schwaerze(quelle, ziel, [geheim])
        assert erg["gesamt"] >= 1, f"nichts getroffen: {erg}"

        # GRUEN: nachher nirgends mehr.
        nach = steckt_noch_drin(ziel, geheim)
        assert nach["sauber"], f"Name ueberlebt: {nach}"
        assert nach["klartext"] == 0 and nach["streams"] == 0
        assert not nach["metadaten"] and not nach["xmp"]

        # Das Original ist unangetastet.
        assert quelle.read_bytes() == vor_hash, "die Quelle wurde veraendert"

        # Der Rest bleibt lesbar -- eine Schwaerzung, die alles frisst, ist
        # keine Schwaerzung, sondern eine Loeschung.
        with fitz.open(ziel) as z:
            text = z[0].get_text()
        assert harmlos in text, f"harmloser Text verschwunden: {text!r}"
        assert geheim not in text

        # Und das Layout: gleiche Seitenzahl, gleiche Groesse.
        with fitz.open(quelle) as a, fitz.open(ziel) as b:
            assert a.page_count == b.page_count
            assert tuple(a[0].rect) == tuple(b[0].rect)

        # ─── Der Scan-Fall, und er ist der gefaehrliche ────────────────────
        # Eine Seite, auf der der Name NUR als Bild steht. Alle fuenf
        # Textpruefungen sind hier blind: pdftotext findet nichts, PyMuPDF
        # findet nichts, die Streams enthalten keinen Klartext -- und der
        # Name ist trotzdem lesbar auf dem Papier.
        scan, scan_z = tmp / "scan.pdf", tmp / "scan_geschwaerzt.pdf"
        d = fitz.open()
        s = d.new_page()
        s.insert_text((72, 100), f"Verwalterin: {geheim}", fontsize=14)
        s.insert_text((72, 130), f"Gegenstand: {harmlos}", fontsize=14)
        bild = d[0].get_pixmap(dpi=150)
        d.close()
        # Dieselbe Seite noch einmal, aber NUR als Bild -- so entsteht ein Scan.
        d = fitz.open()
        s = d.new_page(width=bild.width * 72 / 150, height=bild.height * 72 / 150)
        s.insert_image(s.rect, pixmap=bild)
        d.save(scan)
        d.close()

        with fitz.open(scan) as p:
            assert seitenart(p[0]) == "scan_ohne_text", \
                f"Probe ist kein reiner Scan: {seitenart(p[0])}"
            assert not p[0].search_for(geheim), "Textsuche darf hier nichts finden"

        # ROT: Die Textpruefung meldet den Scan NICHT als sauber, obwohl sie
        # nichts findet -- genau darum geht es. Ein "sauber" waere hier eine
        # Falschaussage ueber Namen Dritter.
        vor_scan = steckt_noch_drin(scan, geheim)
        assert vor_scan["text_poppler"] == 0 and vor_scan["streams"] == 0, \
            "der Scan darf keinen Text tragen, sonst prueft dieser Test nichts"
        assert not vor_scan["sauber"], \
            "eine Bildseite darf NIE als sauber gelten -- sie ist nicht pruefbar"
        assert vor_scan["bildseiten_ungeprueft"] == [1]

        # GRUEN: Mit OCR wird die Stelle gefunden und im Bild geschwaerzt.
        erg_scan = schwaerze(scan, scan_z, [geheim])
        assert erg_scan["seitenarten"].get("scan_ohne_text") == 1
        if erg_scan["gesamt"] > 0:
            # Die Stelle muss im BILD dunkel sein -- Text gibt es nicht zu pruefen.
            with fitz.open(scan) as a, fitz.open(scan_z) as b:
                pa, pb = a[0].get_pixmap(dpi=100), b[0].get_pixmap(dpi=100)
                assert pa.samples != pb.samples, "das Bild wurde gar nicht angefasst"
            assert not erg_scan["ungeprueft"], \
                f"Seiten ohne Befund muessen gemeldet werden: {erg_scan['ungeprueft']}"
        else:
            # Kein OCR-Treffer: DANN MUSS ES GEMELDET WERDEN. Stilles
            # Gelingen waere hier der teure Fehler.
            assert erg_scan["ungeprueft"] == [1], \
                "ohne Treffer auf einer Bildseite muss die Seite als ungeprueft gelten"

        # Negativfaelle.
        leer = schwaerze(quelle, tmp / "leer.pdf", ["   "])
        assert leer["gesamt"] == 0, "Leerraum darf nichts schwaerzen"
        fehlt = schwaerze(quelle, tmp / "fehlt.pdf", ["kommt hier nicht vor"])
        assert fehlt["gesamt"] == 0
        # Ein Wortlaut ohne Treffer darf das Dokument nicht veraendern.
        with fitz.open(tmp / "fehlt.pdf") as f:
            assert harmlos in f[0].get_text()

    print("pdf_schwaerzen: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--quelle", type=Path)
    p.add_argument("--ziel", type=Path)
    p.add_argument("--wortlaut", action="append", default=[])
    p.add_argument("--pruefe", type=Path, help="nur nachsehen, ob etwas ueberlebt hat")
    p.add_argument("--behalte-metadaten", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        return _selftest()
    if fitz is None:
        print("PyMuPDF fehlt -- ohne es gibt es keine echte Schwaerzung.", file=sys.stderr)
        return 1

    import json
    if a.pruefe:
        aus = {w: steckt_noch_drin(a.pruefe, w) for w in a.wortlaut}
        print(json.dumps(aus, ensure_ascii=False, indent=2))
        return 0 if all(v["sauber"] for v in aus.values()) else 1
    if not (a.quelle and a.ziel and a.wortlaut):
        p.print_help()
        return 2

    erg = schwaerze(a.quelle, a.ziel, a.wortlaut, not a.behalte_metadaten)
    # Nach dem Schwaerzen IMMER nachpruefen -- eine Schwaerzung ohne
    # Gegenprobe ist eine Behauptung.
    erg["nachpruefung"] = {w: steckt_noch_drin(a.ziel, w) for w in a.wortlaut}
    print(json.dumps(erg, ensure_ascii=False, indent=2))
    return 0 if all(v["sauber"] for v in erg["nachpruefung"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
