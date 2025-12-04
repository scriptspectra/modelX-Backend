import time
from ..crud import create_news_item
from ..schemas import NewsItemCreate
from .adaderana_scraper import scrape_news  # <- Use the website-specific scraper
from ..config import SCRAPE_INTERVAL_MINUTES

def run_scraper():
    """Continuously scrape news and insert into DB every SCRAPE_INTERVAL_MINUTES."""
    while True:
        try:
            news_list = scrape_news()  # scrape all categories
            for news in news_list:
                # Create Pydantic model to validate & insert
                item = NewsItemCreate(**news)
                create_news_item(item)  # upsert handles duplicates
        except Exception as e:
            print(f"Error while scraping or inserting news: {e}")

        # Wait before next scraping cycle
        time.sleep(SCRAPE_INTERVAL_MINUTES * 60)
