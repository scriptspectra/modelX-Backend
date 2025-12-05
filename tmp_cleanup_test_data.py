from sqlmodel import Session, select
from app.db import engine, NewsItem, StabilitySnapshot

TEST_TITLE = "TEST ITEM FOR REALTIME"
TEST_SOURCE = "unittest"
KEYWORDS_TO_MATCH = {"test", "realtime", "trigger", "updates"}

if __name__ == '__main__':
    removed_news = 0
    removed_snaps = 0
    with Session(engine) as session:
        # Delete test news items by title or source
        news = session.exec(select(NewsItem).where(NewsItem.title == TEST_TITLE)).all()
        for n in news:
            session.delete(n)
            removed_news += 1
        # Also delete any news items with source matching TEST_SOURCE
        news_src = session.exec(select(NewsItem).where(NewsItem.source == TEST_SOURCE)).all()
        for n in news_src:
            session.delete(n)
            removed_news += 1

        # Find snapshots and delete those that appear to contain test keywords
        snaps = session.exec(select(StabilitySnapshot)).all()
        for s in snaps:
            try:
                kws = s.top_keywords or []
                if any(k in kws for k in KEYWORDS_TO_MATCH):
                    session.delete(s)
                    removed_snaps += 1
            except Exception:
                continue

        session.commit()

    print(f"Removed news items: {removed_news}")
    print(f"Removed stability snapshots: {removed_snaps}")
