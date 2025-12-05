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
        index_elements=['title', 'description']  # requires UNIQUE(title, description)
    )
    # Attempt to RETURNING the inserted row so we can know if an insert occurred
    try:
        stmt = stmt.returning(NewsItem)
    except Exception:
        # some SQLModel/SQLAlchemy combinations may not support returning on dialect in this way
        pass

    with Session(engine) as session:
        try:
            result = session.exec(stmt)
            # try to fetch a returned row (None if conflict/no-insert)
            inserted = None
            try:
                inserted = result.one_or_none()
            except Exception:
                try:
                    inserted = result.first()
                except Exception:
                    inserted = None
            session.commit()
        except Exception:
            # fallback: execute without returning
            session.execute(stmt)
            session.commit()
            inserted = None

    # If a real insert happened, notify stability module to update real-time state
    if inserted is not None:
        try:
            from .stability import push_items

            item_dict = {
                "title": item.title,
                "description": item.description,
                "date": item.date,
                "time": item.time,
                "source": item.source,
                "category": item.category,
                "url": item.url,
                "word_count": item.word_count,
                "language": item.language,
                "sentiment": item.sentiment,
            }
            try:
                push_items([item_dict])
            except Exception:
                # don't let realtime push failures break insertion
                pass
        except Exception:
            pass

    return item  # return the input object (optional)
