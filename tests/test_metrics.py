from datetime import date 

from app.metrics import acute_chronic_ratio, detect_back_to_backs, detect_spikes, overtraining_alerts, taper_guidance, taper_score, weekly_load


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

def test_acwr_high_alert():
    # "Today" 2026-07-01. Four Thursdays, one per week: 50, 50, 50, 100 km.
    # Acute (Jun 25-Jul 1): 100. Chronic (28 days / 4): 62.5. ACWR = 1.6.
    acts = [_run("2026-06-04", 50.0), _run("2026-06-11", 50.0),
            _run("2026-06-18", 50.0), _run("2026-06-25", 100.0)]
    assert acute_chronic_ratio(acts, today=date(2026, 7, 1)) == 1.6
    alerts = overtraining_alerts(acts, today=date(2026, 7, 1))
    assert any(a["type"] == "acwr" and a["severity"] == "high" for a in alerts)


def test_acwr_medium_alert():
    # Same shape, last week 85 km: acute 85, chronic 58.75, ACWR = 1.45.
    acts = [_run("2026-06-04", 50.0), _run("2026-06-11", 50.0),
            _run("2026-06-18", 50.0), _run("2026-06-25", 85.0)]
    assert acute_chronic_ratio(acts, today=date(2026, 7, 1)) == 1.45
    alerts = overtraining_alerts(acts, today=date(2026, 7, 1))
    assert any(a["type"] == "acwr" and a["severity"] == "medium" for a in alerts)


def test_spike_alert_without_acwr():
    # Jump in week 2 (50 -> 80 km), then even weeks after: ACWR stays ~0.87.
    acts = [_run("2026-06-04", 50.0), _run("2026-06-11", 80.0),
            _run("2026-06-18", 50.0), _run("2026-06-25", 50.0)]
    alerts = overtraining_alerts(acts, today=date(2026, 7, 1))
    assert len(alerts) == 1
    assert alerts[0]["type"] == "spike"
    assert alerts[0]["severity"] == "high"


def test_no_alerts_on_steady_load():
    acts = [_run("2026-06-04", 50.0), _run("2026-06-11", 50.0),
            _run("2026-06-18", 50.0), _run("2026-06-25", 50.0)]
    assert acute_chronic_ratio(acts, today=date(2026, 7, 1)) == 1.0
    assert overtraining_alerts(acts, today=date(2026, 7, 1)) == []


def test_no_alerts_without_data():
    assert acute_chronic_ratio([], today=date(2026, 7, 1)) is None
    assert overtraining_alerts([], today=date(2026, 7, 1)) == []
