from app_net_history import ensure_baseline_net, get_net_for, upsert_net_snapshot


def test_net_history_baseline_and_upsert():
    session_state = {"net_history": []}

    ensure_baseline_net(session_state)
    assert get_net_for(session_state, "2026-01-28") == 2_000_000.0

    upsert_net_snapshot(session_state, "2026-02-01", 123.45)
    assert get_net_for(session_state, "2026-02-01") == 123.45

    upsert_net_snapshot(session_state, "2026-02-01", 999.0)
    assert get_net_for(session_state, "2026-02-01") == 999.0
