from contextlib import asynccontextmanager
from pathlib import Path
import shutil

import os
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from httpx import request
from starlette.middleware.sessions import SessionMiddleware

from app.auth import create_user, get_or_create_share_token, get_user_by_email, get_user_by_id, get_user_by_share_token, disable_sharing, verify_password, set_race_date
from app.db import init_db, insert_activity, get_all_activities, get_activities_for_user 
from app.metrics import weekly_load, rolling_7day, detect_spikes, detect_back_to_backs, taper_guidance, overtraining_alerts

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
    race_date = user.get("race_date")
    guidance = taper_guidance(acts, race_date) if race_date else None
    share_token = user.get("share_token")
    share_url = f"{request.base_url}share/{share_token}" if share_token else None

    return templates.TemplateResponse(request, "index.html", {
    "user": user,
    "weekly": weekly,
    "rolling": rolling_7day(acts),
    "spikes": detect_spikes(weekly),
    "back_to_backs": detect_back_to_backs(acts),
    "activities": acts[-10:][::-1],
    "race_date": race_date,
    "guidance": guidance,
    "alerts": overtraining_alerts(acts),
    "share_url": share_url,

})

@app.post("/race-date")
def save_race_date(request: Request, race_date: str = Form("")):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    try:
        set_race_date(user["id"], race_date)
    except ValueError:
        pass  # bad date from the form; leave the saved date unchanged
    return RedirectResponse("/", status_code=303)



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
    race_date = user.get("race_date")
    guidance = taper_guidance(acts, race_date) if race_date else None

    return {
        "weekly": weekly,
        "spikes": detect_spikes(weekly),
        "back_to_backs": detect_back_to_backs(acts),
    }


@app.get("/share/{token}")
def shared_profile(request: Request, token: str):
    """Public read-only training profile. No login needed, no email shown,
    nothing editable — the user object is never passed to the template."""
    user = get_user_by_share_token(token)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    acts = get_activities_for_user(user["id"])
    weekly = weekly_load(acts)
    race_date = user.get("race_date")
    guidance = taper_guidance(acts, race_date) if race_date else None

    return templates.TemplateResponse(request, "share.html", {
        "weekly": weekly,
        "rolling": rolling_7day(acts),
        "spikes": detect_spikes(weekly),
        "back_to_backs": detect_back_to_backs(acts),
        "activities": acts[-10:][::-1],
        "race_date": race_date,
        "guidance": guidance,
        "alerts": overtraining_alerts(acts),
    })


@app.post("/share/enable")
def enable_sharing(request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    get_or_create_share_token(user["id"])
    return RedirectResponse("/", status_code=303)


@app.post("/share/disable")
def turn_off_sharing(request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    disable_sharing(user["id"])
    return RedirectResponse("/", status_code=303)


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
