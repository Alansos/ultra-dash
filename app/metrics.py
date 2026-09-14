"""Ultra-specific training metrics. Pure functions: activity dicts in, results out.
No database, no web code here — that keeps every function trivially testable."""

from collections import defaultdict
from datetime import datetime, timedelta


def weekly_load(activities):
    """Group activities by ISO week -> km and hours (time on feet)."""
    weeks = defaultdict(lambda: {"km": 0.0, "hours": 0.0})
    for a in activities:
        dt = datetime.fromisoformat(a["start_time"])
        year, week, _ = dt.isocalendar()
        key = f"{year}-W{week:02d}"
        weeks[key]["km"] += a["distance_km"]
        weeks[key]["hours"] += a["duration_s"] / 3600
    return [
        {"week": k, "km": round(v["km"], 1), "hours": round(v["hours"], 1)}
        for k, v in sorted(weeks.items())
    ]
def detect_back_to_backs(activities, threshold_km=25):
    """Find pairs of long runs on consecutive days — the bread and butter of ultra training."""
    by_date = defaultdict(list)
    for a in activities:
        day = datetime.fromisoformat(a["start_time"]).date()
        by_date[day].append(a)

    long_days = sorted(
        d for d, acts in by_date.items()
        if sum(x["distance_km"] for x in acts) >= threshold_km
    )

    pairs = []
    for i in range(len(long_days) - 1):
        if (long_days[i + 1] - long_days[i]).days == 1:
            pairs.append({
                "day1": str(long_days[i]),
                "day2": str(long_days[i + 1]),
                "day1_km": round(sum(x["distance_km"] for x in by_date[long_days[i]]), 1),
                "day2_km": round(sum(x["distance_km"] for x in by_date[long_days[i + 1]]), 1),
            })
    return pairs
def rolling_7day(activities):
    """For each date, sum km over the trailing 7 days — your workload trend line."""
    by_date = defaultdict(float)
    for a in activities:
        day = datetime.fromisoformat(a["start_time"]).date()
        by_date[day] += a["distance_km"]

    if not by_date:
        return []

    result = []
    day = min(by_date)
    while day <= max(by_date):
        window_km = sum(by_date.get(day - timedelta(days=i), 0.0) for i in range(7))
        result.append({"date": str(day), "km_7day": round(window_km, 1)})
        day += timedelta(days=1)
    return result


def detect_spikes(weekly, threshold_pct=30):
    """Flag any week jumping more than threshold_pct over the previous week.
    Sudden spikes are where most overuse injuries come from."""
    spikes = []
    for prev, curr in zip(weekly, weekly[1:]):
        if prev["km"] == 0:
            continue
        pct = (curr["km"] - prev["km"]) / prev["km"] * 100
        if pct > threshold_pct:
            spikes.append({
                "week": curr["week"],
                "prev_km": prev["km"],
                "km": curr["km"],
                "jump_pct": round(pct, 1),
            })
    return spikes
def taper_score(activities, race_date):
    """Compare the 3 weeks before race_date against the 3 weeks before that.
    A real taper shows a clear volume drop; this returns the % reduction."""
    race_day = datetime.fromisoformat(race_date).date()
    taper_start = race_day - timedelta(weeks=3)
    base_start = race_day - timedelta(weeks=6)

    def km_between(start, end):
        total = 0.0
        for a in activities:
            day = datetime.fromisoformat(a["start_time"]).date()
            if start <= day < end:
                total += a["distance_km"]
        return total

    base_km = km_between(base_start, taper_start)
    taper_km = km_between(taper_start, race_day)
    if base_km == 0:
        return {"base_km": 0.0, "taper_km": round(taper_km, 1), "drop_pct": None}
    drop_pct = (base_km - taper_km) / base_km * 100
    return {
        "base_km": round(base_km, 1),
        "taper_km": round(taper_km, 1),
        "drop_pct": round(drop_pct, 1),
    }
