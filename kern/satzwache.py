#!/usr/bin/env python3
"""Die Ableitungswache: prueft das gesetzte Blatt GEGEN die Baustein-Quelle
(`kern/dokument.py`), NIE ein Blatt gegen ein anderes -- ein gemeinsam
verlorener Baustein waere in einem Paarvergleich unsichtbar, weil beide
Seiten gleich falsch waeren.

DREI EIGENSCHAFTEN, getrennt geprueft und getrennt gemeldet (kein throw --
`Bericht` traegt die Funde, `bestanden()` fasst sie nur zusammen):

  VOLLSTAENDIGKEIT -- jede Kennung aus `dokument.bausteine()` erscheint als
  `\\label{bau:<kennung>}` in der LaTeX-Quelle (`satz.satz_quelle`). Das ist
  die Stufe VOR dem Satzlauf: faellt ein Baustein hier schon heraus, hat er
  auch im PDF keine Spur mehr, an der ihn eine spaetere Pruefung wiederfaende.

  TREUE -- der Baustein-Text erscheint (normalisiert) im per `pdftotext`
  gelesenen Text des GERENDERTEN PDF. GRENZE DES VERGLEICHS: Leerraum wird zu
  einem einzelnen Leerzeichen zusammengefasst (`_normalisiere`), weil
  pdftotext Zeilen anders umbricht als die LaTeX-Quelle -- ein
  Zeichen-fuer-Zeichen-Vergleich waere blind fuer jeden erlaubten Umbruch und
  meldete staendig Falschalarm. Der verbleibende Test ist ein Teilstring-Test
  auf dem normalisierten Text. Das erkennt zuverlaessig, wenn ein Baustein
  GANZ fehlt oder sein Text durch anderen Text ERSETZT wurde (der Auftragsfall).
  Es erkennt NICHT jede denkbare Verstuemmelung: ein Text, der zufaellig als
  Teilstring irgendwo anders im Blatt vorkommt (z. B. eine kurze, generische
  Phrase, die auch im Vorspann steht), wuerde als "gefunden" durchgehen, obwohl
  sie nicht an der erwarteten Stelle steht. Fuer laengere, bausteintypische
  Texte ist das vernachlaessigbar; fuer sehr kurze Feldwerte (einzelne Ziffern,
  ein Wort) ist der Test schwaecher und sollte nicht als einzige Treue-Pruefung
  gelten.

  KONFORMITAET -- `verapdf -f ua1` und `verapdf -f 3u` auf dem erzeugten PDF,
  je PASS/FAIL. Das ist eine LAUFENDE Pruefung, keine einmalige: die
  Eigenschaft war fuer den Vorspann aus `spikes/pdf_a3_erechnung/rechnung.tex`
  belegt (siehe `kern/satz.py`), verfaellt aber stillschweigend, sobald jemand
  den Vorspann aendert -- darum hier bei jedem Lauf neu gemessen.

  NICHT GEPRUEFT: VERANKERUNG (zeigt jede Stelle im Blatt auf den richtigen
  Baustein, nicht nur auf die richtige Seite). Es gibt noch keine Anker
  (`kern/baustein.py` Anker zeigt auf Bausteine, nicht das Label auf
  Zeichenpositionen im PDF) -- diese Wache prueft nur die drei Eigenschaften
  oben. Ein "bestanden" hier ist KEIN Beleg fuer Verankerung.

Fehlt lualatex, pdftotext oder verapdf, meldet die Wache "nicht geprueft:
<grund>" -- nie stillschweigend "bestanden". Nur stdlib; Aussenwerkzeuge
ausschliesslich ueber subprocess.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dokument import bausteine  # noqa: E402
from satz import satz_quelle  # noqa: E402

PROFILE = ("ua1", "3u")


@dataclass
class Bericht:
    vollstaendigkeit_fehlt: list[str] = field(default_factory=list)
    treue_geprueft: bool = False
    treue_grund: str = ""
    treue_abweichungen: list[str] = field(default_factory=list)
    konformitaet: dict[str, str] = field(default_factory=dict)

    def bestanden(self) -> bool:
        if self.vollstaendigkeit_fehlt or self.treue_abweichungen:
            return False
        return bool(self.konformitaet) and all(v == "PASS" for v in self.konformitaet.values())


_LEERRAUM = re.compile(r"\s+")


def _normalisiere(text: str) -> str:
    """Leerraum zusammenfassen -- Grenze des Vergleichs steht im Modulkopf."""
    return _LEERRAUM.sub(" ", text).strip()


def pruefe_vollstaendigkeit(doc, quelle: str) -> list[str]:
    """Kennungen aus dem Dokument, deren Label in der Quelle fehlt."""
    return [b.kennung for b in bausteine(doc) if f"bau:{b.kennung}" not in quelle]


def pruefe_treue(doc, pdf_text: str) -> list[str]:
    """Kennungen, deren Baustein-Text nicht als normalisierter Teilstring im
    PDF-Text auftaucht. Leere Bausteintexte (z. B. Grafik-Platzhalter) werden
    uebersprungen -- ein leerer Text ist trivial "enthalten" und keine Aussage."""
    norm_pdf = _normalisiere(pdf_text)
    abweichend = []
    for b in bausteine(doc):
        erwartet = _normalisiere(b.text)
        if erwartet and erwartet not in norm_pdf:
            abweichend.append(b.kennung)
    return abweichend


def pruefe_konformitaet(pdf_pfad: Path, profile=PROFILE) -> dict[str, str]:
    verapdf = shutil.which("verapdf")
    ergebnis: dict[str, str] = {}
    for profil in profile:
        if not verapdf:
            ergebnis[profil] = "nicht geprueft: verapdf fehlt"
            continue
        lauf = subprocess.run(
            [verapdf, "-f", profil, "--format", "text", str(pdf_pfad)],
            capture_output=True, text=True, timeout=120,
        )
        ausgabe = lauf.stdout + lauf.stderr
        if "PASS" in ausgabe:
            ergebnis[profil] = "PASS"
        elif "FAIL" in ausgabe:
            ergebnis[profil] = "FAIL"
        else:
            ergebnis[profil] = f"nicht geprueft: unerwartete verapdf-Ausgabe (returncode={lauf.returncode})"
    return ergebnis


def satz_lauf(arbeitsverzeichnis: Path, quelle: str) -> tuple[Path | None, str]:
    """Setzt eine LaTeX-Quelle. Gibt (PDF-Pfad, '') oder (None, Grund) zurueck."""
    lualatex = shutil.which("lualatex") or "/usr/local/bin/lualatex"
    if not shutil.which("lualatex") and not Path(lualatex).exists():
        return None, "lualatex fehlt"
    tex = arbeitsverzeichnis / "blatt.tex"
    tex.write_text(quelle, encoding="utf-8")
    lauf = subprocess.run(
        [lualatex, "-interaction=nonstopmode", "-output-directory", str(arbeitsverzeichnis), str(tex)],
        capture_output=True, text=True, timeout=60,
    )
    pdf = arbeitsverzeichnis / "blatt.pdf"
    if lauf.returncode != 0 or not pdf.exists():
        return None, f"lualatex scheiterte (returncode={lauf.returncode})"
    return pdf, ""


def pdf_text(pdf_pfad: Path) -> tuple[str, str]:
    """(Text, '') oder ('', 'nicht geprueft: <grund>')."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return "", "nicht geprueft: pdftotext fehlt"
    lauf = subprocess.run([pdftotext, str(pdf_pfad), "-"], capture_output=True, text=True, timeout=30)
    return lauf.stdout, ""


def pruefe(doc, titel: str = "Pruefblatt", arbeitsverzeichnis: Path | None = None) -> Bericht:
    """Volle Wache: Vollstaendigkeit (immer moeglich, braucht kein Werkzeug),
    Treue und Konformitaet (beide nur, wenn ein Blatt gesetzt werden konnte)."""
    quelle = satz_quelle(doc, titel)
    bericht = Bericht(vollstaendigkeit_fehlt=pruefe_vollstaendigkeit(doc, quelle))

    eigenes_tmp = arbeitsverzeichnis is None
    verzeichnis = Path(tempfile.mkdtemp()) if eigenes_tmp else arbeitsverzeichnis
    try:
        pdf, grund = satz_lauf(verzeichnis, quelle)
        if pdf is None:
            bericht.treue_grund = f"nicht geprueft: {grund}"
            bericht.konformitaet = {p: f"nicht geprueft: {grund}" for p in PROFILE}
            return bericht

        text, textgrund = pdf_text(pdf)
        if textgrund:
            bericht.treue_grund = textgrund
        else:
            bericht.treue_geprueft = True
            bericht.treue_abweichungen = pruefe_treue(doc, text)

        bericht.konformitaet = pruefe_konformitaet(pdf)
        return bericht
    finally:
        if eigenes_tmp:
            shutil.rmtree(verzeichnis, ignore_errors=True)
