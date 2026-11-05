from contextlib import asynccontextmanager
from pathlib import Path
import shutil

import os
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import create_user, get_user_by_email, get_user_by_id, verify_password
from app.db import init_db, insert_activity, get_all_activities, get_activities_for_user 
from app.metrics import weekly_load, rolling_7day, detect_spikes, detect_back_to_backs

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")


@asynccontextmanager
async def lifespan(app):
    init_db()
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="Ultra Dash", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dev-only-change-me"))

def current_user(request: Request):
    """Return the logged-in user, or None."""
    user_id = request.session.get("user_id")
    return get_user_by_id(user_id) if user_id else None


@app.get("/")
def dashboard(request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    acts = get_activities_for_user(user["id"])
    weekly = weekly_load(acts)
    return templates.TemplateResponse(request, "index.html", {
    "user": user,
    "weekly": weekly,
    "rolling": rolling_7day(acts),
    "spikes": detect_spikes(weekly),
    "back_to_backs": detect_back_to_backs(acts),
    "activities": acts[-10:][::-1],
})




@app.post("/upload")
def upload(request: Request, file: UploadFile):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    parsed = parse_gpx(str(dest))
    insert_activity(file.filename, parsed, user["id"])
    return RedirectResponse("/", status_code=303)



@app.get("/activities")
def activities(request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return get_activities_for_user(user["id"])


@app.get("/api/weekly")
def api_weekly(request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    acts = get_activities_for_user(user["id"])
    weekly = weekly_load(acts)
    return {
        "weekly": weekly,
        "spikes": detect_spikes(weekly),
        "back_to_backs": detect_back_to_backs(acts),
    }




@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


@app.post("/register")
def register(request: Request, email: str = Form(...), password: str = Form(...)):
    user = create_user(email, password)
    if user is None:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "That email is already registered."}, status_code=400,
        )
    request.session["user_id"] = user["id"]
    return RedirectResponse("/", status_code=303)


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if user is None or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Invalid email or password."}, status_code=400,
        )
    request.session["user_id"] = user["id"]
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
