"""Test fuer melder/ausloeserlos.py (Auftrag 85, Schritt A2).

Rot-vor-gruen, Grenzwert und Negativfall stehen bereits im Modul-eigenen
--selftest (ausloeserlos._selftest, laeuft ueber test_alle_selftests.py als
Teil der vollen Suite, auf einer Attrappen-Verzeichnisstruktur). Diese Datei
ergaenzt den Blick auf den ECHTEN Bestand -- genau die drei Faelle aus der
Abnahme, gegen die echte settings.json und den echten Quelltext, ohne
irgendetwas zu schreiben (der Melder liest nur)."""
from __future__ import annotations

import ausloeserlos
import ort


def test_selftest():
    ausloeserlos._selftest()


def test_negativfall_knowledge_recall_hook_wird_nicht_gemeldet():
    """haken/knowledge_recall_hook.py steht mit einem UserPromptSubmit-
    Eintrag in ~/.claude/settings.json -- nachweislich verdrahtet, darf nie
    im Bericht auftauchen."""
    settings_pfade = [__import__("pathlib").Path.home() / ".claude" / "settings.json",
                       ort.WURZEL / ".claude" / "settings.json"]
    funde = ausloeserlos.bericht(ort.WURZEL, settings_pfade)
    namen = {f["name"] for f in funde}
    assert "haken/knowledge_recall_hook.py" not in namen


def test_grenzwert_kanten_aus_bedeutung_ist_kein_kandidat():
    """kern/kanten_aus_bedeutung.py steht in KEINER settings.json und laeuft
    trotzdem, weil haken/auszug_nachziehen.py es importiert. Es ist tabu
    fuer diesen Auftrag und liegt ausserhalb der drei Kandidatenordner
    (melder/, haken/, berichte/) -- der Melder darf es darum niemals als
    Kandidaten auffuehren, unabhaengig vom Ausloeser-Befund."""
    kandidaten_namen = {p.name for p in ausloeserlos.kandidaten(ort.WURZEL)}
    assert "kanten_aus_bedeutung.py" not in kandidaten_namen


def test_transitiver_ausloeser_ueber_zwei_ebenen_im_echten_bestand():
    """haken/suchpfad_abruf.py hat KEINEN eigenen settings.json-Eintrag,
    wird aber (direkt oder ueber haken/mehrstufiger_abruf.py) von
    haken/knowledge_recall_hook.py importiert, das seinerseits verdrahtet
    ist -- die transitive Kette, ohne die dieser Melder die Vormessung nur
    nachprogrammiert haette."""
    settings_pfade = [__import__("pathlib").Path.home() / ".claude" / "settings.json",
                       ort.WURZEL / ".claude" / "settings.json"]
    quellen = ausloeserlos.alle_quellen(ort.WURZEL)
    stxt = ausloeserlos.settings_texte(settings_pfade)
    gtxt = ausloeserlos.hole_geplante_texte()
    ok, weg = ausloeserlos.hat_ausloeser(
        ort.WURZEL / "haken" / "suchpfad_abruf.py", quellen, stxt, gtxt)
    assert ok, "suchpfad_abruf.py muesste ueber knowledge_recall_hook.py einen Ausloeser haben"
    assert "settings.json" in weg


def test_melder_endet_immer_mit_erfolg():
    """Hinweisrecht, kein Veto: main() darf nie einen Nicht-Null-Code
    liefern, egal wie viele Funde es macht."""
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, str(ort.WURZEL / "melder" / "ausloeserlos.py"), "--bericht"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr
