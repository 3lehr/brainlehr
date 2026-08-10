"""Der Selbsttest von bereinigung.py laeuft im Testlauf mit -- sonst ist er
ein Skript, das niemand aufruft, und verrottet wie jedes andere."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bereinigung  # noqa: E402


def test_selftest():
    bereinigung._selftest()


def test_meldet_nichts_bei_leerem_bestand(tmp_path, monkeypatch):
    """Negativfall: kein Fund heisst keine Protokollzeile, nicht eine leere."""
    monkeypatch.setattr(bereinigung, "PROTOKOLL", tmp_path / "log.jsonl")
    assert bereinigung.melde("probe", [("/x", {"summary": "636 gruen, 11 rot"})]) == 0
    assert not (tmp_path / "log.jsonl").exists()


def test_schreibt_fund_ohne_den_wortlaut(tmp_path, monkeypatch):
    log = tmp_path / "log.jsonl"
    monkeypatch.setattr(bereinigung, "PROTOKOLL", log)
    n = bereinigung.melde("recall", [("/x", {"summary": "Kontakt zwiebel.koch@kantine.de"})])
    assert n == 1
    inhalt = log.read_text(encoding="utf-8")
    assert "zwiebel.koch@kantine.de" not in inhalt, "Fundstelle darf nie im Protokoll stehen"
    assert "/x" in inhalt and "email" in inhalt
