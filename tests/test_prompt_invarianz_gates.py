from kern.prompt_invarianz import pruefen
from pathlib import Path

def test_canary_and_memory_gate():
    canary={"question":"2+2","expected":"4"}; assert canary["expected"]=="4"
    assert pruefen([{"winner":"a","evidence":1},{"winner":"a","evidence":1}])["recommendation"]

def test_three_agents_share_rules():
    root=Path(__file__).parents[1]/"auszug-offen/prompts"
    texts=[(root/f"{n}.md").read_text() for n in ("CLAUDE","HERMES","CHATGPT")]
    assert all("Expertenrolle ersetzt nie" in text and "frühere Gewinner keine Evidenz" in text for text in texts)
