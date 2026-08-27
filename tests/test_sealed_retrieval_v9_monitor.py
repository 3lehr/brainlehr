from messungen.sealed_retrieval_v9_launcher import abort_reason


def test_v9_monitor_accepts_v8_compressor_delta_but_rejects_critical_signals():
    baseline = {"free_pct": 92, "swapouts": 0, "throttled": 0, "rss_kb": 821072}
    assert abort_reason({"free_pct": 91, "swapouts": 0, "throttled": 0, "rss_kb": 821072}, baseline) is None
    assert abort_reason({"free_pct": 24, "swapouts": 0, "throttled": 0, "rss_kb": 1}, baseline) == "critical_free_memory"
    assert abort_reason({"free_pct": 90, "swapouts": 1, "throttled": 0, "rss_kb": 1}, baseline) == "swapout_increase"
    assert abort_reason({"free_pct": 90, "swapouts": 0, "throttled": 1, "rss_kb": 1}, baseline) == "throttled_pages"
    assert abort_reason({"free_pct": 90, "swapouts": 0, "throttled": 0, "rss_kb": 8 * 1024 * 1024 + 1}, baseline) == "rss_over_8gb"
