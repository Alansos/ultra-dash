from app.metrics import detect_back_to_backs, detect_spikes, taper_score, weekly_load


def test_weekly_load_groups_by_week():
    acts = [
        {"start_time": "2026-06-01T08:00:00+00:00", "distance_km": 20.0, "duration_s": 7200, "elev_gain_m": 0},
        {"start_time": "2026-06-03T08:00:00+00:00", "distance_km": 30.0, "duration_s": 10800, "elev_gain_m": 0},
    ]
    weeks = weekly_load(acts)
    assert len(weeks) == 1
    assert weeks[0]["km"] == 50.0
    assert weeks[0]["hours"] == 5.0


def test_back_to_back_detected():
    acts = [
        {"start_time": "2026-06-01T08:00:00+00:00", "distance_km": 30.0, "duration_s": 10800, "elev_gain_m": 0},
        {"start_time": "2026-06-02T08:00:00+00:00", "distance_km": 25.0, "duration_s": 9000, "elev_gain_m": 0},
    ]
    pairs = detect_back_to_backs(acts)
    assert len(pairs) == 1
    assert pairs[0]["day1"] == "2026-06-01"


def test_back_to_back_ignores_short_runs():
    acts = [
        {"start_time": "2026-06-01T08:00:00+00:00", "distance_km": 10.0, "duration_s": 3600, "elev_gain_m": 0},
        {"start_time": "2026-06-02T08:00:00+00:00", "distance_km": 10.0, "duration_s": 3600, "elev_gain_m": 0},
    ]
    assert detect_back_to_backs(acts) == []


def test_spike_flagged():
    weekly = [
        {"week": "2026-W24", "km": 50.0, "hours": 7.0},
        {"week": "2026-W25", "km": 80.0, "hours": 11.0},
    ]
    spikes = detect_spikes(weekly)
    assert len(spikes) == 1
    assert spikes[0]["jump_pct"] == 60.0


def test_taper_drop():
    acts = [
        {"start_time": "2026-05-25T08:00:00+00:00", "distance_km": 100.0, "duration_s": 36000, "elev_gain_m": 0},
        {"start_time": "2026-06-01T08:00:00+00:00", "distance_km": 100.0, "duration_s": 36000, "elev_gain_m": 0},
        {"start_time": "2026-06-08T08:00:00+00:00", "distance_km": 100.0, "duration_s": 36000, "elev_gain_m": 0},
        {"start_time": "2026-06-15T08:00:00+00:00", "distance_km": 60.0, "duration_s": 21600, "elev_gain_m": 0},
        {"start_time": "2026-06-22T08:00:00+00:00", "distance_km": 60.0, "duration_s": 21600, "elev_gain_m": 0},
        {"start_time": "2026-06-29T08:00:00+00:00", "distance_km": 60.0, "duration_s": 21600, "elev_gain_m": 0},
    ]
    result = taper_score(acts, "2026-07-01T00:00:00+00:00")
    assert result["base_km"] == 300.0
    assert result["taper_km"] == 180.0
    assert result["drop_pct"] == 40.0
