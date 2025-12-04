# temp_test_insert.py
from app.scraper.adaderana_scraper import scrape_news
from app.schemas import NewsItemCreate
from app.crud import create_news_item

news_list = scrape_news()
for news in news_list[:5]:  # test with first 5 items
    item = NewsItemCreate(**news)
    create_news_item(item)
    print(f"Inserted: {news['title']}")
