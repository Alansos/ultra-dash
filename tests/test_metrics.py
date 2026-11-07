from datetime import date 

from app.metrics import detect_back_to_backs, detect_spikes, taper_guidance, taper_score, weekly_load


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
def _run(day, km):
    return {"start_time": f"{day}T08:00:00+00:00", "distance_km": km,
            "duration_s": 3600, "elev_gain_m": 0}


def test_guidance_build_phase():
    # Race 2026-07-01, "today" 2026-05-20: 42 days out, too early to taper.
    result = taper_guidance([], "2026-07-01", today=date(2026, 5, 20))
    assert result["status"] == "build"
    assert result["days_to_race"] == 42


def test_guidance_race_done():
    result = taper_guidance([], "2026-07-01", today=date(2026, 7, 2))
    assert result["status"] == "done"
    assert result["days_to_race"] == -1


def test_guidance_on_track():
    # Race 2026-07-01, "today" 2026-06-19: 12 days out, 10 taper days elapsed.
    # Base first 10 days: 100 km. Taper first 10 days: 50 km -> 50% drop.
    acts = [_run("2026-05-20", 100.0), _run("2026-06-10", 50.0)]
    result = taper_guidance(acts, "2026-07-01", today=date(2026, 6, 19))
    assert result["status"] == "on_track"
    assert result["drop_pct"] == 50.0
    assert result["days_to_race"] == 12


def test_guidance_cut_more():
    acts = [_run("2026-05-20", 100.0), _run("2026-06-10", 80.0)]
    result = taper_guidance(acts, "2026-07-01", today=date(2026, 6, 19))
    assert result["status"] == "cut_more"
    assert result["drop_pct"] == 20.0


def test_guidance_above_build_block():
    acts = [_run("2026-05-20", 100.0), _run("2026-06-10", 120.0)]
    result = taper_guidance(acts, "2026-07-01", today=date(2026, 6, 19))
    assert result["status"] == "cut_more"
    assert result["drop_pct"] == -20.0
    assert "ABOVE" in result["message"]


def test_guidance_no_base_data():
    acts = [_run("2026-06-10", 50.0)]
    result = taper_guidance(acts, "2026-07-01", today=date(2026, 6, 19))
    assert result["status"] == "nodata"
    assert result["drop_pct"] is None
