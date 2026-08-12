#!/usr/bin/env python3
"""geheimnis.py -- das eigene BRAINLEHR_GEHEIMNIS kommt aus einer Datei,
nicht mehr nur aus der Umgebung.

Ausgelagert aus ausweis.py wegen der Monolith-Bremse (>1500 Zeilen, keine
neue Logik mehr in diese Datei). ausweis.loese_auf() ruft
`aufloesen_mit_datei()` auf, statt os.environ.get(ENV_GEHEIMNIS) direkt zu
nehmen.

ANLASS: ~/.claude.json traegt das Geheimnis im Klartext unter
mcpServers.knowledge.env -- und wird von einem Assistenten routinemaessig als
GANZE Datei gelesen (am 2026-08-12 in einer anderen Sitzung geschehen). Jedes
Lesen ist eine weitere Stelle, an der das Geheimnis im Kontext eines Modells
steht. Der bisherige Wert gilt seither als kompromittiert; die Rotation tippt
der Betreiber selbst.

DATEI STATT KONFIGURATION: mein-geheimnis.txt hat GENAU EINEN Inhalt (das
Geheimnis, eine Zeile) und GENAU EINEN Zweck. Kein Aufgabenkontext braucht
ihren Volltext fuer irgendetwas anderes -- anders als ~/.claude.json, die
Server-Namen, Pfade, Modelleinstellungen etc. neben dem Geheimnis traegt und
darum als Ganzes angefasst wird, sobald jemand nur eine dieser Angaben
braucht.

ORT: liegt neben ausweise.json (also im selben, bereits geschuetzten Ordner
mit Rechten 0700 -- Vorgabe ~/Desktop/brainlehr-ausweise, uebersteuerbar mit
BRAINLEHR_AUSWEISE). Kein zweiter Ort, keine zweite Umgebungsvariable dafuer:
wo die Rechtetabelle liegt, liegt auch das Geheimnis, das sie freischaltet.

RECHTE: 0600, wie ausweise.json. Zu weite Rechte -> Datei wird ignoriert
(Meldung auf stderr), nicht stillschweigend verwendet. Lieber unbeglaubigt
als falsch beglaubigt -- dieselbe Regel wie bei ausweise.json.

VORRANG: Datei vor Umgebungsvariable. Sind beide gesetzt und verschieden, ist
das ein Befund (zwei Geheimnisse im Umlauf) und wird auf stderr gemeldet --
die Datei gewinnt trotzdem, still waere hier die falsche Antwort auf einen
Widerspruch.

SICHERHEITSAUFLAGE (gilt fuer dieses Modul wie fuer den Rest des Systems):
kein Aufruf hier gibt den WERT des Geheimnisses aus, weder auf stdout noch in
einer Fehlermeldung -- nur sein Vorhandensein und ob zwei Quellen sich
unterscheiden.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

GEHEIMNISDATEI_NAME = "mein-geheimnis.txt"
_ENV_NAME_FUER_MELDUNG = "BRAINLEHR_GEHEIMNIS"  # nur fuer die Textmeldung


def geheimnisdatei(ausweis_pfad: Path) -> Path:
    """Pfad der eigenen Geheimnisdatei -- liegt neben der Ausweisdatei, folgt
    also automatisch BRAINLEHR_AUSWEISE mit."""
    return ausweis_pfad.parent / GEHEIMNISDATEI_NAME


def _lies_geheimnisdatei(datei: Path) -> str | None:
    """None, wenn es die Datei nicht gibt, sie zu weite Rechte traegt oder
    keine verwertbare Zeile enthaelt -- niemals ein Fehler, denn "Datei
    fehlt" ist vor der Erstausstattung der Normalfall.

    L-ad7232 (GEHEIMNIS-markus.txt, 2026-08-10: 6 Zeilen, 4 davon
    Erklaertext): eine Datei, die Wert UND Erklaerung mischt, macht
    `.strip()` auf den ganzen Inhalt zum Geheimnis -- die Pruefung schlaegt
    dann IMMER fehl, und der Rueckfall (unbeglaubigt) sieht wie "keine Datei
    vorhanden" aus, nicht wie "Datei vorhanden, Inhalt falsch verstanden".
    Der naechste Mensch, der die Datei von Hand anlegt, schreibt eine
    Erklaerung wie in mein-geheimnis.txt selbst empfohlen -- also findet das
    lesende Werkzeug die Zeile selbst: erste nicht-leere Zeile, die nicht mit
    '#' beginnt, ohne umgebende Leerzeichen.

    WEITERE ZEILEN werden still ignoriert, nicht gemeldet: diese Funktion
    laeuft potenziell bei jeder Anmeldung. Eine Meldung bei jedem Lesen einer
    kommentierten Datei waere Dauerlaerm fuer einen Zustand, der nicht falsch
    ist -- nur die erste passende Zeile zaehlt, das ist keine Ausnahme."""
    if not datei.exists():
        return None
    modus = datei.stat().st_mode
    if modus & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"geheimnis: {datei} ist fuer Gruppe/Andere zugaenglich "
              f"(0{modus & 0o777:o}) -- ignoriert. Beheben: chmod 600 {datei}",
              file=sys.stderr)
        return None
    try:
        inhalt = datei.read_text(encoding="utf-8")
    except OSError as fehler:
        print(f"geheimnis: {datei} nicht lesbar ({fehler}) -- ignoriert.",
              file=sys.stderr)
        return None
    for zeile in inhalt.splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#"):
            return zeile
    return None


def aufloesen_mit_datei(umgebung_wert: str | None, ausweis_pfad: Path) -> str | None:
    """Datei vor Umgebungsvariable. Beide gesetzt und verschieden -> Befund
    auf stderr, Datei gewinnt trotzdem. Keins von beiden -> None, der
    Aufrufer (ausweis.loese_auf) faellt dann in den unbeglaubigten Zweig --
    das ist die bewusste Entscheidung, kein Versehen."""
    datei = geheimnisdatei(ausweis_pfad)
    datei_wert = _lies_geheimnisdatei(datei)
    if datei_wert and umgebung_wert and datei_wert != umgebung_wert:
        print(f"geheimnis: {_ENV_NAME_FUER_MELDUNG} (Umgebung) und {datei} "
              f"unterscheiden sich -- die Datei hat Vorrang, die "
              f"Umgebungsvariable wird fuer diese Aufloesung ignoriert. Zwei "
              f"unterschiedliche Geheimnisse im Umlauf ist ein Befund, keine "
              f"stille Auswahl. Beheben: den veralteten Eintrag entfernen.",
              file=sys.stderr)
    return datei_wert or umgebung_wert


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ausweis_pfad = Path(tmp) / "ausweise.json"
        datei = geheimnisdatei(ausweis_pfad)
        assert datei == Path(tmp) / GEHEIMNISDATEI_NAME

        # --- keins von beiden -> None, kein Fehler --------------------------
        assert aufloesen_mit_datei(None, ausweis_pfad) is None

        # --- nur Umgebung -> Ruecktritt greift -------------------------------
        assert aufloesen_mit_datei("aus-umgebung", ausweis_pfad) == "aus-umgebung"

        # --- nur Datei -> ihr Wert wird genommen -----------------------------
        fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("aus-datei\n")
        assert aufloesen_mit_datei(None, ausweis_pfad) == "aus-datei"

        # --- beide gleich -> kein Widerspruch, Datei-Wert kommt zurueck -----
        assert aufloesen_mit_datei("aus-datei", ausweis_pfad) == "aus-datei"

        # --- beide verschieden -> Datei gewinnt, Meldung auf stderr ---------
        alt_stderr = sys.stderr
        import io
        sys.stderr = io.StringIO()
        try:
            ergebnis = aufloesen_mit_datei("aus-umgebung", ausweis_pfad)
            meldung = sys.stderr.getvalue()
        finally:
            sys.stderr = alt_stderr
        assert ergebnis == "aus-datei", "Datei haette gewinnen muessen"
        assert "unterscheiden sich" in meldung, "Befund fehlte auf stderr"
        assert "aus-datei" not in meldung and "aus-umgebung" not in meldung, \
            "Geheimniswert stand in der Meldung -- Sicherheitsauflage verletzt"

        # --- zu weite Rechte -> Datei wird ignoriert -------------------------
        os.chmod(datei, 0o644)
        assert aufloesen_mit_datei(None, ausweis_pfad) is None
        os.chmod(datei, 0o600)
        assert aufloesen_mit_datei(None, ausweis_pfad) == "aus-datei"

        # --- L-ad7232: Kommentare und Leerzeilen um den Wert werden nicht
        # Teil des Geheimnisses -- die erste passende Zeile zaehlt ----------
        fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# Mein Geheimnis, nicht weitergeben\n\n"
                    "GEHEIM-ABC-123\n\n# Ende\n")
        assert aufloesen_mit_datei(None, ausweis_pfad) == "GEHEIM-ABC-123", \
            "die Erklaerung drumherum wurde Teil des Geheimnisses"

        # --- reine Kommentardatei ohne Wert -> None, kein kaputter Wert -----
        fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# nur Erklaerung, kein Geheimnis drin\n")
        assert aufloesen_mit_datei(None, ausweis_pfad) is None

    print("geheimnis.py: Selbsttest gruen")


if __name__ == "__main__":
    raise SystemExit(_selftest())
