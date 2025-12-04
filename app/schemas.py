from pydantic import BaseModel

class NewsItemCreate(BaseModel):
    title: str
    description: str
    date: str
    time: str
