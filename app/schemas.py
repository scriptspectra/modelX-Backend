from pydantic import BaseModel
from typing import Optional

class NewsItemCreate(BaseModel):
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
