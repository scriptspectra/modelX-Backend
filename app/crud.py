from sqlmodel import Session
from sqlalchemy.dialects.postgresql import insert
from .db import engine, NewsItem
from .schemas import NewsItemCreate

def create_news_item(item: NewsItemCreate):
    stmt = insert(NewsItem).values(
        title=item.title,
        description=item.description,
        date=item.date,
        time=item.time,
        source=item.source,
        category=item.category,
        url=item.url,
        word_count=item.word_count,
        language=item.language,
        sentiment=item.sentiment
    ).on_conflict_do_nothing(
        index_elements=['title', 'date']  # requires UNIQUE(title, date)
    )

    with Session(engine) as session:
        session.execute(stmt)
        session.commit()
    return item  # return the input object (optional)
