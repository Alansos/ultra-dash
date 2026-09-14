"""Parse GPX run files into plain summary dicts. No database, no web — just parsing."""

import gpxpy


def parse_gpx(path):
    with open(path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    # Total distance in meters, converted to km
    distance_km = gpx.length_2d() / 1000

    # Walk every point once, collecting start/end time and elevation gain
    start_time = None
    end_time = None
    elev_gain_m = 0.0
    prev_ele = None

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.time:
                    if start_time is None or point.time < start_time:
                        start_time = point.time
                    if end_time is None or point.time > end_time:
                        end_time = point.time
                if point.elevation is not None:
                    if prev_ele is not None and point.elevation > prev_ele:
                        elev_gain_m += point.elevation - prev_ele
                    prev_ele = point.elevation

    duration_s = (end_time - start_time).total_seconds() if start_time and end_time else 0

    return {
        "distance_km": round(distance_km, 2),
        "duration_s": duration_s,
        "elev_gain_m": round(elev_gain_m, 1),
        "start_time": start_time.isoformat() if start_time else None,
    }
