from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.db import create_db_and_tables, engine, NewsItem
from app.crud import create_news_item
from app.schemas import NewsItemCreate
from app.scraper.news_scraper import run_scraper
from app.config import FRONTEND_ORIGIN
import threading

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
