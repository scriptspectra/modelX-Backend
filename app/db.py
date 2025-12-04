from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from .config import POSTGRES_URI

engine = create_engine(POSTGRES_URI, echo=True)

class NewsItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # let PostgreSQL auto-generate
    title: str
    description: str
    date: str
    time: str

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
