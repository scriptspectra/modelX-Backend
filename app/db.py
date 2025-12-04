from sqlmodel import SQLModel, Field, create_engine, UniqueConstraint
from typing import Optional
from .config import POSTGRES_URI

engine = create_engine(POSTGRES_URI, echo=True)

class NewsItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("title", "date", name="uix_title_date"),)  # NEW

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    date: str
    time: str
    source: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    word_count: Optional[int] = None
    language: Optional[str] = "en"
    sentiment: Optional[float] = None

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
