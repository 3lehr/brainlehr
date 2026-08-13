#!/usr/bin/env python3
"""fundstelle.py -- beantwortet "wo genau steht das", oder sagt, dass es das nicht weiss.

ANLASS (Betreiber, 2026-08-13): Fuer ein Arbeitstreffen mit zwei bis drei
Menschen am buckeberg-Projekt braucht die App eine Sache -- "zeig mir, wo das
steht". Das Dokument aufgeschlagen an der richtigen Stelle, markiert.

DER BEFUND, DER DIESES MODUL BEGRUENDET, gemessen am 2026-08-13:
`dossier/quellen.json` fuehrt 49 Quellen. **13** davon tragen `seite` UND
`suchtext`. Fuer 36 weiss heute niemand, welche Zeile gemeint ist. Ein Viewer
allein loest also ein Viertel des Problems.

DIE FEHLKLASSE, gegen die hier gebaut wird -- und sie entsteht ohne Vorsatz:
Wer bei Nichtfund die erste Seite zurueckgibt, hat aus "ich weiss es nicht" ein
"hier steht es" gemacht. Eine falsch gesetzte Markierung ist schlimmer als
keine, weil sie aussieht wie ein Beleg. Darum gibt es hier den Rueckgabewert
`belegt=False` mit Grund, und er ist kein Fehlerfall, sondern eine Antwort.

PREIS EINES FEHLALARMS: gering -- ein Dokument oeffnet unmarkiert, der Mensch
sucht selbst. Der umgekehrte Fehler ist der teure.

DREI QUELLEN, in dieser Rangfolge:
  1. gepflegt   -- dossier/quellen.json, von Hand geprueft (quellen_check.py)
  2. gerechnet  -- Volltextsuche in den .txt-Beidateien; die Seite kommt aus
                   den "--- Seite N ---"-Marken, die die Extraktion gesetzt hat
  3. keine      -- belegt=False mit Grund. NICHT raten.

WAS HIER BEWUSST NICHT PASSIERT: keine Texterkennung. Gemessen am 2026-08-13
tragen 29 von 29 PDFs unter homepage/public/quellen/ eine Textschicht -- es
gibt nichts zu erkennen. Und keine Seitenberechnung fuer PDFs ohne Beidatei:
das kann PDFKit in der App besser und nativ (findString -> PDFSelection.pages).
Dieses Modul liefert dann Datei + Suchtext, die Seite loest die Anzeige auf.

buckeberg wird ausschliesslich GELESEN. Der Ort ist ueber
BRAINLEHR_QUELLENKORPUS uebersteuerbar, nicht verdrahtet.

Aufruf:
    python3 kern/fundstelle.py --quelle 14
    python3 kern/fundstelle.py --text "Grundverguetung 50,00"
    python3 kern/fundstelle.py --bestand
    python3 kern/fundstelle.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ENV_KORPUS = "BRAINLEHR_QUELLENKORPUS"
STANDARD_KORPUS = "/Volumes/daten/Begod2026/buckeberg"

# Die Extraktion (phoenix-recovery-engine, 2026-07-22) setzt diese Marke vor
# jede Seite. Sie ist der einzige Grund, warum eine Seitenzahl rechenbar ist.
SEITENMARKE = re.compile(r"^--- Seite (\d+) ---$", re.MULTILINE)

# Verzeichnisse mit Volltext-Beidateien, in Reihenfolge der Verlaesslichkeit.
VOLLTEXT_ORTE = ("dokumente", "homepage/public/quellen")

# Ab wie vielen Dokumenten ein Wortlaut als Vordruck gilt statt als Beleg.
# Gemessen im Bestand: 29,6 % aller Textzeilen stehen in mehr als einem
# Dokument, 7,7 % in mehr als fuenf. Bei mehr als fuenf ist die Trefferliste
# keine Antwort mehr, sondern eine Suchanfrage -- und die erste davon als
# "die Fundstelle" auszugeben, ist geraten.
BRIEFKOPF_AB_DOKUMENTEN = 5

# Was die Anzeige auseinanderhalten muss. Alles andere ist "unbekannt" und
# geht an Quick Look -- das kann mehr Formate, als wir hier auflisten wollen.
FORMATE = {".pdf": "pdf", ".html": "html", ".htm": "html", ".txt": "text",
           ".md": "text", ".jpg": "bild", ".jpeg": "bild", ".png": "bild"}


@dataclass
class Fundstelle:
    """Eine Antwort auf "wo steht das" -- auch dann, wenn sie "weiss ich nicht" lautet."""

    belegt: bool
    herkunft: str          # gepflegt | gerechnet | keine
    grund: str = ""        # Klartext in Nutzersprache; auch bei belegt=True moeglich
    datei: str = ""        # Pfad relativ zur Korpuswurzel
    absolut: str = ""
    format: str = "unbekannt"
    seite: int | None = None
    seiten: list[int] = field(default_factory=list)  # ALLE Fundstellen, nicht nur die erste
    suchtext: str = ""
    kurz: str = ""         # Klartextbeschreibung der Quelle, falls vorhanden
    weitere: list[dict] = field(default_factory=list)  # weitere Treffer, ungewichtet

    @property
    def mehrdeutig(self) -> bool:
        """Steht der Wortlaut auf mehr als einer Seite?

        Die App MUSS das wissen: PDFKit findString markiert sonst den ersten
        Treffer, und der ist bei 8 der 14 gepflegten Suchtexte eine blosse Zahl
        ("50,00", "35,00", "75,00"). Bei Quelle 4 steht "75,00" auf den Seiten
        4, 5, 6 und 8 -- gepflegt ist 8, markiert wuerde 4.
        """
        return len(self.seiten) > 1

    @property
    def markierbar(self) -> bool:
        """Aufschlagen und Markieren sind ZWEI Aussagen, und sie fallen auseinander.

        Quelle 1 des heutigen Bestands ist der Beleg: Seite 4 ist gepflegt, ein
        Suchtext nicht. Das Dokument laesst sich also richtig aufschlagen, aber
        nichts darf hervorgehoben werden -- eine Markierung waere hier geraten.
        """
        return bool(self.suchtext)

    def als_dict(self) -> dict:
        d = asdict(self)
        d["markierbar"] = self.markierbar
        d["mehrdeutig"] = self.mehrdeutig
        return d


# ─── reine Funktionen (ohne Dateisystem, darum ohne Aufbau testbar) ────────

def seite_aus_volltext(volltext: str, suchtext: str) -> int | None:
    """Seitenzahl der ERSTEN Fundstelle von `suchtext`, oder None.

    Zaehlt nicht die Marken, sondern nimmt die LETZTE Marke vor dem Treffer --
    ein Volltext kann bei 1 oder bei 0 beginnen, und ein Auszug kann mitten
    im Dokument anfangen. Wer Marken zaehlt, verschiebt sich in beiden Faellen.

    ACHTUNG beim Aufrufen: "erste Fundstelle" ist nur dann "die Fundstelle",
    wenn es genau eine gibt. Fuer alles Weitere seiten_aus_volltext() nehmen.
    """
    s = seiten_aus_volltext(volltext, suchtext)
    return s[0] if s else None


def seiten_aus_volltext(volltext: str, suchtext: str) -> list[int]:
    """ALLE Seiten, auf denen `suchtext` steht -- aufsteigend, ohne Dubletten.

    DER GRUND, WARUM ES DIESE FUNKTION GIBT (Konsil 2026-08-13): Die Suche nach
    der ersten Fundstelle liefert bei einer Kopf- oder Fusszeile immer Seite 1.
    Gemessen im Bestand: "Fax: 07231 58993150" steht auf 11 von 11 Seiten der
    Jahresabrechnung 2024, und das Modul meldete belegt=True, Seite 1 -- genau
    die Fehlerklasse, gegen die es gebaut wurde, nur eine Ebene tiefer.
    116 von 367 Dokumenten tragen eine solche Zeile.

    Wer wissen will, OB eine Stelle eindeutig ist, muss alle zaehlen. Die eine
    Zahl kann das nicht sagen, und ihr Schweigen sieht aus wie Gewissheit.
    """
    if not suchtext:
        return []
    h, n = _glaetten(volltext), _glaetten(suchtext)
    if not n:
        return []

    # Marken auf der GEGLAETTETEN Zeichenkette suchen, damit die Positionen
    # zueinander passen -- _finde glaettet ebenfalls.
    marken = [(m.start(), int(m.group(1)))
              for m in re.finditer(r"--- seite (\d+) ---", h)]

    treffer: list[int] = []
    pos = h.find(n)
    while pos >= 0:
        seite = None
        for start, nr in marken:
            if start > pos:
                break
            seite = nr
        if seite is not None and seite not in treffer:
            treffer.append(seite)
        pos = h.find(n, pos + 1)
    return sorted(treffer)


def ist_laufender_kopf(seiten: list[int], seiten_gesamt: int) -> bool:
    """Steht der Text auf so vielen Seiten, dass er das Dokument nicht mehr eingrenzt?

    Schwelle: mindestens 3 Seiten UND mindestens 60 % des Dokuments. Beides
    zusammen, weil je eine allein danebenliegt -- 2 von 2 Seiten ist keine
    Kopfzeile, und 3 von 40 ist eine echte Mehrfachnennung.
    """
    if seiten_gesamt <= 0 or len(seiten) < 3:
        return False
    return len(seiten) / seiten_gesamt >= 0.6


def _finde(heuhaufen: str, nadel: str) -> int:
    """Suche ohne Ruecksicht auf Gross-/Kleinschreibung und Mehrfach-Leerraum.

    Der Zeilenumbruch mitten im Wort ist der Normalfall in PDF-Auszuegen --
    eine wortgetreue Suche findet "Grundverguetung 50,00" darum fast nie.
    """
    h = _glaetten(heuhaufen)
    n = _glaetten(nadel)
    if not n:
        return -1
    return h.find(n)


def _glaetten(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def _seitenzahl(volltext: str) -> int:
    """Hoechste Seitenmarke -- der Nenner fuer die Kopfzeilen-Erkennung."""
    nummern = [int(m.group(1)) for m in SEITENMARKE.finditer(volltext)]
    return max(nummern) if nummern else 0


def format_von(datei: str) -> str:
    return FORMATE.get(Path(datei).suffix.casefold(), "unbekannt")


# ─── Korpuszugriff ────────────────────────────────────────────────────────

def korpus_wurzel(pfad: str | os.PathLike | None = None) -> Path:
    return Path(pfad or os.environ.get(ENV_KORPUS) or STANDARD_KORPUS)


def _quellenverzeichnis(wurzel: Path) -> dict:
    """dossier/quellen.json, nur die echten Quellen.

    Die Verwaltungszeilen tragen einen fuehrenden Unterstrich (_hinweis, _rang,
    _stand) und werden ueber die SCHLUESSELFORM ausgeschlossen -- nicht ueber
    den Werttyp. Ein Filter auf isinstance(v, dict) sieht richtig aus und ist
    falsch: _rang IST ein Objekt und wurde dadurch als 49. Quelle mitgezaehlt.
    Gemessen und korrigiert am 2026-08-13; richtig sind 48 (Schluessel 1-48,
    lueckenlos). Dieselbe Fehlerklasse wie L-16e428 -- nach der Form gefiltert
    statt nach der Bedeutung.
    """
    p = wurzel / "dossier" / "quellen.json"
    if not p.is_file():
        return {}
    roh = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in roh.items() if k.isdigit() and isinstance(v, dict)}


def _dateiort(wurzel: Path, datei: str) -> Path | None:
    """Wo eine in quellen.json genannte Datei tatsaechlich liegt."""
    for ort in ("homepage/public/quellen", "dokumente", "dossier", "pdf"):
        p = wurzel / ort / datei
        if p.is_file():
            return p
    return None


def volltext_dateien(wurzel: Path) -> list[Path]:
    """Alle .txt-Beidateien des Korpus. Sortiert, damit Treffer reproduzierbar sind."""
    treffer: list[Path] = []
    for ort in VOLLTEXT_ORTE:
        basis = wurzel / ort
        if basis.is_dir():
            treffer.extend(sorted(basis.rglob("*.txt")))
    return treffer


# ─── die eigentliche Aufloesung ───────────────────────────────────────────

def loese_quelle(nummer: str, wurzel: Path | None = None) -> Fundstelle:
    """Rang 1: die von Hand gepflegte Fundstelle aus dossier/quellen.json."""
    w = korpus_wurzel(wurzel)
    eintraege = _quellenverzeichnis(w)
    e = eintraege.get(str(nummer))
    if e is None:
        return Fundstelle(False, "keine", grund=f"Quelle {nummer} ist nicht verzeichnet.")

    kurz = e.get("kurz", "")
    datei = e.get("datei", "")
    if not datei:
        return Fundstelle(False, "keine", grund="Zu dieser Quelle ist keine Kopie hinterlegt.",
                          kurz=kurz)
    ort = _dateiort(w, datei)
    if ort is None:
        return Fundstelle(False, "keine", grund="Die hinterlegte Kopie ist nicht auffindbar.",
                          datei=datei, kurz=kurz, format=format_von(datei))

    seite, suchtext = e.get("seite"), e.get("suchtext", "")
    if not suchtext:
        # Der haeufigste Fall (36 von 49) -- und er zerfaellt in zwei, die nicht
        # zusammengeworfen werden duerfen: mit gepflegter Seite laesst sich das
        # Dokument richtig aufschlagen (belegt, aber nicht markierbar); ohne
        # Seite ist nur bekannt, DASS es das Dokument gibt.
        if seite:
            return Fundstelle(True, "gepflegt",
                              grund="Seite bekannt, die Stelle auf der Seite ist nicht erfasst.",
                              datei=str(ort.relative_to(w)), absolut=str(ort),
                              format=format_von(datei), seite=seite, kurz=kurz)
        return Fundstelle(False, "keine",
                          grund="Das Dokument ist hinterlegt, die genaue Stelle ist nicht erfasst.",
                          datei=str(ort.relative_to(w)), absolut=str(ort),
                          format=format_von(datei), kurz=kurz)

    return Fundstelle(True, "gepflegt", datei=str(ort.relative_to(w)), absolut=str(ort),
                      format=format_von(datei), seite=seite, suchtext=suchtext, kurz=kurz)


def loese_text(text: str, wurzel: Path | None = None, grenze: int = 5) -> Fundstelle:
    """Rang 2: den Wortlaut im Korpus suchen und die Seite ausrechnen."""
    w = korpus_wurzel(wurzel)
    if len(_glaetten(text)) < 8:
        # Zu kurz, um zu treffen statt zu raten. Drei Zeichen finden ueberall
        # etwas -- und "ueberall" ist dasselbe wie "nirgends".
        return Fundstelle(False, "keine",
                          grund="Der gesuchte Wortlaut ist zu kurz fuer eine belastbare Stelle.")

    # Vollstaendig durchzaehlen statt nach `grenze` abzubrechen. Gemessen kostet
    # der Volllauf ueber 367 Dateien 92 ms -- und der Abbruch war teuer erkauft:
    # er verschwieg bis zu 48 weitere Vorkommen, ohne das kenntlich zu machen,
    # und konnte einen Briefkopf nicht von einer Fundstelle unterscheiden.
    # `grenze` begrenzt jetzt nur noch, wie viele Treffer BERICHTET werden.
    treffer: list[Fundstelle] = []
    uebersprungen: list[str] = []   # als laufender Kopf verworfen
    for txt in volltext_dateien(w):
        try:
            inhalt = txt.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        seiten = seiten_aus_volltext(inhalt, text)
        if not seiten and _finde(inhalt, text) < 0:
            continue
        # Die Anzeige will das Original, nicht den Auszug: neben X.txt liegt X.pdf.
        anzeige = next((txt.with_suffix(s) for s in (".pdf", ".html", ".jpg", ".png")
                        if txt.with_suffix(s).is_file()), txt)
        gesamt = _seitenzahl(inhalt)
        if ist_laufender_kopf(seiten, gesamt):
            # Eine Kopf- oder Fusszeile grenzt nichts ein. Sie als Fundstelle
            # zu melden waere schlimmer als Schweigen -- sie sieht aus wie ein
            # Beleg und zeigt auf Seite 1, weil dort der erste Treffer liegt.
            uebersprungen.append(str(anzeige.relative_to(w)))
            continue
        treffer.append(Fundstelle(
            True, "gerechnet",
            datei=str(anzeige.relative_to(w)), absolut=str(anzeige),
            format=format_von(anzeige.name),
            seite=seiten[0] if seiten else None, seiten=seiten, suchtext=text,
            kurz=anzeige.stem,
        ))

    if not treffer:
        if uebersprungen:
            return Fundstelle(
                False, "keine",
                grund="Dieser Wortlaut steht auf fast jeder Seite und grenzt die Stelle nicht ein.",
                suchtext=text, weitere=[{"datei": d} for d in uebersprungen[:grenze]])
        return Fundstelle(False, "keine",
                          grund="Dieser Wortlaut steht in keinem hinterlegten Dokument.",
                          suchtext=text)

    # Briefkopf-Regel, die zweite Haelfte der Kopfzeilen-Frage: ein Wortlaut in
    # sehr vielen Dokumenten ist Vordruck, nicht Beleg. Gemessen steht
    # "Fax: 07231 58993150" in Dutzenden Abrechnungen desselben Verwalters --
    # je Dokument auf zu wenigen Seiten fuer ist_laufender_kopf(), quer ueber
    # den Bestand aber vollkommen nichtssagend. Ohne diese Regel meldete das
    # Modul die Faxnummer als Fundstelle mit Seite 1.
    # Die als laufender Kopf VERWORFENEN zaehlen mit. Sonst rettet sich ein
    # Briefkopf ausgerechnet dadurch, dass er in den meisten Dokumenten zu
    # eindeutig ein Briefkopf war: die fielen vorher raus, und die restlichen
    # vier sahen aus wie eine schmale, saubere Trefferliste. Genau so ist die
    # Faxnummer beim ersten Anlauf durchgerutscht.
    dokumente = len(treffer) + len(uebersprungen)
    if dokumente > BRIEFKOPF_AB_DOKUMENTEN:
        return Fundstelle(
            False, "keine",
            grund=(f"Dieser Wortlaut steht in {dokumente} Dokumenten und "
                   f"grenzt die Stelle nicht ein."),
            suchtext=text, weitere=[{"datei": t.datei} for t in treffer[:grenze]])

    erste = treffer[0]
    # `grenze` schneidet nur den BERICHT, nicht mehr die Suche -- und wo sie
    # schneidet, steht es da. Vorher fielen bis zu 48 Vorkommen still weg.
    erste.weitere = [t.als_dict() for t in treffer[1:grenze]]
    if len(treffer) > grenze:
        erste.grund = (f"In {len(treffer)} Dokumenten gefunden, hier die ersten "
                       f"{grenze} -- die Stelle ist nicht eindeutig.")
    return erste


def loese(quelle: str = "", text: str = "", wurzel: Path | None = None) -> Fundstelle:
    """Die eine Tuer: erst die gepflegte Angabe, dann der Wortlaut, dann Schweigen."""
    if quelle:
        f = loese_quelle(quelle, wurzel)
        if f.markierbar:
            return f
        # Die gepflegte Angabe kennt das Dokument, aber nicht die Stelle --
        # dann darf der Wortlaut nachhelfen, ohne die Datei zu wechseln.
        if text and f.absolut:
            beidatei = Path(f.absolut).with_suffix(".txt")
            if beidatei.is_file():
                seite = seite_aus_volltext(
                    beidatei.read_text(encoding="utf-8", errors="replace"), text)
                if seite is not None:
                    f.belegt, f.herkunft, f.seite, f.suchtext, f.grund = (
                        True, "gerechnet", seite, text, "")
        return f
    if text:
        return loese_text(text, wurzel)
    return Fundstelle(False, "keine", grund="Weder eine Quellennummer noch ein Wortlaut angegeben.")


def bestand(wurzel: Path | None = None) -> dict:
    """Der Nenner, ohne den keine Aussage ueber Abdeckung zulaessig ist."""
    w = korpus_wurzel(wurzel)
    e = _quellenverzeichnis(w)
    # Eingeteilt nach dem, was die ANZEIGE damit tun kann -- nicht nach den
    # gefuellten Feldern. Quelle 48 traegt einen Suchtext ohne Seite: die Seite
    # findet PDFKit selbst, markierbar ist sie trotzdem. Wer nach "seite UND
    # suchtext" zaehlt, zaehlt sie faelschlich zu den unbelegten (erst so
    # gezaehlt, vom Gegenprobe-Test am 2026-08-13 widerlegt).
    mit_stelle = [k for k, v in e.items() if v.get("suchtext")]
    nur_seite = [k for k, v in e.items() if v.get("seite") and not v.get("suchtext")]
    formate: dict[str, int] = {}
    for v in e.values():
        formate[format_von(v.get("datei", ""))] = formate.get(format_von(v.get("datei", "")), 0) + 1

    # Format GEGEN Fundstellenqualitaet -- die Randsummen allein verstecken den
    # Befund, der den Zuschnitt entscheidet: gemessen 2026-08-13 ist jede
    # markierbare Quelle ein PDF, und keine der 20 HTML-Quellen traegt eine
    # Stelle. Fuer HTML ist die Fundstelle also kein Anzeige-, sondern ein
    # Datenproblem, und die Volltextsuche der einzige Weg, der dort existiert.
    kreuz: dict[str, dict[str, int]] = {}
    for v in e.values():
        f = format_von(v.get("datei", ""))
        k = "markierbar" if v.get("suchtext") else ("nur_seite" if v.get("seite") else "keine_stelle")
        kreuz.setdefault(f, {})[k] = kreuz.setdefault(f, {}).get(k, 0) + 1
    return {
        "wurzel": str(w),
        "erreichbar": w.is_dir(),
        "quellen": len(e),
        "mit_fundstelle": len(mit_stelle),      # markierbar (Suchtext vorhanden)
        "nur_seite": len(nur_seite),            # aufschlagbar, nicht markierbar
        "ohne_stelle": len(e) - len(mit_stelle) - len(nur_seite),
        "nummern_mit_fundstelle": sorted(mit_stelle, key=lambda s: int(s) if s.isdigit() else 0),
        "formate": formate,
        "format_gegen_stelle": kreuz,
        "volltexte": len(volltext_dateien(w)),
    }


# ─── Selbsttest ───────────────────────────────────────────────────────────

def _selftest() -> int:
    # Die Seitenrechnung ist der Kern -- und sie wird ohne Dateisystem geprueft,
    # damit der Test auch ohne buckeberg laeuft.
    vt = ("--- Seite 1 ---\nEinleitung ohne Zahlen\n"
          "--- Seite 2 ---\nGrundverguetung 50,00 EUR je Wohneinheit\n"
          "--- Seite 3 ---\nSchluss\n")
    assert seite_aus_volltext(vt, "Grundverguetung 50,00") == 2
    assert seite_aus_volltext(vt, "Einleitung") == 1
    assert seite_aus_volltext(vt, "Schluss") == 3
    # Negativfall: was nicht dasteht, bekommt KEINE Seite -- nicht Seite 1.
    assert seite_aus_volltext(vt, "Hausmeisterkosten") is None
    assert seite_aus_volltext(vt, "") is None
    # Grenzwert: ein Auszug, der nicht bei Seite 1 beginnt, verschiebt nicht.
    assert seite_aus_volltext("--- Seite 7 ---\nnur hier\n", "nur hier") == 7
    # Zeilenumbruch mitten im Wortlaut ist der Normalfall in PDF-Auszuegen.
    assert seite_aus_volltext("--- Seite 4 ---\nGrundver-\nguetung  50,00\n",
                              "Grundver- guetung 50,00") == 4

    assert format_von("a.PDF") == "pdf" and format_von("a.html") == "html"
    assert format_von("a.docx") == "unbekannt"

    # Ohne Angabe wird nichts behauptet.
    leer = loese()
    assert leer.belegt is False and leer.seite is None

    # Nicht verzeichnete Quelle: Antwort, kein Absturz, keine erfundene Seite.
    nix = loese_quelle("999999")
    assert nix.belegt is False and nix.seite is None and nix.grund

    # Zu kurzer Wortlaut trifft ueberall -- also gilt er als kein Treffer.
    kurz = loese_text("ab")
    assert kurz.belegt is False

    print("fundstelle: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--quelle", default="", help="Nummer aus dossier/quellen.json")
    p.add_argument("--text", default="", help="Wortlaut, der belegt werden soll")
    p.add_argument("--bestand", action="store_true", help="Nenner und Abdeckung zeigen")
    p.add_argument("--korpus", default=None, help=f"Korpuswurzel (sonst ${ENV_KORPUS})")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        return _selftest()
    w = korpus_wurzel(a.korpus)
    if a.bestand:
        print(json.dumps(bestand(w), ensure_ascii=False, indent=2))
        return 0
    if not (a.quelle or a.text):
        p.print_help()
        return 2
    print(json.dumps(loese(a.quelle, a.text, w).als_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
