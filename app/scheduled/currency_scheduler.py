from apscheduler.schedulers.background import BackgroundScheduler
from .currency_service import fetch_and_save_rates
from .news_exporter import export_new_news_to_json

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule job to run every day at 00:00 (start of day)
    scheduler.add_job(fetch_and_save_rates, 'cron', hour=0, minute=0)
    # Schedule news exporter to run every 5 minutes
    scheduler.add_job(export_new_news_to_json, 'interval', minutes=5)
    scheduler.start()
