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
from app.stability import push_snapshot, get_buffer_status, load_latest_snapshot_from_db, get_current_snapshot

app = FastAPI()

# CORS for frontend
FRONTEND_ORIGINS = [
    "http://localhost:3000",                       # local dev
    "https://model-x-frontend-nmva.vercel.app"    # production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Restore previous stability state from DB (if any) so smoothing survives restarts
    try:
        load_latest_snapshot_from_db()
    except Exception:
        pass
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


@app.get("/currency_rates/insights")
def get_currency_insights():
    """
    Compute and return:
    1. USD to LKR (today's latest rate or most recent available)
    2. Fastest gaining currency (% change in last 7 days)
    3. Fastest losing currency (% change in last 7 days)
    4. Most volatile currency (std dev in last 7 days)
    """
    def _parse_date_field(val):
        """Parse date from various formats"""
        if val is None:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        s = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                continue
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

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)

    with Session(engine) as session:
        # Get all rates in last 7 days (no date filtering yet, we'll parse)
        week_rates = session.exec(select(CurrencyRate)).all()

    # Parse and filter: only keep rates in the 7-day window
    parsed_rates = []
    for rate in week_rates:
        parsed_date = _parse_date_field(rate.date)
        if not parsed_date:
            continue
        if parsed_date < week_ago or parsed_date > today:
            continue
        parsed_rates.append((parsed_date, rate.currency, rate.exchange_rate_LKR))

    # Build map: currency -> sorted list of (date, rate) tuples
    currency_series: dict = {}
    for parsed_date, cur, rate_val in parsed_rates:
        if cur not in currency_series:
            currency_series[cur] = []
        currency_series[cur].append((parsed_date, rate_val))

    # Sort each currency's rates by date
    for cur in currency_series:
        currency_series[cur].sort(key=lambda x: x[0])

    # Find most recent date with USD data (or use today)
    usd_rates = currency_series.get("USD", [])
    usd_rate = None
    if usd_rates:
        usd_rate = usd_rates[-1][1]  # most recent
    
    usd_value = f"{usd_rate:.2f}" if usd_rate else "N/A"
    usd_change = "0.0%"
    if usd_rate and len(usd_rates) > 1:
        old_rate = usd_rates[0][1]
        if old_rate != 0:
            change_pct = ((usd_rate - old_rate) / old_rate) * 100
            usd_change = f"{change_pct:+.2f}%"

    # Calculate % change and volatility
    metrics = {}
    for cur, rates in currency_series.items():
        if len(rates) < 2:
            continue
        first_val = rates[0][1]
        last_val = rates[-1][1]
        pct_change = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
        
        # volatility: standard deviation
        values = [r[1] for r in rates]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        volatility = variance ** 0.5
        
        metrics[cur] = {
            "pct_change": pct_change,
            "volatility": volatility,
            "current_rate": last_val
        }

    # Find fastest gainer, loser, and most volatile
    gainer = max(metrics.items(), key=lambda x: x[1]["pct_change"], default=(None, {}))
    loser = min(metrics.items(), key=lambda x: x[1]["pct_change"], default=(None, {}))
    volatile = max(metrics.items(), key=lambda x: x[1]["volatility"], default=(None, {}))

    return {
        "usd_to_lkr": {
            "value": usd_value,
            "change": usd_change,
            "is_positive": float(usd_change.rstrip('%').replace('+', '')) >= 0 if usd_change != "0.0%" else False
        },
        "fastest_gainer": {
            "currency": gainer[0] or "N/A",
            "change": f"{gainer[1].get('pct_change', 0):+.2f}%",
            "rate": f"{gainer[1].get('current_rate', 0):.2f}"
        },
        "fastest_loser": {
            "currency": loser[0] or "N/A",
            "change": f"{loser[1].get('pct_change', 0):+.2f}%",
            "rate": f"{loser[1].get('current_rate', 0):.2f}"
        },
        "most_volatile": {
            "currency": volatile[0] or "N/A",
            "volatility": f"{volatile[1].get('volatility', 0):.4f}",
            "rate": f"{volatile[1].get('current_rate', 0):.2f}"
        }
    }

from app.scraper.trends_scraper import youtube_trends, reddit_trends
from app.scraper.sheduler import start_trends_scheduler
from app.stability import push_snapshot, get_buffer_status

@app.on_event("startup")
def start_trends_scraper():
    # Start background trends scraper
    start_trends_scheduler()

# API endpoints
@app.get("/trends/youtube")
def get_youtube_trends():
    return {"youtube_trends": youtube_trends}

@app.get("/trends/reddit")
def get_reddit_trends():
    return {"reddit_trends": reddit_trends}

@app.get("/trends/all")
def get_all_trends():
    return {
        "youtube_trends": youtube_trends,
        "reddit_trends": reddit_trends
    }


@app.post('/stability/push_snapshot')
def stability_push_snapshot(file_path: str):
    """Push a snapshot JSON file into the 60-minute rolling buffer and return updated heuristic scores.

    Body/form parameter: `file_path` - path to the JSON snapshot file (can be absolute or relative).
    """
    try:
        res = push_snapshot(file_path)
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/stability/status')
def stability_status():
    return get_buffer_status()


@app.get('/stability/current')
def stability_current():
    """Return current smoothed stability snapshot for frontend consumption."""
    try:
        return get_current_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))