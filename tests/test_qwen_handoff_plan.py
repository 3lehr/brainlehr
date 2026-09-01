import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PHASE_DIR = ROOT / "docs" / "qwen_abschluss"
PHASES = (
    "00_BOOTSTRAP_OMLX_GRENZE.md",
    "01_KATALOG_GRAPH_P60_P62.md",
    "02_P42_ANALYZER_OSS.md",
    "03_ALLE_MUST_P67.md",
    "04_HERMES_ZWEI_REPOS.md",
    "05_PAKET_DIFF_UEBERGABE.md",
    "06_CODEX_ENDABNAHME.md",
)
QWEN_ROLLOVER_PHASES = PHASES[:5]
BOOTSTRAP = PHASE_DIR / "BOOTSTRAP_STABLE.md"
STARTPROMPT = PHASE_DIR / "STARTPROMPT_STABLE.md"
STATE_SCHEMA = PHASE_DIR / "RUN_STATE.schema.json"
INITIAL_STATE = PHASE_DIR / "RUN_STATE.initial.json"


def test_every_qwen_phase_has_terminal_gate_and_rollover_prompt():
    for name in PHASES:
        text = (PHASE_DIR / name).read_text()
        assert "## Abschlussgate" in text, name
        assert "## Neues Kontextfenster öffnen" in text, name


def test_qwen_rollovers_reuse_one_exact_startprompt():
    for name in QWEN_ROLLOVER_PHASES:
        text = (PHASE_DIR / name).read_text()
        assert "exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden" in text, name
        assert "Du bist Qwen3.8 im" not in text, name


def test_phase_chain_is_ordered_and_preserves_release_boundaries():
    for current, successor in zip(PHASES, PHASES[1:]):
        assert successor in (PHASE_DIR / current).read_text(), current
    combined = "\n".join((PHASE_DIR / name).read_text() for name in PHASES)
    for required in (
        "DB=UNTOUCHED/FROZEN",
        "PUSH=NOT_DONE",
        "CANDIDATE PASS",
        "CodeRank",
        "BGE-M3",
        "untracked",
        "Produktiv-DB",
    ):
        assert required in combined


def test_stable_prefix_excludes_runtime_churn():
    prompt = STARTPROMPT.read_text()
    bootstrap = BOOTSTRAP.read_text()
    combined = prompt + bootstrap
    assert "/Volumes/daten/brainlehr-qwen-run/state.json" in combined
    assert "next_phase_path" in prompt
    assert not re.search(r"20\d\d-\d\d-\d\d", combined)
    assert not re.search(r"[0-9a-f]{40,64}", combined)
    assert not re.search(r"/0[0-6]_[A-Z0-9_]+\.md", prompt)
    for forbidden in ("BOOTSTRAP_SHA256_PLACEHOLDER", "STARTPROMPT_SHA256_PLACEHOLDER"):
        assert forbidden not in combined


def test_initial_state_matches_schema_contract_and_file_hashes():
    schema = json.loads(STATE_SCHEMA.read_text())
    state = json.loads(INITIAL_STATE.read_text())
    assert set(state) == set(schema["required"])
    assert state["plan_schema_version"] == schema["properties"]["plan_schema_version"]["const"]
    assert state["phase_id"] == "00"
    assert state["db_mode"] == "FROZEN"
    assert state["push_status"] == "NOT_DONE"
    assert state["retrieval"] == {
        "bge_m3": "ACTIVE",
        "coderank": "H0_INACTIVE",
        "rrf": "INACTIVE",
    }
    assert state["bootstrap_sha256"] == hashlib.sha256(BOOTSTRAP.read_bytes()).hexdigest()
    assert state["startprompt_sha256"] == hashlib.sha256(STARTPROMPT.read_bytes()).hexdigest()
    requirements = ROOT / "docs" / "REQUIREMENTS_BRAINLEHR.md"
    assert state["requirements_sha256"] == hashlib.sha256(requirements.read_bytes()).hexdigest()
