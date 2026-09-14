from contextlib import asynccontextmanager
from pathlib import Path
import shutil

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.gpx_parser import parse_gpx
from app.db import init_db, insert_activity, get_all_activities
from app.metrics import weekly_load, rolling_7day, detect_spikes, detect_back_to_backs

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")


@asynccontextmanager
async def lifespan(app):
    init_db()
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="Ultra Dash", lifespan=lifespan)


@app.get("/")
def dashboard(request: Request):
    acts = get_all_activities()
    weekly = weekly_load(acts)
    return templates.TemplateResponse(request, "index.html", {
    "weekly": weekly,
    "rolling": rolling_7day(acts),
    "spikes": detect_spikes(weekly),
    "back_to_backs": detect_back_to_backs(acts),
    "activities": acts[-10:][::-1],
})



@app.post("/upload")
def upload(file: UploadFile):
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    parsed = parse_gpx(str(dest))
    insert_activity(file.filename, parsed)
    return RedirectResponse("/", status_code=303)


@app.get("/activities")
def activities():
    return get_all_activities()


@app.get("/api/weekly")
def api_weekly():
    acts = get_all_activities()
    weekly = weekly_load(acts)
    return {
        "weekly": weekly,
        "spikes": detect_spikes(weekly),
        "back_to_backs": detect_back_to_backs(acts),
    }
