from apscheduler.schedulers.background import BackgroundScheduler
from .currency_service import fetch_and_save_rates

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule job to run every day at 00:00 (start of day)
    scheduler.add_job(fetch_and_save_rates, 'cron', hour=0, minute=0)
    scheduler.start()
