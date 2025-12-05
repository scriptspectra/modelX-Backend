from app.scheduled.currency_service import fetch_and_save_rates
from app.db import engine, CurrencyRate
from sqlmodel import Session, select

if __name__ == "__main__":
    fetch_and_save_rates()
    with Session(engine) as s:
        rows = s.exec(select(CurrencyRate).order_by(CurrencyRate.id.desc()).limit(10)).all()
        print([{'id': r.id, 'currency': r.currency, 'date': str(r.date), 'rate': r.exchange_rate_LKR} for r in rows])
