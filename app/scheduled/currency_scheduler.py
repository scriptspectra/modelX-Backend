from apscheduler.schedulers.background import BackgroundScheduler
from .currency_service import fetch_and_save_rates

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_save_rates, "interval", days=1)
    scheduler.start()
