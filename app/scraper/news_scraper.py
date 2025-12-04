import time
from ..crud import create_news_item
from ..schemas import NewsItemCreate
from .utils import scrape_news
from ..config import SCRAPE_INTERVAL_MINUTES

def run_scraper():
    while True:
        news_list = scrape_news()

        for news in news_list:
            item = NewsItemCreate(**news)
            create_news_item(item)  # upsert handles duplicates

        time.sleep(SCRAPE_INTERVAL_MINUTES * 60)
