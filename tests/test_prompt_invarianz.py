from kern.prompt_invarianz import planen, pruefen


def test_routing_evidence_and_tie():
    assert planen("test")["profile"] == "off"
    assert planen("rangfolge")["profile"] == "light"
    assert planen("rangfolge", security=True)["profile"] == "strong"
    assert pruefen([{"winner": "a"}])["status"] == "human_review"
    tie = pruefen([{"winner": "a", "evidence": 1}, {"winner": "b", "evidence": 1}])
    assert tie["status"] == "continue" and tie["winner"] is None


def test_winner_change_never_recommends():
    result = pruefen([{"winner": "a", "evidence": 1}, {"winner": "b", "evidence": 1}])
    assert result["recommendation"] is False and result["order_sensitive"]
