"""Deterministisches Routing fuer prompt-sensible Entscheidungen."""

DECISIONS = {"bewertung", "rangfolge", "entscheidung"}
HIGH = {"shared", "irreversible", "security", "data_model", "automatic_mutation", "vendor_lock_in"}


def planen(task_type, risk="low", **flags):
    impact = risk == "high" or any(flags.get(name, False) for name in HIGH)
    profile = "strong" if task_type in DECISIONS and impact else "light" if task_type in DECISIONS else "off"
    calls = (2, 6 if profile == "strong" else 2) if profile != "off" else (0, 0)
    return {
        "profile": profile,
        "min_calls": calls[0],
        "max_calls": calls[1],
        "required_checks": [] if profile == "off" else ["baseline", "reversed_order", "evidence"],
        "stop_rule": "same winner with evidence" if profile != "off" else "deterministic evidence",
    }


def pruefen(runs, threshold=.8, high_risk=False):
    if not runs or any(not run.get("winner") or not run.get("evidence") for run in runs):
        return {"status": "human_review", "reason": "missing winner or evidence"}
    winners = [run["winner"] for run in runs]
    counts = {winner: winners.count(winner) for winner in set(winners)}
    top = max(counts.values())
    best = [winner for winner, count in counts.items() if count == top]
    stability = top / len(winners)
    if len(best) > 1:
        status, winner = ("human_review" if high_risk or len(runs) >= 6 else "continue"), None
    else:
        status, winner = ("accept" if stability >= threshold and not (high_risk and len(runs) < 2) else "human_review" if high_risk or len(runs) >= 6 else "continue"), best[0]
    return {"status": status, "winner": winner, "stability": stability, "order_sensitive": len(counts) > 1}
