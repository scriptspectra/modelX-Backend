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
