#!/usr/bin/env python3
"""LaTeX-Erzeuger fuer den Gestaltungsvorrat (ADR-015).

Liest die KANONISCHE Designvorrat-Datei (gemessen in
runs/messung_i2_designvorrat_2026-08-15T111743.md:
design-lab/begod/knowledge/apps/akademia/aka-design-guide.json -- Pfad-
Uebereinstimmung mit dem Erzeuger, Git-Status, Alter und Vollstaendigkeit
zeigen dorthin) und schreibt LaTeX-Definitionen daraus. Keine Kopie der
Quelldatei wird angelegt -- genau das war der gemessene Fehler (53 Kopien
einer Datei, 36 der anderen, 33 davon veraltet).

Der Pfad ist ein Parameter mit Vorgabewert (KANONISCHER_PFAD), nicht fest
verdrahtet -- ein Test kann gegen eine eigene Datei laufen.

Drei Entscheidungen zur Zuordnung, mit Begruendung:

1. Farben: Quelle liefert bereits Hex (#RRGGBB), keine Farbraum-Umrechnung
   noetig. \\definecolor{...}{HTML}{...} (xcolor) bildet das verlustfrei ab.
   Liegt ein anderes Format vor (rgb(), hsl(), Wort), ist das ein
   UNBEKANNTER FARBRAUM -- wird gemeldet, nie stumm geraten.

2. Einheit fuer Abstaende: Punkt (pt), nicht Millimeter oder em. Begruendung:
   Die Quelle selbst traegt fuer Radius und Typo-Skala bereits PDF-Punktwerte
   (aus einem PyMuPDF-Vektor-Audit gemessen, siehe pdf_masszahlen.*.pt) --
   das ist die Originalgroesse aus dem Druckwerk, nicht aus px zurueckgerechnet.
   pt in der Quelle wird pt in LaTeX, ohne Umrechnungsfehler dazwischen.

3. Schriften: RotisSansSerifPro (typografie.font_family_primary) ist nur
   nutzbar, wenn der Satzrechner sie kennt. Fehlt sie, faellt klassisches
   LaTeX (NFSS-Substitution) OHNE FEHLER auf eine Ersatzschrift zurueck --
   das Blatt sieht weiterhin "fertig" aus und ist es nicht. Darum: Pruefung
   per `fc-list` (Fontconfig), wenn vorhanden; Ergebnis immer als WARNUNG
   ausgegeben (gefunden / fehlt / nicht pruefbar), nie stillschweigend
   uebergangen.

4. Werte ohne LaTeX-Entsprechung (Schatten/Elevation, Uebergaenge, ganze
   Bloecke wie dark_mode, komponenten, kursarten_semantik, ...): werden NICHT
   uebersetzt -- sie werden als UEBERSPRUNGEN gemeldet (Kommentarzeile in der
   erzeugten Datei + Ruecklaufwert), analog zum PDF/UA-Fehlschlag vom
   2026-08-14 (konformes Kennzeichen ohne Struktur = Meldung ohne Deckung).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

KANONISCHER_PFAD = (
    "/Volumes/daten/Begod2026/design-lab/begod/knowledge/apps/akademia/"
    "aka-design-guide.json"
)

HEX_MUSTER = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Diese Top-Level-Schluessel werden uebersetzt. Alles andere im Guide ist
# eine Wissenslueke fuer LaTeX (Farbschema fuer Flutter, SCSS-Overrides,
# Komponenten-Elevation/Schatten, dark_mode, ...) und wird als UEBERSPRUNGEN
# gemeldet -- nie still verschluckt (Auflage 4).
UEBERSETZTE_SCHLUESSEL = {"farben", "typografie", "pdf_masszahlen", "meta"}


def lade_guide(pfad: str) -> dict:
    """Liest+parst Designvorrat. Grenzwerte: Datei fehlt, Datei leer."""
    if not os.path.exists(pfad):
        raise FileNotFoundError(f"Designvorrat nicht gefunden: {pfad}")
    with open(pfad, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        raise ValueError(f"Designvorrat ist leer: {pfad}")
    return json.loads(text)


def _cs_name(prefix: str, schluessel: str) -> str | None:
    """Baut einen gueltigen LaTeX-Steuersequenz-Namen (nur A-Za-z).

    LaTeX-Befehlsnamen vertragen weder Ziffern noch Bindestriche noch
    Unterstriche. Alles, was kein ASCII-Buchstabe ist, wird als Trenner
    behandelt (camelCase). Bleibt nichts uebrig, gibt es None zurueck --
    der Aufrufer muss das als UEBERSPRUNGEN melden, nicht stumm verwerfen.
    """
    teile = [t for t in re.split(r"[^A-Za-z]+", schluessel) if t]
    if not teile:
        return None
    name = teile[0].lower() + "".join(t.capitalize() for t in teile[1:])
    if not name:
        return None
    return prefix + name[0].upper() + name[1:]


def _pruefe_schrift(name: str) -> str:
    """Prueft per fc-list, ob eine Schrift auf diesem Rechner bekannt ist.

    Rueckgabe ist immer eine Warnzeile -- Ergebnis positiv, negativ oder
    "nicht pruefbar" wird immer gemeldet, nie stumm uebergangen (Auflage 3).
    """
    fc_list = shutil.which("fc-list")
    if not fc_list:
        return (
            f"SCHRIFTPRUEFUNG NICHT MOEGLICH: 'fc-list' fehlt auf diesem "
            f"Rechner. Ungeprueft, ob '{name}' installiert ist -- LaTeX "
            f"faellt sonst OHNE FEHLER auf eine Ersatzschrift zurueck."
        )
    try:
        out = subprocess.run(
            [fc_list], capture_output=True, text=True, timeout=10
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        return f"SCHRIFTPRUEFUNG FEHLGESCHLAGEN ({exc}): '{name}' ungeprueft."
    if name.lower() in out.lower():
        return f"Schrift '{name}' ist auf diesem Rechner installiert."
    return (
        f"SCHRIFT FEHLT: '{name}' ist auf diesem Rechner NICHT installiert. "
        f"LaTeX setzt sonst KLAGLOS eine Ersatzschrift -- das Blatt sieht "
        f"fertig aus und ist es nicht. Vor dem Satz installieren oder "
        f"bewusst auf den Fallback umstellen."
    )


def generate_latex(guide: dict) -> tuple[str, list[str]]:
    """Baut LaTeX-Definitionen aus dem Designvorrat.

    Rueckgabe: (latex_text, warnungen). warnungen enthaelt jede uebersprungene
    Stelle und das Schriftpruef-Ergebnis -- wird vom Aufrufer laut gemeldet,
    nie verschluckt.
    """
    warnungen: list[str] = []
    verwendete_namen: set[str] = set()
    zeilen: list[str] = []

    version = guide.get("meta", {}).get("version", "?")
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    zeilen += [
        "% AUTO-GENERIERT von kern/designtokens_latex.py -- NICHT VON HAND BEARBEITEN",
        f"% Quelle: {KANONISCHER_PFAD} v{version}",
        f"% Erzeugt: {jetzt}",
        "\\RequirePackage{xcolor}",
        "",
    ]

    # -- Farben --------------------------------------------------------
    zeilen.append("% -- Farben (Hex direkt aus der Quelle, keine Umrechnung) --")
    for schluessel, wert in guide.get("farben", {}).items():
        hex_val = wert.get("hex", "")
        if not HEX_MUSTER.match(hex_val):
            warnungen.append(
                f"UNBEKANNTER FARBRAUM bei Farbe '{schluessel}': {hex_val!r} "
                f"ist kein #RRGGBB-Hex -- uebersprungen."
            )
            continue
        name = _cs_name("aka", schluessel)
        if name is None:
            warnungen.append(
                f"UEBERSPRUNGEN: Farbe '{schluessel}' ergibt nach Bereinigung "
                f"keinen gueltigen LaTeX-Namen (Sonderzeichen)."
            )
            continue
        if name in verwendete_namen:
            warnungen.append(
                f"UEBERSPRUNGEN: Farbe '{schluessel}' kollidiert nach "
                f"Namensbereinigung mit einer bereits vergebenen Definition "
                f"({name}) -- wird nicht ueberschrieben."
            )
            continue
        verwendete_namen.add(name)
        zeilen.append(f"\\definecolor{{{name}}}{{HTML}}{{{hex_val.lstrip('#').upper()}}}")
    zeilen.append("")

    # -- Laengen: Border-Radius (pt, siehe Modul-Docstring Punkt 2) ----
    radius_sys = guide.get("pdf_masszahlen", {}).get("border_radius_system", {})
    if radius_sys:
        zeilen.append("% -- Eckenradien in pt (Original-Druckmass aus der Quelle) --")
        for schluessel, eintrag in radius_sys.items():
            if not isinstance(eintrag, dict) or "pt" not in eintrag:
                continue
            name = _cs_name("akaRadius", schluessel)
            if name is None or name in verwendete_namen:
                warnungen.append(
                    f"UEBERSPRUNGEN: Radius-Eintrag '{schluessel}' ohne "
                    f"gueltigen/eindeutigen LaTeX-Namen."
                )
                continue
            verwendete_namen.add(name)
            zeilen.append(f"\\def\\{name}{{{eintrag['pt']}pt}}")
        zeilen.append("")

    # -- Laengen: Typografie-Skala (pt, Druckgroesse) ------------------
    typo_skala = guide.get("pdf_masszahlen", {}).get("print_typo_skala", [])
    if typo_skala:
        zeilen.append("% -- Schriftgroessen in pt (Druckgroesse, aus PDF gemessen) --")
        for eintrag in typo_skala:
            rolle = eintrag.get("rolle", "")
            pt = eintrag.get("pt")
            if pt is None:
                continue
            name = _cs_name("akaFontSize", rolle)
            if name is None:
                warnungen.append(
                    f"UEBERSPRUNGEN: Typo-Skala-Rolle {rolle!r} ergibt keinen "
                    f"gueltigen LaTeX-Namen (Sonderzeichen)."
                )
                continue
            if name in verwendete_namen:
                warnungen.append(
                    f"UEBERSPRUNGEN: Typo-Skala-Rolle {rolle!r} kollidiert "
                    f"nach Bereinigung mit {name}."
                )
                continue
            verwendete_namen.add(name)
            zeilen.append(f"\\def\\{name}{{{pt}pt}}")
        zeilen.append("")

    # -- Schrift-Pruefung (Auflage 3) -----------------------------------
    typo = guide.get("typografie", {})
    primaer = typo.get("font_family_primary")
    fallback = typo.get("font_family_digital_fallback")
    if primaer:
        pruef_zeile = _pruefe_schrift(primaer)
        warnungen.append(pruef_zeile)
        zeilen.append(f"% SCHRIFTPRUEFUNG: {pruef_zeile}")
        zeilen.append(f"\\def\\akaFontPrimary{{{primaer}}}")
    if fallback:
        zeilen.append(f"\\def\\akaFontFallback{{{fallback}}}")
    zeilen.append("")

    # -- Uebersprungene Bloecke (Auflage 4) -----------------------------
    uebersprungen = [k for k in guide.keys() if k not in UEBERSETZTE_SCHLUESSEL]
    if uebersprungen:
        zeilen.append(
            "% -- UEBERSPRUNGEN (keine LaTeX-Entsprechung, siehe ADR-015) --"
        )
        for k in uebersprungen:
            zeilen.append(f"% {k}: keine Entsprechung, nicht uebersetzt")
            warnungen.append(
                f"UEBERSPRUNGEN (keine LaTeX-Entsprechung): '{k}' "
                f"(z.B. Schatten/Elevation, Uebergaenge, plattformspezifische "
                f"Bloecke) -- nicht uebersetzt, absichtlich ausgewiesen."
            )
        zeilen.append("")

    return "\n".join(zeilen) + "\n", warnungen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pfad", default=KANONISCHER_PFAD, help="Designvorrat-Datei")
    p.add_argument("--out", default=None, help="Zieldatei (sonst stdout)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()

    try:
        guide = lade_guide(args.pfad)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1

    latex, warnungen = generate_latex(guide)
    for w in warnungen:
        print(f"WARNUNG: {w}", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(latex)
        print(f"geschrieben: {args.out}")
    else:
        print(latex)
    return 0


def _selftest() -> int:
    tmp_dir = "/tmp"  # ponytail: nur fuer Selbsttest-Dateien, kein Produktionscode
    ok_guide = {
        "meta": {"version": "9.9.9"},
        "farben": {
            "primary": {"hex": "#00993E"},
            "kaputt_rgb": {"hex": "rgb(0,0,0)"},  # unbekannter Farbraum
            "!!!": {"hex": "#000000"},  # Sonderzeichen-Name
        },
        "typografie": {
            "font_family_primary": "GarantiertNichtInstallierteTestschriftXYZ",
            "font_family_digital_fallback": "Arial",
        },
        "pdf_masszahlen": {
            "border_radius_system": {
                "xl": {"pt": 25, "px": 33},
            },
            "print_typo_skala": [
                {"pt": 9.0, "rolle": "Fließtext (body)"},
            ],
        },
        "komponenten": {"kurs_card": {"elevation": 1}},  # ohne Entsprechung
        "dark_mode": {"foo": "bar"},  # ohne Entsprechung
    }

    latex, warnungen = generate_latex(ok_guide)

    assert "\\definecolor{akaPrimary}{HTML}{00993E}" in latex, latex
    assert any("UNBEKANNTER FARBRAUM" in w and "kaputt_rgb" in w for w in warnungen), warnungen
    assert any("Sonderzeichen" in w for w in warnungen), warnungen
    assert "\\def\\akaRadiusXl{25pt}" in latex
    assert any(w.startswith("\\def\\akaFontSize") for w in [l for l in latex.splitlines()]) or \
        "\\def\\akaFontSizeFlietextBody{9.0pt}" in latex, latex
    assert any("SCHRIFT FEHLT" in w and "GarantiertNichtInstallierteTestschriftXYZ" in w for w in warnungen), warnungen
    assert any("komponenten" in w and "UEBERSPRUNGEN" in w for w in warnungen), warnungen
    assert any("dark_mode" in w and "UEBERSPRUNGEN" in w for w in warnungen), warnungen

    # Grenzwerte: Datei fehlt
    fehlend = os.path.join(tmp_dir, "designtokens_latex_selftest_fehlt_nicht.json")
    if os.path.exists(fehlend):
        os.remove(fehlend)
    try:
        lade_guide(fehlend)
        raise AssertionError("FileNotFoundError erwartet")
    except FileNotFoundError:
        pass

    # Grenzwerte: Datei leer
    leer = os.path.join(tmp_dir, "designtokens_latex_selftest_leer.json")
    with open(leer, "w", encoding="utf-8") as f:
        f.write("")
    try:
        lade_guide(leer)
        raise AssertionError("ValueError erwartet")
    except ValueError:
        pass
    finally:
        os.remove(leer)

    # Grenzwert: Farbe ohne jeglichen Hex-Schluessel
    latex2, warnungen2 = generate_latex({"farben": {"x": {}}, "meta": {}})
    assert any("UNBEKANNTER FARBRAUM" in w for w in warnungen2), warnungen2

    print("designtokens_latex: Selbsttest bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
