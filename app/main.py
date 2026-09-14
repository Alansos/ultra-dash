from contextlib import asynccontextmanager
from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile

from app.gpx_parser import parse_gpx
from app.db import init_db, insert_activity, get_all_activities

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


@asynccontextmanager
async def lifespan(app):
    init_db()              # create the table if it doesn't exist
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield                  # everything after this runs at shutdown


app = FastAPI(title="Ultra Dash", lifespan=lifespan)


@app.get("/")
def root():
    return {"status": "alive"}


@app.post("/upload")
def upload(file: UploadFile):
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    parsed = parse_gpx(str(dest))
    insert_activity(file.filename, parsed)
    return {"filename": file.filename, **parsed}


@app.get("/activities")
def activities():
    return get_all_activities()
