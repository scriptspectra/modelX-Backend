from sqlmodel import SQLModel, Field, create_engine, UniqueConstraint
from typing import Optional
from .config import POSTGRES_URI
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy import JSON as SA_JSON

engine = create_engine(POSTGRES_URI, echo=True)

class NewsItem(SQLModel, table=True):
    # Make title+description unique instead of title+date
    __table_args__ = (UniqueConstraint("title", "description", name="uix_title_description"),)

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

class CurrencyRate(SQLModel, table=True):
    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint("currency", "date", name="uix_currency_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    date: str                   # real DATE type (not string)
    currency: str                # e.g., "USD"
    exchange_rate_LKR: float         # e.g., 324.15

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


class StabilitySnapshot(SQLModel, table=True):
    """Persisted stability snapshot for historical smoothing and analysis."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    composite_score: float = Field(default=0.0)
    category_scores: dict = Field(sa_column=Column(SA_JSON), default={})
    top_keywords: list = Field(sa_column=Column(SA_JSON), default=[])
    total_items: int = Field(default=0)
    last_snapshot_path: Optional[str] = None
