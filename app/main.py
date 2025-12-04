from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.db import create_db_and_tables, engine, NewsItem, CurrencyRate
from app.crud import create_news_item
from app.schemas import NewsItemCreate
from app.scraper.news_scraper import run_scraper
from app.config import FRONTEND_ORIGIN
from app.scheduled.currency_scheduler import start_scheduler
import threading
from datetime import datetime, timedelta, date
import os
import json
from app.config import CLAUDE_HAIKU45_ENABLED, DEFAULT_MODEL_NAME

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # initialize model feature flag state (in-memory + optional persistence)
    # persisted file lives in project root 'model_flag.json'
    flag_file = os.path.join(os.path.dirname(__file__), "..", "model_flag.json")
    flag_file = os.path.abspath(flag_file)
    try:
        if os.path.exists(flag_file):
            with open(flag_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                app.state.claude_haiku45_enabled = bool(data.get("claude_haiku45_enabled", CLAUDE_HAIKU45_ENABLED))
        else:
            app.state.claude_haiku45_enabled = bool(CLAUDE_HAIKU45_ENABLED)
    except Exception:
        app.state.claude_haiku45_enabled = bool(CLAUDE_HAIKU45_ENABLED)

# Start scraper in background
@app.on_event("startup")
def start_scraper():
    threading.Thread(target=run_scraper, daemon=True).start()

# API endpoints
@app.post("/news_items/")
def create_item(item: NewsItemCreate):
    return create_news_item(item)

@app.get("/news_items/")
def read_items():
    with Session(engine) as session:
        return session.exec(select(NewsItem)).all()
    

@app.get("/")
def root():
    return {"message": "Backend running"}


# Admin endpoints to read/update the Claude feature flag.
@app.get("/admin/model-flag")
def get_model_flag():
    enabled = bool(getattr(app.state, "claude_haiku45_enabled", CLAUDE_HAIKU45_ENABLED))
    model = "claude-haiku-4.5" if enabled else DEFAULT_MODEL_NAME
    return {"claude_haiku45_enabled": enabled, "selected_model": model}


@app.post("/admin/model-flag")
def set_model_flag(enabled: bool = True):
    # update in-memory flag and persist to model_flag.json
    try:
        app.state.claude_haiku45_enabled = bool(enabled)
        flag_file = os.path.join(os.path.dirname(__file__), "..", "model_flag.json")
        flag_file = os.path.abspath(flag_file)
        with open(flag_file, "w", encoding="utf-8") as f:
            json.dump({"claude_haiku45_enabled": app.state.claude_haiku45_enabled}, f)
        return {"claude_haiku45_enabled": app.state.claude_haiku45_enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/currency_rates/currencies")
def list_unique_currencies():
    # returns a list of unique currency codes present in the DB
    with Session(engine) as session:
        rows = session.exec(select(CurrencyRate.currency)).all()
        # rows may contain duplicates; make unique and sort
        unique = sorted(list({r for r in rows}))
        return {"currencies": unique}

@app.on_event("startup")
def start_currency_scheduler():
    start_scheduler()

@app.get("/currency_rates/")
def get_currency_rates(currency: str = Query(...), time_range: str = Query("30d")):
    # compute start/end as date objects
    end_date = datetime.utcnow().date()
    if time_range.endswith("d"):
        start_date = end_date - timedelta(days=int(time_range[:-1]))
    elif time_range.endswith("y"):
        start_date = end_date - timedelta(days=int(time_range[:-1]) * 365)
    else:
        start_date = end_date - timedelta(days=30)

    def _parse_date_field(val):
        # handle date/datetime objects
        if val is None:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        s = str(val).strip()
        # try common formats
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                continue
        # fallback: split by non-digit and try day/month/year
        try:
            import re
            parts = re.split(r"\D+", s)
            parts = [p for p in parts if p]
            if len(parts) == 3:
                d, m, y = map(int, parts)
                if y < 100:
                    y += 2000
                return date(y, m, d)
        except Exception:
            pass
        return None

    with Session(engine) as session:
        rows = session.exec(select(CurrencyRate).where(CurrencyRate.currency == currency)).all()

    parsed = []
    for r in rows:
        parsed_date = _parse_date_field(getattr(r, "date", None))
        if not parsed_date:
            continue
        if parsed_date < start_date or parsed_date > end_date:
            continue
        parsed.append((parsed_date, r.exchange_rate_LKR))

    parsed.sort(key=lambda x: x[0])
    return [{"date": d.isoformat(), "rate": rate} for d, rate in parsed]