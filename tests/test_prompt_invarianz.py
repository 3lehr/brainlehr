from kern.prompt_invarianz import planen, pruefen


def test_routing_and_conflict():
    assert planen("test")["profile"] == "off"
    assert planen("rangfolge")["profile"] == "light"
    assert planen("rangfolge", security=True)["profile"] == "strong"
    conflict = pruefen([{"winner":"a","evidence":1},{"winner":"b","evidence":1}])
    assert conflict["status"] == "continue" and conflict["winner"] is None


def test_evidence_gate_and_stability():
    assert pruefen([{"winner":"a"}])["status"] == "human_review"
    stable = pruefen([{"winner":"a","evidence":"x"},{"winner":"a","evidence":"y"}], high_risk=True)
    assert stable == {"status":"accept","winner":"a","stability":1.0,
                      "order_sensitive":False,"recommendation":True}
