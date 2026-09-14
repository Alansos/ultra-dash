# Ultra Dash

Training-load analytics for ultrarunners. I run ultras, and generic fitness apps don't answer the questions I actually ask: am I stacking back-to-back long runs? Is my workload spiking? Am I really tapering? So I built the tool.

## Stack

Python, FastAPI, SQLite (stdlib `sqlite3`, no ORM), Jinja2, Chart.js, gpxpy, pytest.

## Architecture
browser → FastAPI (app/main.py) → metrics engine (app/metrics.py) → SQLite
                                     ↑
                        pure functions, fully tested


## Metrics

- **Weekly load** — km and time-on-feet per ISO week
- **7-day rolling km** — trailing workload trend
- **Spike flags** — weeks jumping >30% over the previous week
- **Back-to-back detection** — pairs of 25+ km runs on consecutive days (configurable threshold)
- **Taper score** — 3-week pre-race volume vs. the 3 weeks before that

## Run it locally
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload


Open http://localhost:8000 and upload a `.gpx` file.

## Tests
python -m pytest

