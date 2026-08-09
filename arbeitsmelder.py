#!/usr/bin/env python3
"""Ein Melder auf die ARBEIT, nicht auf den Bestand -- S11 (docs/PLAN_DESTILLE_2026-08-09.md).

Anlass, und er ist ein Selbstbeleg: Innerhalb einer Stunde am 2026-08-09
sind drei Fehler passiert, zu denen jeweils eine Lehre im Bestand lag --
keine hat gefeuert, weil `pruefer.py` und alle anderen Melder den BESTAND
pruefen (Wissensknoten, Lehren, Spalten), nicht das, was gerade im
Arbeitsbaum ENTSTEHT. Der Speicher haengt am Gespraech, nicht an der
Arbeit.

BEZUGSGROESSE, und warum: der Diff des Arbeitsbaums (inkl. uncommitteter
Aenderungen) gegen den letzten Commit VOR dem heutigen Datum. Reiner
Uncommitted-Diff waere zu eng -- fast jede Aenderung dieses Tages ist
bereits committet (S1..S11 laufen als Einzelcommits, siehe "Committen ohne
Aufforderung" in den Hausregeln), ein Melder nur auf `git diff` saehe fast
nichts. Der ganze Bestand waere zu weit -- das ist genau der Fehler, den
dieser Melder beheben soll (S11: "wer den ganzen Bestand prueft, erzeugt
eine Liste, die niemand liest"). Der Tagesanfang ist ein fester, messbarer
Punkt (erster Commit mit Datum >= heute) und deckt genau das ab, was "in
DIESER Sitzung" (= an diesem Arbeitstag) entstanden ist.

Drei Fehlerklassen, alle mit Lehre im Bestand, alle am 2026-08-09
eingetreten (Belege unten je Pruefung):

  1. ZUSTAND ALS DURCHSATZ GEZAEHLT (L-502be0) -- eine Zeilenzahl einer
     wachsenden Protokolldatei wird als Ganzes gegen eine Schwelle
     gehalten, obwohl "Zeilen SEIT einem Zeitpunkt" gemeint war.
  2. ORTSABHAENGIGE ZAHL IM QUELLTEXT -- eine Nulllinie/Baseline, die an
     einem Ort GEMESSEN und dann als Literal in den Quelltext geschrieben
     wurde, statt am Leseort gemessen zu werden.
  3. LEERE ALS BEFUND (L-36d092) -- ein leeres, GEFILTERTES Abfrageergebnis
     wird als Feststellung gelesen, ohne dass der Filter selbst
     verdaechtigt (und ungefiltert gegengeprueft) wird.

Dieselben drei Auflagen wie `pruefer.py` gelten hier genauso (siehe dort):
messbar statt Stimmung, Fehlklasse benannt, Preis eines Fehlalarms
beziffert. Und er schweigt, wenn nichts anschlaegt.

VORBEHALT (aus dem Plan uebernommen, ernst zu nehmen): Fehlerklassen ohne
Bezeichner maschinell zu erkennen ist schwer. Darum bewusst nur diese drei,
schmal geschnittenen Muster -- kein Versuch, "schlechten Code" allgemein zu
erkennen. Wer die Trefferquote (--selbstpruefung) unter etwa 50 Prozent
brauchbarer Meldungen sieht, sollte die Muster enger schrauben statt sie
zu verallgemeinern (L-40d9a5: ein Melder mit hoher Fehlalarmquote erzieht
zum Ueberlesen).

Aufruf:
    python3 arbeitsmelder.py                # ausfuehrlich
    python3 arbeitsmelder.py --melder        # nur sprechen, wenn etwas anschlaegt
    python3 arbeitsmelder.py --selftest
    python3 arbeitsmelder.py --basis <ref>   # anderer Vergleichspunkt (Tests)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WURZEL = Path(__file__).resolve().parent


def _heutiger_tagesanfang(cwd: Path) -> str:
    """Der letzte Commit VOR dem heutigen Datum -- die Nulllinie dieses
    Melders selbst. Gemessen per `git log`, nie von Hand eingetragen (genau
    der Fehler aus Pruefstein 2 waere es, hier ein Datum zu haerten)."""
    heute = subprocess.run(["date", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(
        ["git", "log", "--format=%H", "--before", f"{heute} 00:00:00", "-1"],
        capture_output=True, text=True, cwd=cwd,
    )
    ref = r.stdout.strip()
    return ref or "HEAD"


@dataclass
class Zeile:
    pfad: str
    nr: int
    text: str


def _geaenderte_zeilen(cwd: Path, basis: str) -> dict[str, list[Zeile]]:
    """Neu hinzugefuegte Zeilen je .py-Datei seit `basis`, plus komplette
    neue (noch nicht versionierte) .py-Dateien. Nur ADDED-Zeilen zaehlen --
    eine Pruefung auf die ARBEIT prueft, was geschrieben wurde, nicht was
    unveraendert danebensteht."""
    ergebnis: dict[str, list[Zeile]] = {}

    diff = subprocess.run(
        ["git", "diff", "--unified=0", basis, "--", "*.py"],
        capture_output=True, text=True, cwd=cwd,
    ).stdout
    pfad = None
    zielzeile = None
    for zeile in diff.splitlines():
        if zeile.startswith("+++ b/"):
            pfad = zeile[6:]
            continue
        if zeile.startswith("@@"):
            m = re.search(r"\+(\d+)", zeile)
            zielzeile = int(m.group(1)) if m else 1
            continue
        if pfad and zeile.startswith("+") and not zeile.startswith("+++"):
            ergebnis.setdefault(pfad, []).append(Zeile(pfad, zielzeile, zeile[1:]))
            zielzeile += 1

    unversioniert = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
        capture_output=True, text=True, cwd=cwd,
    ).stdout.splitlines()
    for pfad_u in unversioniert:
        try:
            inhalt = (cwd / pfad_u).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        ergebnis[pfad_u] = [Zeile(pfad_u, i + 1, t) for i, t in enumerate(inhalt)]

    return ergebnis


def _voller_text(cwd: Path, pfad: str) -> list[str]:
    try:
        return (cwd / pfad).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Pruefstein 1: Zustand als Durchsatz gezaehlt (L-502be0)
# ---------------------------------------------------------------------------

_ZAEHL_RE = re.compile(
    r"=\s*sum\(1 for _ in\s+[\w./\"'()\[\] ]*\.(open|readlines)\("
    r"|=\s*sum\(1 for _ in open\("
)
_VERGLEICH_RE = re.compile(r"(>=|>)\s*\w")
_ABZUG_RE = re.compile(r"-\s*\w*(nulllinie|baseline|basis|start|grundlinie)\w*", re.IGNORECASE)


def zustand_als_durchsatz(cwd: Path, basis: str,
                          geaendert: dict[str, list[Zeile]]) -> list[dict]:
    """Eine Zeilenzahl ueber eine ganze Protokolldatei, direkt gegen eine
    Schwelle gehalten -- ohne dass irgendwo eine Nulllinie abgezogen wird.

    FEHLKLASSE: Zustand als Durchsatz gezaehlt (L-502be0, woertlich:
    "pruefen ob die gesuchte Groesse ein ZUSTAND oder ein DURCHSATZ ist.
    Ein Zustand steht in genau einer Zeile; wer ihn summiert, bekommt ein
    Integral und merkt es nicht."). Konkret hier: die GESAMTZAHL der
    Zeilen einer wachsenden Datei ist ein Durchsatz seit Dateianfang, kein
    Zustand seit einem Ereignis.

    PREIS EINES FEHLALARMS: mittel. Manche Zaehlungen ueber eine Datei
    SOLLEN den Gesamtbestand pruefen (z.B. "ist die Datei ueberhaupt schon
    ueber 0 Zeilen"). Darum nur, wenn eine Schwellenvergleichszeile in der
    Naehe UND keine Abzugsoperation im Umkreis von 8 Zeilen vorkommt --
    beides muss zutreffen, damit gemeldet wird."""
    funde = []
    for pfad, zeilen in geaendert.items():
        voll = _voller_text(cwd, pfad)
        geaenderte_nrn = {z.nr for z in zeilen}
        for z in zeilen:
            if not _ZAEHL_RE.search(z.text):
                continue
            fenster = voll[z.nr - 1: z.nr + 8]
            fenstertext = "\n".join(fenster)
            if not _VERGLEICH_RE.search(fenstertext):
                continue
            if _ABZUG_RE.search(fenstertext):
                continue  # Nulllinie wird abgezogen -- kein Durchsatz-Fehler
            funde.append({
                "pruefung": "zustand_als_durchsatz",
                "befund": f"{pfad}:{z.nr} zaehlt die Gesamtzeilen einer Datei und "
                          f"vergleicht sie ohne erkennbaren Nulllinien-Abzug gegen "
                          f"eine Schwelle: `{z.text.strip()}`",
                "fehlklasse": "Zustand als Durchsatz gezaehlt (L-502be0)",
                "fehlalarm_kostet": "mittel: manche Zaehlungen wollen bewusst den "
                                    "Gesamtbestand pruefen -- Fundstelle lesen, nicht blind aendern",
            })
    return funde


# ---------------------------------------------------------------------------
# Pruefstein 2: ortsabhaengige Zahl im Quelltext
# ---------------------------------------------------------------------------

_ORTSZAHL_RE = re.compile(
    r"\b\w*(nulllinie|baseline|grundlinie|startwert|ausgangswert)\w*\s*=\s*(\d+)\s*(#.*)?$",
    re.IGNORECASE,
)


def ortsabhaengige_zahl(cwd: Path, basis: str,
                        geaendert: dict[str, list[Zeile]]) -> list[dict]:
    """Eine Nulllinie/Baseline als nacktes Zahlenliteral im Quelltext,
    statt am Leseort gemessen.

    FEHLKLASSE: ortsabhaengige Zahl -- eine Zahl im Quelltext gilt fuer den
    Ort, den der Autor im Kopf hatte (Hauptverzeichnis, 42 Zeilen), waehrend
    der Code sie an seinem eigenen Ort liest (866 Zeilen). Am 2026-08-09
    unmittelbar nach Pruefstein 1 selbst passiert.

    PREIS EINES FEHLALARMS: gering. Eine Variable, die "nulllinie" oder
    "baseline" heisst UND ein blankes Zahlenliteral bekommt, ist so gut wie
    nie beabsichtigt -- der Name verspricht eine Messung, das Literal ist
    keine."""
    funde = []
    for pfad, zeilen in geaendert.items():
        for z in zeilen:
            m = _ORTSZAHL_RE.search(z.text)
            if not m:
                continue
            funde.append({
                "pruefung": "ortsabhaengige_zahl",
                "befund": f"{pfad}:{z.nr} setzt `{m.group(1)}` auf ein nacktes "
                          f"Zahlenliteral statt sie zu messen: `{z.text.strip()}`",
                "fehlklasse": "ortsabhaengige Zahl im Quelltext -- Nulllinie/Baseline "
                             "aus einer Messung an einem anderen Ort",
                "fehlalarm_kostet": "gering: der Variablenname verspricht eine Messung, "
                                    "ein Literal ist fast nie beabsichtigt",
            })
    return funde


# ---------------------------------------------------------------------------
# Pruefstein 3: Leere als Befund (L-36d092)
# ---------------------------------------------------------------------------

_SQL_FILTER_RE = re.compile(
    r"execute\(\s*[\"'].*\bWHERE\b.*(timestamp|zeit|datum|name|id)\s*[<>=]",
    re.IGNORECASE | re.DOTALL,
)
_LEER_ZWEIG_RE = re.compile(r"^\s*if\s+(not\s+\w+|len\(\w+\)\s*==\s*0|\w+\s*==\s*0)\s*:")
_BEFUND_PHRASEN = (
    "nicht vorhanden", "nicht gefunden", "keine ", "kein treffer",
    "existiert nicht", "hat nicht", "gibt es nicht",
)


def leere_als_befund(cwd: Path, basis: str,
                     geaendert: dict[str, list[Zeile]]) -> list[dict]:
    """Ein leeres, GEFILTERTES Abfrageergebnis wird als Feststellung
    gelesen, ohne den Filter selbst zu verdaechtigen.

    FEHLKLASSE: Leere als Befund (L-36d092, woertlich: "ein Filter, der auf
    einer Annahme ueber Zeit, Kennung oder Namen beruht, gehoert bei einem
    Nullergebnis zuerst weggelassen -- erst wenn es OHNE Filter auch leer
    bleibt, ist die Leere ein Befund"). Konkret hier: eine SQL-Abfrage mit
    WHERE-Filter (Zeit/Name/ID) liefert leer, und der naechste Code-Zweig
    spricht das als Tatsache aus, statt den Filter zu pruefen.

    PREIS EINES FEHLALARMS: hoch. Ein leerer Zweig nach einer gefilterten
    Abfrage ist oft schlicht der Normalfall (z.B. "kein Datensatz zu dieser
    ID" ist eine legitime, gewollte Antwort). Darum nur, wenn die Abfrage
    UND der Befund-Zweig beide in dieser Sitzung NEU geschrieben wurden --
    an bestehendem, bereits gelebtem Code ist die Vermutung schwaecher."""
    funde = []
    for pfad, zeilen in geaendert.items():
        voll = _voller_text(cwd, pfad)
        geaenderte_nrn = {z.nr for z in zeilen}
        volltext = "\n".join(voll)
        if not _SQL_FILTER_RE.search(volltext):
            continue
        for z in zeilen:
            if not _LEER_ZWEIG_RE.match(z.text):
                continue
            fenster = "\n".join(voll[z.nr: z.nr + 4]).lower()
            if not any(p in fenster for p in _BEFUND_PHRASEN):
                continue
            funde.append({
                "pruefung": "leere_als_befund",
                "befund": f"{pfad}:{z.nr} spricht bei leerem Ergebnis eine Feststellung "
                          f"aus, obwohl die Datei eine gefilterte SQL-Abfrage enthaelt: "
                          f"`{z.text.strip()}`",
                "fehlklasse": "Leere als Befund (L-36d092) -- Filter nicht verdaechtigt",
                "fehlalarm_kostet": "hoch: ein leeres, gewolltes Ergebnis ist oft der "
                                    "Normalfall -- Fundstelle immer lesen, nie blind aendern",
            })
    return funde


# ---------------------------------------------------------------------------
# Pruefstein 4: Protokoll als Nenner, ohne Beginn des Aufzeichnens (L-cb3f28)
# ---------------------------------------------------------------------------

_LOG_OEFFNEN_RE = re.compile(
    r"\b\w*log\w*\b\s*\.\s*(open|read_text|readlines)\("
    r"|open\([^)]*\blog\w*\b"
    r"|\.(jsonl|log)\b",
    re.IGNORECASE,
)
_NENNER_RE = re.compile(
    r"/[^\w]{0,3}len\(|len\([^)]*\)[^\w]{0,3}/|\bvon\s+(len\(|\{)|%\s*\)",
    re.IGNORECASE,
)
_ZEITVERGLEICH_RE = re.compile(
    r"\b(ts|timestamp|datum)\w*\b.{0,60}(>=|>|<|<=)"
    r"|(>=|>|<|<=).{0,60}\b(ts|timestamp|datum)\w*\b",
    re.IGNORECASE | re.DOTALL,
)


def _funktion_grenzen(voll: list[str], zeilen_nr: int) -> tuple[int, int]:
    """Start- und Endindex (0-basiert, Ende exklusiv) der Funktion, in der
    Zeile `zeilen_nr` (1-basiert) liegt. Ohne umschliessendes `def` ein
    schmales Fenster als Rueckfall -- besser eine zu enge Pruefung als ein
    Absturz."""
    idx = zeilen_nr - 1
    def_idx = def_indent = None
    for i in range(idx, -1, -1):
        m = re.match(r"^(\s*)def\s+\w+\(", voll[i])
        if m:
            def_idx, def_indent = i, len(m.group(1))
            break
    if def_idx is None:
        return (max(0, idx - 5), min(len(voll), idx + 5))
    ende = len(voll)
    for j in range(def_idx + 1, len(voll)):
        zeile = voll[j]
        if not zeile.strip():
            continue
        einzug = len(zeile) - len(zeile.lstrip())
        if einzug <= def_indent:
            ende = j
            break
    return (def_idx, ende)


def _helfer_mit_zeitvergleich(voll: list[str], koerper: str) -> bool:
    """Eine Ebene der Aufrufkette: enthaelt der Rumpf selbst keinen
    Zeitvergleich, aber ruft er eine andere Funktion DESSELBEN Moduls auf,
    deren eigener Rumpf einen Zeitvergleich enthaelt, gilt das als erfuellt.
    Tiefer wird bewusst nicht verfolgt (kein rekursiver Abstieg in die
    Helfer der Helfer) -- Preis: eine ueber zwei Ebenen versteckte Filterung
    wird weiterhin faelschlich gemeldet, der Leser muss dann eine
    Fundstelle lesen."""
    for name in set(re.findall(r"\b([a-zA-Z_]\w*)\s*\(", koerper)):
        for i, zeile in enumerate(voll):
            m = re.match(rf"^(\s*)def\s+{re.escape(name)}\(", zeile)
            if not m:
                continue
            indent = len(m.group(1))
            ende = len(voll)
            for j in range(i + 1, len(voll)):
                z = voll[j]
                if not z.strip():
                    continue
                if len(z) - len(z.lstrip()) <= indent:
                    ende = j
                    break
            if _ZEITVERGLEICH_RE.search("\n".join(voll[i:ende])):
                return True
    return False


def protokoll_als_nenner(cwd: Path, basis: str,
                         geaendert: dict[str, list[Zeile]]) -> list[dict]:
    """Ein Protokoll (.jsonl/.log oder eine log-benannte Datei) wird als
    Ganzes gelesen und dient als Nenner einer Quote/Prozentzahl -- ohne dass
    dieselbe Funktion die Protokollzeilen gegen eine Zeit-/Datumsuntergrenze
    filtert.

    FEHLKLASSE: Protokoll als Nenner, ohne Beginn des Aufzeichnens (L-cb3f28).
    Konkret zweimal am 2026-08-09 eingetreten: recall_log.jsonl wurde
    vollstaendig als Grundmenge gelesen und daraus eine Quote gebildet (88
    von 205 "unerklaert"), obwohl leere Abrufe erst seit Commit e3ef28f
    (2026-08-09 09:52:53) ueberhaupt protokolliert werden -- "leerer Abruf"
    war davon nicht von "gar kein Abruf" zu unterscheiden. Nach Beschneiden
    des Fensters blieben von 94 Faellen 2 unerklaert statt 88 von 205.

    PREIS EINES FEHLALARMS: mittel. Eine Auswertung, die absichtlich das
    GESAMTE Protokoll zaehlen will (Durchsatz statt Zustand seit einem
    Ereignis -- z.B. eine reine Statistik ueber den kompletten Bestand),
    wird hier faelschlich gemeldet, sobald sie zusaetzlich eine Quote
    daraus bildet; grob geschaetzt jede 3.-5. Meldung dieser Sorte. Der
    Leser muss dann eine Zeile lesen und entscheiden -- reines Zaehlen ohne
    Quote (`_NENNER_RE`) loest dagegen gar nicht erst aus."""
    funde = []
    gemeldete_funktionen: set[tuple[str, int]] = set()
    for pfad, zeilen in geaendert.items():
        voll = _voller_text(cwd, pfad)
        for z in zeilen:
            if not _LOG_OEFFNEN_RE.search(z.text):
                continue
            start, ende = _funktion_grenzen(voll, z.nr)
            schluessel = (pfad, start)
            if schluessel in gemeldete_funktionen:
                continue
            koerper = "\n".join(voll[start:ende])
            if not _NENNER_RE.search(koerper):
                continue
            if _ZEITVERGLEICH_RE.search(koerper):
                continue  # Zeitvergleich auf den Protokollzeilen vorhanden
            if _helfer_mit_zeitvergleich(voll, koerper):
                continue  # Zeitvergleich eine Ebene tiefer, in aufgerufenem Helfer
            gemeldete_funktionen.add(schluessel)
            funde.append({
                "pruefung": "protokoll_als_nenner",
                "befund": f"{pfad}:{z.nr} liest ein Protokoll vollstaendig und bildet "
                          f"daraus eine Quote, ohne die Zeilen gegen eine Zeit-/"
                          f"Datumsuntergrenze zu filtern: `{z.text.strip()}`",
                "fehlklasse": "Protokoll als Nenner, ohne Beginn des Aufzeichnens (L-cb3f28)",
                "fehlalarm_kostet": "mittel: eine absichtliche Zaehlung ueber das GESAMTE "
                                    "Protokoll (Durchsatz statt Zustand) wird hier "
                                    "faelschlich gemeldet -- Fundstelle lesen, nicht blind aendern",
            })
    return funde


PRUEFUNGEN = (zustand_als_durchsatz, ortsabhaengige_zahl, leere_als_befund, protokoll_als_nenner)


_EIGENE_DATEI = Path(__file__).name


def alle(cwd: Path | None = None, basis: str | None = None) -> list[dict]:
    """Schliesst die eigene Datei aus: ihr Selbsttest enthaelt die
    historischen Fehlermuster als STRINGS (Fixtures), und diese Zeilen
    matchen textlich genauso wie echter Code -- ohne den Ausschluss meldet
    sich der Melder selbst, sobald er unversioniert im Arbeitsbaum liegt."""
    # DER ORT WIRD GEMESSEN, NICHT ANGENOMMEN -- und das ist genau der
    # Pruefstein, den dieses Modul selbst sucht (ortsabhaengige Groesse im
    # Quelltext). Erste Fassung nahm WURZEL, also brainlehrs eigenes
    # Verzeichnis. Gemessen 2026-08-09 aus dem fahrtenbuch-Arbeitsbaum
    # heraus: dort lagen 43 geaenderte Dateien, der Melder sagte "nichts
    # anzumerken" -- er sah die ganze Arbeit des Betreibers in fremden
    # Baeumen nie.
    #
    # Der Melder haengt an PostToolUse und laeuft im Arbeitsverzeichnis der
    # SITZUNG. Genau das ist der Baum, in dem gerade geschrieben wird.
    # WURZEL bleibt nur der Rueckfall, wenn dort kein Repo liegt.
    if cwd is None:
        import os
        hier = Path(os.getcwd())
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, cwd=hier)
        cwd = Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else WURZEL
    basis = basis or _heutiger_tagesanfang(cwd)
    geaendert = {p: z for p, z in _geaenderte_zeilen(cwd, basis).items()
                if Path(p).name != _EIGENE_DATEI}
    funde = []
    for pruefung in PRUEFUNGEN:
        funde.extend(pruefung(cwd, basis, geaendert))
    return funde


# ---------------------------------------------------------------------------
# Selbsttest -- rot vor gruen an den historischen Fassungen der drei Fehler,
# dazu ein Fehlalarm-Test.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    def git(cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "t@t.de")
        git(repo, "config", "user.name", "t")

        # Basisstand: eine leere Datei, committet -- das ist "vor der Sitzung".
        (repo / "melder_test.py").write_text("# leer\n", encoding="utf-8")
        git(repo, "add", "melder_test.py")
        git(repo, "commit", "-q", "-m", "basis")
        basis = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                               capture_output=True, text=True).stdout.strip()

        # --- Pruefstein 1, historische (buggy) Fassung: Gesamtzeilen statt
        # Zeilen seit Nulllinie -- so wie am 2026-08-09 vor der Korrektur
        # in pruefer.py gestanden hat (siehe docs/PLAN_DESTILLE_2026-08-09.md, S11).
        buggy_1 = (
            "from pathlib import Path\n"
            "def faellig(datei: Path, schwelle: int) -> bool:\n"
            "    n = sum(1 for _ in datei.open(encoding='utf-8'))\n"
            "    if n >= schwelle:\n"
            "        return True\n"
            "    return False\n"
        )
        (repo / "melder_test.py").write_text(buggy_1, encoding="utf-8")
        funde = alle(repo, basis)
        assert any(f["pruefung"] == "zustand_als_durchsatz" for f in funde), \
            "Pruefstein 1 muss an der historisch buggy Fassung anschlagen"

        # Korrigierte Fassung (heutiger Stand, mit Nulllinien-Abzug) --
        # NICHT anschlagen.
        fix_1 = (
            "from pathlib import Path\n"
            "def faellig(datei: Path, nulllinie: int, schwelle: int) -> bool:\n"
            "    n = sum(1 for _ in datei.open(encoding='utf-8'))\n"
            "    seit = n - nulllinie\n"
            "    if seit >= schwelle:\n"
            "        return True\n"
            "    return False\n"
        )
        (repo / "melder_test.py").write_text(fix_1, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "zustand_als_durchsatz" for f in funde), \
            "korrigierte Fassung (mit Nulllinien-Abzug) darf nicht anschlagen"

        # --- Fehlalarm-Test: eine harmlose Zaehlung ueber eine Liste im
        # Speicher (kein .open()) darf niemals anschlagen -- sonst ist das
        # Muster zu grob.
        harmlos = (
            "def anzahl(elemente: list) -> bool:\n"
            "    n = sum(1 for _ in elemente)\n"
            "    if n >= 20:\n"
            "        return True\n"
            "    return False\n"
        )
        (repo / "melder_test.py").write_text(harmlos, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "zustand_als_durchsatz" for f in funde), \
            "sum() ueber eine Liste im Speicher ist kein Durchsatz-Fehler -- Fehlalarm"

        # --- Pruefstein 2, historische Fassung: Nulllinie von Hand als
        # Literal eingetragen (42, aus dem Hauptverzeichnis gemessen),
        # waehrend der Code an seinem eigenen Ort liest.
        buggy_2 = "NULLLINIE_RECALL_LOG = 42\n"
        (repo / "melder_test.py").write_text(buggy_2, encoding="utf-8")
        funde = alle(repo, basis)
        assert any(f["pruefung"] == "ortsabhaengige_zahl" for f in funde), \
            "Pruefstein 2 muss an der handeingetragenen Nulllinie anschlagen"

        # Korrigierte Fassung: Nulllinie wird gemessen, nicht eingetragen.
        fix_2 = (
            "from pathlib import Path\n"
            "def nulllinie(datei: Path) -> int:\n"
            "    return sum(1 for _ in datei.open(encoding='utf-8'))\n"
        )
        (repo / "melder_test.py").write_text(fix_2, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "ortsabhaengige_zahl" for f in funde), \
            "gemessene Nulllinie darf nicht anschlagen"

        # --- Pruefstein 3, historische Fassung: leeres, gefiltertes
        # SQL-Ergebnis wird als Feststellung gelesen (L-36d092: Zeitfilter
        # angenommen statt gemessen).
        buggy_3 = (
            "def suchen(conn, seit):\n"
            "    zeilen = conn.execute(\n"
            "        \"SELECT * FROM recall_log WHERE timestamp > ?\", (seit,)\n"
            "    ).fetchall()\n"
            "    if not zeilen:\n"
            "        print('keine Suchen gefunden')\n"
            "        return None\n"
            "    return zeilen\n"
        )
        (repo / "melder_test.py").write_text(buggy_3, encoding="utf-8")
        funde = alle(repo, basis)
        assert any(f["pruefung"] == "leere_als_befund" for f in funde), \
            "Pruefstein 3 muss an der ungeprueften Leere anschlagen"

        # Korrigierte Fassung: kein Befund-Wortlaut im leeren Zweig (Filter
        # wird stattdessen zuerst ohne Zeitfilter erneut versucht).
        fix_3 = (
            "def suchen(conn, seit):\n"
            "    zeilen = conn.execute(\n"
            "        \"SELECT * FROM recall_log WHERE timestamp > ?\", (seit,)\n"
            "    ).fetchall()\n"
            "    if not zeilen:\n"
            "        zeilen = conn.execute(\"SELECT * FROM recall_log\").fetchall()\n"
            "    return zeilen\n"
        )
        (repo / "melder_test.py").write_text(fix_3, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "leere_als_befund" for f in funde), \
            "Fassung ohne Befund-Wortlaut im leeren Zweig darf nicht anschlagen"

        # --- Pruefstein 4, historische Fassung: recall_log.jsonl wird
        # komplett gelesen und daraus eine Quote gebildet -- ohne
        # Zeitvergleich auf den Protokollzeilen (L-cb3f28, woertlich siehe
        # oben: 88 von 205 "unerklaert", weil leere Abrufe erst seit einem
        # bestimmten Commit ueberhaupt protokolliert werden).
        buggy_4 = (
            "import json\n"
            "def quote_unerklaert(pfad):\n"
            "    zeilen = [json.loads(z) for z in open(pfad + '/recall_log.jsonl')]\n"
            "    unerklaert = sum(1 for z in zeilen if not z.get('treffer'))\n"
            "    if unerklaert / len(zeilen) > 0.3:\n"
            "        print(f\"{unerklaert} von {len(zeilen)} unerklaert\")\n"
            "    return unerklaert\n"
        )
        (repo / "melder_test.py").write_text(buggy_4, encoding="utf-8")
        funde = alle(repo, basis)
        assert any(f["pruefung"] == "protokoll_als_nenner" for f in funde), \
            "Pruefstein 4 muss anschlagen, wenn ein Protokoll ohne Zeitvergleich als Nenner dient"

        # Korrigierte Fassung: dieselbe Quote, aber die Zeilen werden zuerst
        # auf einen Zeitraum ab einer Untergrenze beschnitten.
        fix_4 = (
            "import json\n"
            "def quote_unerklaert(pfad, seit):\n"
            "    zeilen = [json.loads(z) for z in open(pfad + '/recall_log.jsonl')]\n"
            "    zeilen = [z for z in zeilen if z.get('timestamp', 0) >= seit]\n"
            "    unerklaert = sum(1 for z in zeilen if not z.get('treffer'))\n"
            "    if unerklaert / len(zeilen) > 0.3:\n"
            "        print(f\"{unerklaert} von {len(zeilen)} unerklaert\")\n"
            "    return unerklaert\n"
        )
        (repo / "melder_test.py").write_text(fix_4, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "protokoll_als_nenner" for f in funde), \
            "Fassung mit Zeitvergleich auf den Protokollzeilen darf nicht anschlagen"

        # --- Eine Ebene der Aufrufkette: der Zeitvergleich sitzt nicht in
        # der pruefenden Funktion selbst, sondern in einem Helfer desselben
        # Moduls, den sie aufruft (wie in pruefer.py: _seit_untergrenze).
        helfer_mit_zeit = (
            "import json\n"
            "def _seit_untergrenze(zeilen, seit):\n"
            "    return [z for z in zeilen if z.get('timestamp', 0) >= seit]\n"
            "def quote_unerklaert(pfad, seit):\n"
            "    zeilen = [json.loads(z) for z in open(pfad + '/recall_log.jsonl')]\n"
            "    zeilen = _seit_untergrenze(zeilen, seit)\n"
            "    unerklaert = sum(1 for z in zeilen if not z.get('treffer'))\n"
            "    if unerklaert / len(zeilen) > 0.3:\n"
            "        print(f\"{unerklaert} von {len(zeilen)} unerklaert\")\n"
            "    return unerklaert\n"
        )
        (repo / "melder_test.py").write_text(helfer_mit_zeit, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "protokoll_als_nenner" for f in funde), \
            "Zeitvergleich im aufgerufenen Helfer (eine Ebene) darf nicht anschlagen"

        # --- Gegenprobe: derselbe Aufbau, aber der aufgerufene Helfer
        # filtert NICHT nach Zeit -- muss weiterhin anschlagen.
        helfer_ohne_zeit = (
            "import json\n"
            "def _alle_zeilen(zeilen):\n"
            "    return [z for z in zeilen if z.get('treffer') is not None]\n"
            "def quote_unerklaert(pfad, seit):\n"
            "    zeilen = [json.loads(z) for z in open(pfad + '/recall_log.jsonl')]\n"
            "    zeilen = _alle_zeilen(zeilen)\n"
            "    unerklaert = sum(1 for z in zeilen if not z.get('treffer'))\n"
            "    if unerklaert / len(zeilen) > 0.3:\n"
            "        print(f\"{unerklaert} von {len(zeilen)} unerklaert\")\n"
            "    return unerklaert\n"
        )
        (repo / "melder_test.py").write_text(helfer_ohne_zeit, encoding="utf-8")
        funde = alle(repo, basis)
        assert any(f["pruefung"] == "protokoll_als_nenner" for f in funde), \
            "Helfer ohne Zeitvergleich darf den Fund nicht unterdruecken"

        # --- Fehlalarm-Test: das Protokoll wird gelesen und gezaehlt, aber
        # es wird KEINE Quote/Prozentzahl daraus gebildet (reiner Durchsatz-
        # Ausdruck, kein Nenner-Missbrauch) -- darf nicht anschlagen.
        harmlos_4 = (
            "def zeilen_zaehlen(pfad):\n"
            "    with open(pfad + '/recall_log.jsonl') as f:\n"
            "        zeilen = f.readlines()\n"
            "    print(f\"{len(zeilen)} Zeilen im Protokoll\")\n"
            "    return len(zeilen)\n"
        )
        (repo / "melder_test.py").write_text(harmlos_4, encoding="utf-8")
        funde = alle(repo, basis)
        assert not any(f["pruefung"] == "protokoll_als_nenner" for f in funde), \
            "reines Zaehlen ohne Quote ist kein Nenner-Missbrauch -- Fehlalarm"

    print("selftest ok (12 Faelle: 4 Pruefsteine je rot+gruen, 1 Aufrufketten-Ebene "
          "je rot+gruen, 2 Fehlalarm)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--basis", default=None, help="Vergleichspunkt statt Tagesanfang (Tests)")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return

    funde = alle(basis=a.basis)

    if a.melder:
        if funde:
            zeilen = [f"{f['befund']} ({f['fehlklasse']})" for f in funde]
            print("⚠️ Arbeitsmelder: " + "\n   ".join(zeilen))
        return

    if not funde:
        print("Arbeitsmelder: nichts anzumerken.")
        return
    for f in funde:
        print(f"[{f['pruefung']}] {f['befund']}")
        print(f"   Fehlklasse:  {f['fehlklasse']}")
        print(f"   Fehlalarm:   {f['fehlalarm_kostet']}")


if __name__ == "__main__":
    main()
