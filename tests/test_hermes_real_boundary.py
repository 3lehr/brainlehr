"""P74 external gold: real Hermes classes, fake transport, no user memory."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

import project_context


HERMES = Path.home() / ".hermes" / "hermes-agent"
ADAPTER = Path("/Volumes/daten/Begod2026/hermes-brainlehr")


def _external_or_skip():
    if not (HERMES / "agent" / "memory_manager.py").is_file() or not (ADAPTER / "brainlehr_provider.py").is_file():
        pytest.skip("P74 coverage_gap: real Hermes/Brainlehr adapter checkout is unavailable")
    for path in (str(HERMES), str(ADAPTER)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from agent.memory_manager import MemoryManager
    from agent.memory_provider import MemoryProvider
    from brainlehr_provider import BrainlehrProvider
    return MemoryManager, MemoryProvider, BrainlehrProvider


def test_real_hermes_memory_manager_keeps_builtin_and_brainlehr_bounded_without_writes():
    MemoryManager, MemoryProvider, BrainlehrProvider = _external_or_skip()

    class Builtin(MemoryProvider):
        @property
        def name(self):
            return "builtin"
        def is_available(self):
            return True
        def initialize(self, session_id, **kwargs):
            return None
        def get_tool_schemas(self):
            return []
        def prefetch(self, query, *, session_id=""):
            return "builtin:" + query
        def queue_prefetch(self, query, *, session_id=""):
            self.queued = query

    class FakeMCP:
        def __init__(self):
            self.calls = []
        def ruf(self, name, args):
            self.calls.append((name, args))
            assert name == "knowledge_search", "default Hermes sync must not write"
            return {"results": [{"title": "Bounded", "summary": "evidence", "source": "test"}]}

    fake = FakeMCP()
    provider = BrainlehrProvider()
    provider._verbindung = lambda: fake
    provider.initialize("isolated", agent_context="primary")
    builtin = Builtin()
    manager = MemoryManager(external_prefetch_timeout=1)
    manager.add_provider(builtin)
    manager.add_provider(provider)

    foreground = manager.prefetch_all("specific query", session_id="s")
    manager.queue_prefetch_all("next query", session_id="s")
    manager.sync_all("user content", "assistant content", session_id="s")
    assert manager.flush_pending(3)
    assert [item.name for item in manager.providers] == ["builtin", "brainlehr"]
    assert "builtin:specific query" in foreground and "Aus brainlehr" in foreground
    assert len(fake.calls) == 1
    assert builtin.queued == "next query"
    assert provider.mitschrift is False and provider.mitschrift_grund.startswith("mitschrift ist ausgeschaltet")


@pytest.mark.parametrize("mode", ["empty", "error", "timeout"])
def test_real_brainlehr_provider_makes_empty_error_and_timeout_visible(mode):
    _, _, BrainlehrProvider = _external_or_skip()
    status, warnings = [], []
    provider = BrainlehrProvider()
    provider.initialize("isolated", agent_context="primary", status_callback=status.append, warning_callback=warnings.append)
    if mode == "empty":
        provider._suchen = lambda query: []
    elif mode == "error":
        provider._suchen = lambda query: (_ for _ in ()).throw(RuntimeError("fake transport"))
    else:
        provider._suchen = lambda query: (time.sleep(0.05) or [])
        import brainlehr_provider
        old = brainlehr_provider.WARTEFRIST
        brainlehr_provider.WARTEFRIST = 0.001
    try:
        assert provider.prefetch("long enough query") == ""
    finally:
        if mode == "timeout":
            brainlehr_provider.WARTEFRIST = old
    if mode == "empty":
        assert status and "no results" in status[-1]
    else:
        assert warnings and ("crashed" in warnings[-1] or "exceeded" in warnings[-1])


def test_real_hermes_route_matrix_labels_oneshot_and_disables_background_subagent_capture():
    """Inspect the actual constructors; do not replace them with injected labels."""
    _external_or_skip()
    init_source = (HERMES / "agent" / "agent_init.py").read_text(encoding="utf-8")
    sync_source = (HERMES / "run_agent.py").read_text(encoding="utf-8")
    oneshot_source = (HERMES / "hermes_cli" / "oneshot.py").read_text(encoding="utf-8")
    background_source = (HERMES / "agent" / "background_review.py").read_text(encoding="utf-8")
    subagent_source = (HERMES / "tools" / "delegate_tool.py").read_text(encoding="utf-8")
    assert '"agent_context": _memory_context' in init_source
    assert '"agent_context": memory_context' in sync_source
    assert 'platform="oneshot"' in oneshot_source
    assert "skip_memory=True" in background_source
    assert 'platform="subagent"' in subagent_source and "skip_memory=True" in subagent_source


def test_capability_inventory_uses_the_same_safe_card_contract_for_hermes_source():
    _external_or_skip()
    inventory = project_context.capability_inventory(HERMES)
    assert inventory["cards"]
    assert inventory["revision"]
    assert all(not item.startswith("/") for card in inventory["cards"] for item in card["files"])
    assert all(family["attempted"] for family in inventory["discovery_coverage"].values())
