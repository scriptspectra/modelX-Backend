from app.schemas import NewsItemCreate
from app.crud import create_news_item

if __name__ == '__main__':
    itm = NewsItemCreate(
        title="TEST ITEM FOR REALTIME",
        description="This is a test item to trigger realtime updates.",
        date="2025-12-05",
        time="21:00",
        source="unittest",
        category="Test",
        url="http://example.test/realtime",
        word_count=6,
        language="en",
        sentiment=0.1
    )
    create_news_item(itm)
    print("create_news_item called")
