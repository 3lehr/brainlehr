#!/usr/bin/env python3
"""Rot-vor-gruen fuer haken/worktree_identitaet.py (Aufgabe 98, Teil
WorktreeCreate).

Rot-Probe: Vor diesem Auftrag existierte `haken/worktree_identitaet.py`
gar nicht -- dieser Test haette mit ModuleNotFoundError durchweg rot
angeschlagen. Siehe auch den Selbsttest im Modul selbst
(`python3 haken/worktree_identitaet.py --selftest`), der dieselben vier
Faelle direkt gegen die internen Funktionen prueft; dieser Test prueft
zusaetzlich den `main()`-Pfad ueber echtes stdin/stdout wie ein Kommando-
Haken ihn tatsaechlich sieht.

Kein Zugriff auf den echten Hauptbaum -- alles gegen
tempfile.TemporaryDirectory().
"""

import importlib.util
import io
import json
import pathlib
import sys
import tempfile

WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "worktree_identitaet.py"

_spec = importlib.util.spec_from_file_location("worktree_identitaet_ev", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _run_main(stdin_text: str) -> str:
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(stdin_text)
    sys.stdout = out = io.StringIO()
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
    return out.getvalue()


def _basis(td: str) -> pathlib.Path:
    basis = pathlib.Path(td) / "hauptbaum"
    (basis / ".claude").mkdir(parents=True)
    (basis / "CLAUDE.md").write_text("# Hausregeln\n", encoding="utf-8")
    (basis / ".claude" / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")
    return basis


def test_zielverzeichnis_bekommt_beide_dateien_wenn_es_schon_existiert():
    """POSITIV: Nachbereitungsfall -- der neue Arbeitsbaum existiert bereits
    (leer), der Haken zieht CLAUDE.md (Symlink) und settings.json (Kopie)
    nach. Vorher hatte das Zielverzeichnis keine der beiden Dateien."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis(td)
        ziel = basis / ".claude" / "worktrees" / "probe"
        ziel.mkdir(parents=True)
        assert not (ziel / "CLAUDE.md").exists()
        assert not (ziel / ".claude" / "settings.json").exists()

        stdout = _run_main(json.dumps({"base_directory": str(basis), "worktree_name": "probe"}))

        assert stdout.strip() == str(ziel)
        assert (ziel / "CLAUDE.md").is_symlink(), "CLAUDE.md soll ein Symlink sein"
        assert (ziel / "CLAUDE.md").read_text(encoding="utf-8") == "# Hausregeln\n"
        assert (ziel / ".claude" / "settings.json").read_text(encoding="utf-8") == '{"hooks": {}}\n'
        assert not (ziel / ".claude" / "settings.json").is_symlink(), "settings.json soll eine Kopie sein"


def test_vorhandene_datei_im_zielbaum_wird_nicht_ueberschrieben():
    """GRENZWERT: Der Arbeitsbaum hat CLAUDE.md schon (z.B. aus eigenem
    Checkout) -- der Haken darf sie nicht durch einen Symlink ersetzen."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis(td)
        ziel = basis / ".claude" / "worktrees" / "probe"
        ziel.mkdir(parents=True)
        (ziel / "CLAUDE.md").write_text("# eigene Fassung im Baum\n", encoding="utf-8")

        _run_main(json.dumps({"base_directory": str(basis), "worktree_name": "probe"}))

        assert (ziel / "CLAUDE.md").read_text(encoding="utf-8") == "# eigene Fassung im Baum\n"
        assert not (ziel / "CLAUDE.md").is_symlink()


def test_fehlendes_zielverzeichnis_bleibt_folgenlos_und_druckt_trotzdem_den_pfad():
    """NEGATIV: Laeuft der Haken VOR der eigentlichen Anlage (Zielverzeichnis
    existiert noch nicht), legt er nichts an -- `git worktree add` verlangt
    ein leeres oder fehlendes Zielverzeichnis, ein vorab befuellter Ordner
    liesse die Anlage scheitern (empirisch geprueft, siehe Modulkopf).
    stdout traegt trotzdem den erwarteten Pfad, exit bleibt 0."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis(td)
        erwartet = basis / ".claude" / "worktrees" / "probe-fehlt-noch"

        stdout = _run_main(json.dumps({"base_directory": str(basis), "worktree_name": "probe-fehlt-noch"}))

        assert stdout.strip() == str(erwartet)
        assert not erwartet.exists(), "Haken haette das Zielverzeichnis nicht anlegen duerfen"


def test_interner_fehler_blockiert_die_anlage_nicht():
    """NEGATIV, wie im Auftrag verlangt: faellt die Kopierlogik intern mit
    einem Fehler aus, druckt main() trotzdem den Pfad (WorktreeCreate
    blockiert bei JEDEM Exit ungleich 0 -- dieser Haken darf also niemals
    mit einer Ausnahme durchfallen)."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis(td)
        ziel = basis / ".claude" / "worktrees" / "probe-kaputt"
        ziel.mkdir(parents=True)

        alt = hook._identitaet_nachziehen
        hook._identitaet_nachziehen = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaputt"))
        try:
            stdout = _run_main(json.dumps({"base_directory": str(basis), "worktree_name": "probe-kaputt"}))
        finally:
            hook._identitaet_nachziehen = alt

        assert stdout.strip() == str(ziel), stdout


def test_kaputtes_stdin_druckt_trotzdem_einen_pfad():
    """NEGATIV: Weder gueltiges JSON noch leeres stdin duerfen main() zum
    Absturz bringen -- der Kommando-Vertrag verlangt IMMER eine Pfadzeile."""
    stdout = _run_main("kein json{{{")
    assert stdout.strip(), "main() haette trotzdem eine Zeile drucken muessen"


if __name__ == "__main__":
    test_zielverzeichnis_bekommt_beide_dateien_wenn_es_schon_existiert()
    print("[POSITIV] existierendes Zielverzeichnis -> beide Dateien nachgezogen")
    test_vorhandene_datei_im_zielbaum_wird_nicht_ueberschrieben()
    print("[GRENZWERT] vorhandene Datei bleibt unangetastet")
    test_fehlendes_zielverzeichnis_bleibt_folgenlos_und_druckt_trotzdem_den_pfad()
    print("[NEGATIV] fehlendes Zielverzeichnis -> No-Op, Pfad trotzdem gedruckt")
    test_interner_fehler_blockiert_die_anlage_nicht()
    print("[NEGATIV] interner Fehler -> Pfad trotzdem gedruckt")
    test_kaputtes_stdin_druckt_trotzdem_einen_pfad()
    print("[NEGATIV] kaputtes stdin -> Pfad trotzdem gedruckt")
    print("test_worktree_identitaet: alle Zusicherungen halten")
