#!/usr/bin/env python3
"""`git commit -o <pfad>` auf eine brandneue Datei -- der Fehler, der gar
nicht erst entstehen darf.

ANLASS: `L-5e40a7` (3x, `escalated_to_rule`). `git commit -o <pfad>` (bzw.
`--only`) scheitert mit "pathspec did not match any file(s) known to git",
wenn `<pfad>` noch nie getrackt war -- `-o` committet nur bereits bekannte
Pfade, ein neuer Pfad muss vorher per `git add` bekannt gemacht werden. Die
zweite, teurere Variante desselben Fehlers: `git commit -q -- <pfade> -m
"..."` liest NACH `--` jedes weitere Wort als Pfad, verschluckt also `-m` und
die ganze mehrzeilige Nachricht als angeblichen Dateinamen und begraebt den
eigentlichen Fehler im Ausgabelaerm.

WARUM EIN WERKZEUG UND KEIN MELDER: Ein Melder ruegt NACH dem fehlgeschlagenen
Versuch -- der Fehler ist dann schon passiert (ein Shell-Fehlschlag, der
nichts Bleibendes hinterlaesst aber Zeit kostet und, schlimmer, im
Ausgabelaerm der zweiten Variante den eigentlichen Fehler verschleiert). Ein
Werkzeug, das den Aufruf gar nicht erst FALSCH bilden kann, schlaegt jeden
nachtraeglichen Waechter: hier gebaut als (a) Pfade werden IMMER per
`subprocess`-Argumentliste uebergeben, nie als Shell-String -- die
`-m-nach---`-Variante ist damit strukturell ausgeschlossen, nicht nur
verboten; (b) jeder Pfad wird vor dem Commit gegen `git status --porcelain`
geprueft, ein `??`-Pfad wird automatisch (und NUR er) per `git add` bekannt
gemacht, bevor `--only` laeuft.

    python3 tool/sicherer_commit.py <nachricht-datei-oder-'-'> -- <pfade>
    python3 tool/sicherer_commit.py --selftest
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class SichererCommitFehler(RuntimeError):
    """Der Commit wurde abgelehnt oder ist fehlgeschlagen -- Grund im Text."""


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args],
                           capture_output=True, text=True)


def untrackte_darunter(cwd: Path, pfade: list[str]) -> list[str]:
    """Welche der genannten Pfade sind laut `git status --porcelain` `??`
    (noch nie getrackt)."""
    if not pfade:
        return []
    lauf = _git(cwd, "status", "--porcelain", "--", *pfade)
    untrackt = set()
    for zeile in lauf.stdout.splitlines():
        if zeile.startswith("?? "):
            untrackt.add(zeile[3:].strip())
    # git meldet Pfade ggf. relativ zur Repo-Wurzel -- Abgleich per Endung
    # reicht hier, weil die Aufrufer stets repo-relative oder absolute Pfade
    # unterhalb von cwd uebergeben.
    return [p for p in pfade if p in untrackt or any(u.endswith(p) or p.endswith(u) for u in untrackt)]


def sicher_committen(cwd: Path, nachricht: str, pfade: list[str]) -> subprocess.CompletedProcess:
    """`git add` NUR fuer neue Pfade, dann `git commit --only -m <nachricht>
    -- <pfade>` -- als Argumentliste, nie als Shell-String. Wirft
    `SichererCommitFehler`, wenn `git add` oder `git commit` fehlschlaegt;
    verschluckt nichts."""
    if not pfade:
        raise SichererCommitFehler("keine Pfade uebergeben")
    neu = untrackte_darunter(cwd, pfade)
    if neu:
        lauf = _git(cwd, "add", "--", *neu)
        if lauf.returncode != 0:
            raise SichererCommitFehler(f"git add fehlgeschlagen fuer {neu}: {lauf.stderr.strip()}")
    lauf = _git(cwd, "commit", "--only", "-m", nachricht, "--", *pfade)
    if lauf.returncode != 0:
        raise SichererCommitFehler(f"git commit fehlgeschlagen: {lauf.stderr.strip() or lauf.stdout.strip()}")
    return lauf


# -------------------------------------------------------------------- Selbsttest
def _init_repo(wurzel: Path) -> None:
    subprocess.run(["git", "init", "-q", str(wurzel)], check=True)
    subprocess.run(["git", "-C", str(wurzel), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(wurzel), "config", "user.name", "t"], check=True)


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        wurzel = Path(td)
        _init_repo(wurzel)

        # ROT-PROBE: der ALTE, kaputte Weg (git commit -o <pfad> auf eine
        # brandneue Datei, ohne vorherigen add) MUSS scheitern -- sonst waere
        # der folgende Positivfall kein Beleg fuer die Reparatur.
        (wurzel / "neu.txt").write_text("x\n")
        alt = _git(wurzel, "commit", "-o", "-m", "roh", "--", "neu.txt")
        assert alt.returncode != 0, "Rot-Probe wirkungslos: der alte Weg haette hier scheitern muessen"
        assert "did not match any file" in (alt.stderr + alt.stdout), alt.stderr

        # 1) POSITIV: exakt derselbe Fall ueber den Wrapper -> gelingt.
        sicher_committen(wurzel, "erster commit: neu.txt", ["neu.txt"])
        log = _git(wurzel, "log", "--oneline", "-1")
        assert "erster commit" in log.stdout, log.stdout

        # 2) POSITIV: bereits getrackte Datei mit Aenderung -> gelingt weiterhin
        #    (der Wrapper darf den Normalfall nicht kaputt machen).
        (wurzel / "neu.txt").write_text("x\ny\n")
        sicher_committen(wurzel, "zweiter commit: aenderung", ["neu.txt"])
        log2 = _git(wurzel, "log", "--oneline", "-1")
        assert "zweiter commit" in log2.stdout, log2.stdout

        # 3) NEGATIV: eine Nachricht, die wie ein Pathspec-Angriff aussieht
        #    (" -- fake/pfad"), darf NICHT als zusaetzlicher Pfad gelesen
        #    werden -- Beleg fuer die Argumentliste statt Shell-String.
        (wurzel / "dritte.txt").write_text("z\n")
        boese_nachricht = "dritter commit -- fake/pfad.txt und -m spielverderber"
        sicher_committen(wurzel, boese_nachricht, ["dritte.txt"])
        log3 = _git(wurzel, "log", "--format=%B", "-1")
        assert boese_nachricht in log3.stdout, log3.stdout
        geaendert = _git(wurzel, "show", "--name-only", "--format=", "-1")
        dateien = [z for z in geaendert.stdout.splitlines() if z.strip()]
        assert dateien == ["dritte.txt"], dateien

        # 4) NEGATIV: leere Pfadliste wird abgelehnt, nicht stillschweigend
        #    committet (kein leerer Commit durch die Hintertuer).
        try:
            sicher_committen(wurzel, "leer", [])
            assert False, "haette SichererCommitFehler werfen muessen"
        except SichererCommitFehler:
            pass

        # 5) NEGATIV: Pfad, der weder existiert noch getrackt ist -> Fehler
        #    wird durchgereicht, nicht verschluckt.
        try:
            sicher_committen(wurzel, "geist", ["gibt_es_nicht.txt"])
            assert False, "haette SichererCommitFehler werfen muessen"
        except SichererCommitFehler as e:
            assert "fehlgeschlagen" in str(e), e

    print("sicherer_commit: Selbsttest gruen (Rot-Probe gegen den alten Weg, "
          "2 Positivfaelle inkl. Bestandsaenderung, 3 Negativfaelle: "
          "Pathspec-Angriff in der Nachricht, leere Pfadliste, unbekannter Pfad)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    argv = sys.argv[1:]
    if "--" not in argv:
        print(__doc__)
        return 2
    trenner = argv.index("--")
    nachricht_arg, pfade = argv[0], argv[trenner + 1:]
    nachricht = sys.stdin.read() if nachricht_arg == "-" else Path(nachricht_arg).read_text()
    try:
        sicher_committen(Path.cwd(), nachricht, pfade)
    except SichererCommitFehler as e:
        print(f"sicherer_commit: abgelehnt -- {e}", file=sys.stderr)
        return 1
    print("sicherer_commit: committet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
