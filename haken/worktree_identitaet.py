#!/usr/bin/env python3
"""WorktreeCreate-Haken: Identitaets- und Regeldateien reisen mit.

DIE LUECKE (Aufgabe 92, Befund 2026-08-13): CLAUDE.md 0 von 5 Arbeitsbaeumen,
.claude/settings.json 0 von 5. Jedes gemessene Stop-Ereignis lief mit einem
Arbeitsbaum als Verzeichnis, nie im Hauptbaum -- die projekteigene Regelablage
wirkte deshalb nie, weil sie den Arbeitsbaum nie erreichte. `git worktree add`
checkt nur aus, was zum Checkout-Commit bereits VERSIONIERT ist; ein Baum, der
von einem aelteren Commit abzweigt, bekommt eine Datei nicht, die erst spaeter
hinzukam -- und `brainlehr/CLAUDE.md` existiert zum Zeitpunkt dieses Haken noch
gar nicht (nachgesehen, nicht vermutet). Aufgabe 92 legt den Inhalt an; dieser
Haken legt nur den WEG, auf dem er (und die projekteigene settings.json)
kuenftig jeden neuen Arbeitsbaum erreicht.

ENTWURFSFRAGE je Datei (nicht pauschal, Aufsatz laut Auftrag):

  CLAUDE.md -> SYMLINK (relativ). Ein Arbeitsbaum liegt gemessen (git worktree
  list, 8 Baeume) IMMER unter `<base_directory>/.claude/worktrees/<name>` --
  eine relative Verlinkung `../../../CLAUDE.md` bleibt darum gueltig, solange
  diese Schachtelung haelt (und genau die Schachtelung ist die Voraussetzung,
  unter der dieser Haken ueberhaupt laeuft). Ein Symlink hat hier keinen
  Nachteil gegenueber einer Kopie: Hausregeln aendern sich, eine Kopie wuerde
  veralten (dieselbe Fehlerklasse wie eine hinterherhinkende Datenbanksicherung,
  siehe haken/auszug_nachziehen.py), ein Symlink nie. Existiert im Zielbaum
  bereits eine reguliere Datei (z.B. weil ein spaeterer Commit CLAUDE.md selbst
  versioniert und normal auscheckt), wird NICHT ueberschrieben -- ein
  ausgechecktes Original schlaegt den Symlink.

  .claude/settings.json -> KOPIE, kein Symlink. Diese Datei ist
  projekteigene Werkzeug-Konfiguration; ein Symlink wuerde jede Aenderung, die
  ein Agent INNERHALB des Arbeitsbaums an ihr vornimmt, sofort in den
  Hauptbaum durchreichen -- und damit auf alle anderen parallel laufenden
  Sitzungen wirken. Exakt die Gefahr, vor der dieser Auftrag bei
  ~/.claude/settings.json selbst warnt (Sicherungskopie vor jeder Aenderung,
  nur additiv). Eine Kopie darf veralten; das ist hier der kleinere Preis als
  eine versehentliche Fernwirkung. Kopiert wird nur, wenn im Zielbaum noch
  keine settings.json liegt -- ein aeltere-Commit-Baum hat sonst schon eine
  aus dem eigenen Checkout, und die ist massgeblich.

STDOUT-VERTRAG (offizielle Referenz, code.claude.com/docs/en/hooks.md):
Ein Kommando-Haken auf WorktreeCreate hat KEIN JSON-Ausgabeformat -- Claude
Code liest stdout direkt als den Pfad des Arbeitsbaums. Der Pfad wird darum
gedruckt, auch wenn die eigene Kopierlogik scheitert.

ZWEI FEHLSCHLAEGE AM 2026-08-13, beide hier dokumentiert, weil der zweite aus
der Korrektur des ersten entstand:
  (1) Fehlte `worktree_name`, druckte der Haken `<base>/.claude/worktrees` --
      das Sammelverzeichnis selbst. git lehnte ab: "already in use by worktree
      ...". Keine neue Sitzung mehr moeglich.
  (2) Daraufhin druckte er gar nichts mehr. Der Klient lehnte erneut ab, jetzt
      mit "no output". Die Annahme, ein leeres stdout lasse ihn seinen
      Vorgabepfad waehlen, war Modellwissen und falsch.
RICHTIG IST DIE DRITTE ANTWORT: immer eine Zeile, aber nie ein belegter Pfad.
Fehlt der Name, wird einer mit Zeitstempel und Prozesskennung erzeugt.

DIE LEHRE UEBER BEIDE FEHLSCHLAEGE: Ein Vertrag mit genau zwei Zustaenden
("Zeile" gegen "keine Zeile") verleitet dazu, den Fehlerfall in den zweiten zu
schieben. Hier hat der Vertrag aber nur EINEN gueltigen Zustand -- und dann
muss der Fehlerfall INNERHALB dessen geloest werden, nicht daneben.

NIE BLOCKIEREND: WorktreeCreate lehnt bei jedem Exit-Code ungleich 0 die
Anlage komplett ab (staerkster Exit-Vertrag aller Ereignisse). Ein Haken, der
selbst abstuerzt, darf darum niemals mit einem Fehler enden -- die gesamte
Kopierlogik liegt in einem try/except, das im schlimmsten Fall nur den Pfad
druckt und sonst nichts tut.

STAND 2026-08-13: Selbsttest per `python3 haken/worktree_identitaet.py
--selftest`. Empirisch geprueft (git-Testrepo unter /tmp): `git worktree add`
verlangt ein LEERES Zielverzeichnis -- ein vorab befuellter Ordner laesst die
Anlage mit "fatal: ... already exists" scheitern. Deshalb seedet dieser Haken
NIE, bevor das Zielverzeichnis existiert; er ist ein reiner Nachbereiter, der
still bleibt, falls er vor der eigentlichen Anlage laeuft (leeres oder
fehlendes Zielverzeichnis).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _zeitmarke() -> str:
    """Eindeutiger Namensteil, wenn der Klient keinen Namen mitgibt."""
    import time
    return time.strftime("%Y%m%dT%H%M%S") + f"-{os.getpid()}"


def _zielpfad(base_directory: str, worktree_name: str) -> Path:
    return Path(base_directory) / ".claude" / "worktrees" / worktree_name


def _identitaet_nachziehen(base_directory: str, worktree_ziel: Path) -> None:
    """Kopiert/verlinkt die zwei bekannten Regeldateien, falls das
    Zielverzeichnis schon existiert (Nachbereitung) und dort noch fehlen."""
    if not worktree_ziel.is_dir():
        return  # Anlage laeuft noch / dieser Aufruf kommt vor ihr -- nichts tun.

    basis = Path(base_directory)

    # CLAUDE.md: Symlink, siehe Modulkopf.
    quelle = basis / "CLAUDE.md"
    ziel = worktree_ziel / "CLAUDE.md"
    if quelle.exists() and not ziel.exists() and not ziel.is_symlink():
        relativ = os.path.relpath(quelle, ziel.parent)
        ziel.symlink_to(relativ)

    # .claude/settings.json: Kopie, siehe Modulkopf.
    quelle = basis / ".claude" / "settings.json"
    ziel = worktree_ziel / ".claude" / "settings.json"
    if quelle.exists() and not ziel.exists():
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(quelle.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    rohdaten = sys.stdin.read()
    daten: dict = {}
    try:
        daten = json.loads(rohdaten) if rohdaten.strip() else {}
    except Exception:
        daten = {}

    base_directory = daten.get("base_directory") or os.getcwd()
    worktree_name = daten.get("worktree_name") or ""

    # DREI ANTWORTEN WAREN MOEGLICH, ZWEI SIND FALSCH (Befund 2026-08-13).
    #
    # 1. Das Sammelverzeichnis drucken -- so war es, und git wies die Anlage ab
    #    mit "already in use by worktree ...". Der Betreiber konnte keine neue
    #    Sitzung starten.
    # 2. Nichts drucken -- mein erster Fix. Der Klient meldete daraufhin
    #    "no output" und lehnte ebenfalls ab. Ich hatte angenommen, er waehle
    #    dann seinen Vorgabepfad; das war Modellwissen, nicht geprueft.
    # 3. Einen GUELTIGEN, FREIEN Pfad drucken. Nur das erfuellt beide
    #    Bedingungen: Der Vertrag verlangt eine Zeile, und die Zeile darf kein
    #    belegtes Verzeichnis nennen.
    #
    # Fehlt der Name, wird einer erzeugt. Ein erfundener Name ist hier
    # unbedenklich, weil er nur den ORT bestimmt -- der Zweig kommt vom
    # Klienten. Und er kann nicht kollidieren, weil er den Zeitstempel traegt.
    if not worktree_name:
        worktree_name = "baum-" + _zeitmarke()

    pfad = _zielpfad(base_directory, worktree_name)

    # Zweite Schranke: Selbst mit Namen darf der Pfad nie das Sammelverzeichnis
    # sein (etwa bei einem Namen aus Punkten oder Schraegstrichen).
    sammel = Path(base_directory) / ".claude" / "worktrees"
    if pfad.resolve() == sammel.resolve():
        return

    # VIERTER FEHLSCHLAG AM SELBEN VERTRAG, 2026-08-14, gemeldet vom Betreiber
    # beim Start eines neuen Chats:
    #   "hook printed .../baum-20260814T121618-62360 but no directory exists there"
    #
    # Der Klient verlangt inzwischen, dass der gedruckte Pfad EXISTIERT. Damit
    # ist die bisherige Selbstbeschreibung hinfaellig: dieser Haken ist kein
    # Nachbereiter, er ist ein VORBEREITER. Beides zugleich geht nicht, und
    # daran haengt die ganze Schwierigkeit --
    #
    #   git worktree add akzeptiert ein bereits vorhandenes LEERES Verzeichnis
    #   (gemessen 2026-08-14 an einem Wegwerf-Repo, beide Faelle gefahren:
    #   leer vorhanden -> exit 0, gar nicht vorhanden -> exit 0),
    #   aber es scheitert an einem BEFUELLTEN ("fatal: ... already exists").
    #
    # Also: Verzeichnis anlegen, ja. Es hier befuellen, nein -- das wuerde die
    # Anlage zerstoeren, die der Haken ermoeglichen soll. Der Aufruf von
    # _identitaet_nachziehen faellt an dieser Stelle deshalb weg; er stand vor
    # dem mkdir und lief bislang ohnehin ins Leere (Zielverzeichnis existierte
    # noch nicht), nach dem mkdir haette er aktiv geschadet.
    #
    # WAS DAMIT OFFEN IST, und es wird benannt statt verschwiegen: CLAUDE.md
    # und .claude/settings.json reisen derzeit NICHT mehr mit. Der richtige Ort
    # dafuer ist ein Ereignis NACH der Anlage (SessionStart im neuen Baum) --
    # eine Verdrahtung in ~/.claude/settings.json, die dem Betreiber gehoert.
    # _identitaet_nachziehen bleibt darum stehen und getestet, damit dieser
    # Umzug nur eine Verdrahtung ist und keine Neuentwicklung.
    try:
        pfad.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # Haken darf die Anlage nie verhindern (Exit bleibt 0).

    print(str(pfad))


def _selftest() -> None:
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="worktree_identitaet_selftest_"))
    try:
        base = tmp / "hauptbaum"
        (base / ".claude").mkdir(parents=True)
        (base / "CLAUDE.md").write_text("# Hausregeln\n", encoding="utf-8")
        (base / ".claude" / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")

        # 1) POSITIV: Zielverzeichnis existiert schon (Nachbereitungsfall) ->
        # beide Dateien landen darin, CLAUDE.md als Symlink, settings.json als Kopie.
        ziel = _zielpfad(str(base), "probe1")
        ziel.mkdir(parents=True)
        _identitaet_nachziehen(str(base), ziel)
        assert (ziel / "CLAUDE.md").is_symlink(), "CLAUDE.md haette ein Symlink werden muessen"
        assert (ziel / "CLAUDE.md").read_text(encoding="utf-8") == "# Hausregeln\n"
        assert not (ziel / ".claude" / "settings.json").is_symlink(), "settings.json haette eine Kopie sein muessen"
        assert (ziel / ".claude" / "settings.json").read_text(encoding="utf-8") == '{"hooks": {}}\n'
        print("[POSITIV] existierendes Zielverzeichnis -> CLAUDE.md verlinkt, settings.json kopiert")

        # 2) GRENZWERT: Datei liegt im Ziel schon vor (regulaere Datei) ->
        # NICHT ueberschreiben.
        ziel2 = _zielpfad(str(base), "probe2")
        ziel2.mkdir(parents=True)
        (ziel2 / "CLAUDE.md").write_text("# eigene Fassung\n", encoding="utf-8")
        (ziel2 / ".claude").mkdir()
        (ziel2 / ".claude" / "settings.json").write_text('{"eigen": true}\n', encoding="utf-8")
        _identitaet_nachziehen(str(base), ziel2)
        assert (ziel2 / "CLAUDE.md").read_text(encoding="utf-8") == "# eigene Fassung\n", "vorhandene Datei wurde ueberschrieben"
        assert not (ziel2 / "CLAUDE.md").is_symlink()
        assert (ziel2 / ".claude" / "settings.json").read_text(encoding="utf-8") == '{"eigen": true}\n'
        print("[GRENZWERT] vorhandene Datei bleibt unangetastet")

        # 3) NEGATIV: Zielverzeichnis existiert noch NICHT (Vorlauf-Fall) ->
        # kein Fehler, kein mkdir, stiller No-Op.
        ziel3 = _zielpfad(str(base), "probe3-existiert-noch-nicht")
        _identitaet_nachziehen(str(base), ziel3)
        assert not ziel3.exists(), "Haken haette das Zielverzeichnis nicht anlegen duerfen"
        print("[NEGATIV] fehlendes Zielverzeichnis -> No-Op, kein Anlegen")

        # 4) main() druckt IMMER den Pfad, auch wenn die Kopierlogik intern
        # eine Ausnahme wirft -- Nachbau des "Haken faellt aus"-Falls.
        import io as _io
        import worktree_identitaet as _mod  # eigenes Modul, siehe unten geladen

        alt = _mod._identitaet_nachziehen
        _mod._identitaet_nachziehen = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaputt"))
        stdin_bak, stdout_bak = sys.stdin, sys.stdout
        sys.stdin = _io.StringIO(json.dumps({"base_directory": str(base), "worktree_name": "probe4"}))
        sys.stdout = out = _io.StringIO()
        try:
            _mod.main()
        finally:
            sys.stdin, sys.stdout = stdin_bak, stdout_bak
            _mod._identitaet_nachziehen = alt
        erwartet = str(_zielpfad(str(base), "probe4"))
        assert out.getvalue().strip() == erwartet, out.getvalue()
        print("[NEGATIV] interner Fehler -> stdout traegt trotzdem den Pfad (Exit bleibt 0)")

        # 5) DER FELDFEHLER vom 2026-08-13T22:05: Fehlt worktree_name, darf
        # NICHTS gedruckt werden. Frueher kam hier `<base>/.claude/worktrees`
        # heraus -- das Sammelverzeichnis selbst -- und git wies die Anlage ab
        # mit "already in use by worktree ...". Der Betreiber konnte keine neue
        # Sitzung mehr starten. Ohne diesen Fall waere der Selbsttest gruen
        # geblieben, denn Fall 4 prueft nur den Weg MIT Namen.
        for eingabe in ({"base_directory": str(base)},
                        {"base_directory": str(base), "worktree_name": ""}):
            stdin_bak, stdout_bak = sys.stdin, sys.stdout
            sys.stdin = _io.StringIO(json.dumps(eingabe))
            sys.stdout = out = _io.StringIO()
            try:
                _mod.main()
            finally:
                sys.stdin, sys.stdout = stdin_bak, stdout_bak
            zeile = out.getvalue().strip()
            assert zeile, "ohne worktree_name muss trotzdem eine Zeile kommen"
            sammel = str(_zielpfad(str(base), ""))
            assert zeile.rstrip("/") != sammel.rstrip("/"), (
                "gedruckt wurde das Sammelverzeichnis: " + zeile)
            assert zeile.startswith(sammel.rstrip("/") + "/baum-"), zeile
        print("[FELDFEHLER] ohne worktree_name -> gueltiger erzeugter Pfad, nie das Sammelverzeichnis")

        # 5) FELDFEHLER 2026-08-14, vierter am selben Vertrag: der Klient
        # lehnt ab, wenn der gedruckte Pfad nicht existiert ("hook printed
        # ... but no directory exists there"). Zwei Zusicherungen, und die
        # zweite ist die schwierigere: das Verzeichnis muss existieren UND
        # leer sein -- ein befuelltes laesst `git worktree add` scheitern
        # ("fatal: ... already exists"), und dann haette der Haken die Anlage
        # auf die andere Weise verhindert.
        import contextlib as _ctx
        import io as _io
        base5 = tmp / "hauptbaum5"
        (base5 / ".claude").mkdir(parents=True)
        (base5 / "CLAUDE.md").write_text("# Hausregeln\n", encoding="utf-8")
        (base5 / ".claude" / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")
        eingabe = json.dumps({"base_directory": str(base5), "worktree_name": "probe5"})
        out5 = _io.StringIO()
        alt_stdin = sys.stdin
        sys.stdin = _io.StringIO(eingabe)
        try:
            with _ctx.redirect_stdout(out5):
                main()
        finally:
            sys.stdin = alt_stdin
        gedruckt = Path(out5.getvalue().strip())
        assert gedruckt.is_dir(), (
            f"gedruckter Pfad existiert nicht: {gedruckt} -- genau die vom "
            "Betreiber gemeldete Ablehnung des Klienten")
        assert not any(gedruckt.iterdir()), (
            f"gedrucktes Verzeichnis ist nicht leer: {list(gedruckt.iterdir())} -- "
            "git worktree add scheitert dann mit 'already exists'. Hier NICHT "
            "befuellen; das gehoert an ein Ereignis NACH der Anlage.")
        print("[FELDFEHLER] gedruckter Pfad existiert und ist leer -- beide Bedingungen")

        print("worktree_identitaet: alle Zusicherungen halten")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        # Modul unter eigenem Namen importierbar machen (fuer Testfall 4).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        _selftest()
    else:
        main()
