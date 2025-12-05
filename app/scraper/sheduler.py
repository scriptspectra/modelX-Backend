from apscheduler.schedulers.background import BackgroundScheduler
from .trends_scraper import scrape_all_trends

def start_trends_scheduler():
    scheduler = BackgroundScheduler()
    # Scrape every 10 minutes
    scheduler.add_job(scrape_all_trends, 'interval', minutes=10)
    scheduler.start()
    print("Trends scheduler started (YouTube + Reddit)")
