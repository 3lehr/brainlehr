"""Tests fuer caveman_bulk.py + json_minify.py."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sys
from pathlib import Path

import pytest

# REPO_ROOT ist der hub, nicht der Elternordner: seit dem Umzug am
# 2026-08-08 liegt brainlehr neben dem hub statt darin, und parents[2]
# zeigte auf den Verbund-Ordner. Die Aufloesung steht in conftest.py,
# damit sie an einer Stelle korrigierbar bleibt.
from conftest import HUB  # noqa: E402

REPO_ROOT = HUB if HUB else Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "begod/scripts"
sys.path.insert(0, str(SCRIPTS))

import caveman_bulk as cb  # type: ignore  # noqa: E402
import json_minify as jm  # type: ignore  # noqa: E402


# --- caveman_bulk --------------------------------------------------------

def test_bulk_dry_run_does_not_write(tmp_path: Path):
    f = tmp_path / "note.md"
    original = (
        "# Note\n\nThis is just basically a really simple note. "
        "It would be good to make sure to consider this carefully.\n"
    )
    f.write_text(original, encoding="utf-8")
    backup = f.with_name("note.original.md")

    sys.argv = ["caveman_bulk.py", "--dry-run", "--root", str(tmp_path), "--min-chars", "10"]
    rc = cb.main(["--dry-run", "--root", str(tmp_path), "--min-chars", "10"])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == original
    assert not backup.exists()


def test_bulk_apply_writes_with_backup(tmp_path: Path):
    f = tmp_path / "note.md"
    original = (
        "# Note\n\nThis is just basically a really simple note. "
        "It would be good to make sure to consider this carefully. "
        "Sure! I'd be happy to help with that.\n"
    )
    f.write_text(original, encoding="utf-8")
    backup = f.with_name("note.original.md")

    rc = cb.main(["--apply", "--root", str(tmp_path), "--min-chars", "10"])
    assert rc == 0
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original
    assert f.read_text(encoding="utf-8") != original


def test_bulk_skips_legal_content(tmp_path: Path):
    f = tmp_path / "legal_note.md"
    original = "Dies basiert auf Art. 6 DSGVO. Bitte beachten.\n" * 20
    f.write_text(original, encoding="utf-8")
    rc = cb.main(["--apply", "--root", str(tmp_path), "--min-chars", "10"])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == original


def test_bulk_skips_denied_paths(tmp_path: Path):
    legal = tmp_path / "legal"
    legal.mkdir()
    f = legal / "rules.md"
    f.write_text("Just a really simple test text.\n" * 30, encoding="utf-8")
    # Note: bulk denylist gates auf REPO_ROOT-relativ; ausserhalb REPO ungeprueft.
    # Daher gegen denylist-pattern passenden Ordnernamen mit fnmatch im Tool testen:
    import caveman_compress as cc
    policy = cc.load_policy()
    denied, _ = policy.is_denied("legal/rules.md")
    assert denied


def test_bulk_restore_all(tmp_path: Path):
    f = tmp_path / "x.md"
    original = "Original content. " * 20 + "Just basically really.\n"
    f.write_text(original, encoding="utf-8")
    cb.main(["--apply", "--root", str(tmp_path), "--min-chars", "10"])
    assert f.read_text(encoding="utf-8") != original
    rc = cb.main(["--restore-all", "--root", str(tmp_path)])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == original


# --- json_minify --------------------------------------------------------

def test_json_minify_data_file(tmp_path: Path):
    f = tmp_path / "data.json"
    data = {"a": 1, "b": [1, 2, 3], "c": {"nested": "value"}}
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    backup = f.with_name("data.original.json")

    rc = jm.main(["--apply", "--root", str(tmp_path)])
    assert rc == 0
    assert backup.exists()
    minified = f.read_text(encoding="utf-8")
    assert "\n" not in minified
    assert json.loads(minified) == data


def test_json_minify_protects_schemas(tmp_path: Path):
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    f = schemas / "konsil.json"
    data = {"$schema": "x", "type": "object"}
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    import caveman_compress as cc
    policy = cc.load_policy()
    denied, _ = policy.is_denied("schemas/konsil.json")
    assert denied


def test_json_minify_preserves_identity(tmp_path: Path):
    f = tmp_path / "complex.json"
    data = {
        "list": [{"k": "v"}, None, True, False, 1.5, "text"],
        "unicode": "Begod2026 — Pflege-Lotse",
        "empty": [],
    }
    f.write_text(json.dumps(data, indent=4), encoding="utf-8")
    jm.main(["--apply", "--root", str(tmp_path)])
    re = json.loads(f.read_text(encoding="utf-8"))
    assert re == data


def test_json_minify_dry_run_no_write(tmp_path: Path):
    f = tmp_path / "x.json"
    original = json.dumps({"k": "v"}, indent=2)
    f.write_text(original, encoding="utf-8")
    jm.main(["--dry-run", "--root", str(tmp_path)])
    assert f.read_text(encoding="utf-8") == original


def test_json_minify_blocks_package_json(tmp_path: Path):
    f = tmp_path / "package.json"
    f.write_text(json.dumps({"name": "x"}, indent=2), encoding="utf-8")
    rc = jm.main(["--apply", "--root", str(tmp_path)])
    assert rc == 0
    # File unveraendert weil ADDITIONAL_DENY greift
    assert "\n" in f.read_text(encoding="utf-8")
