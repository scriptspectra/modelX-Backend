from fastapi import APIRouter, Query
from sqlmodel import select, Session
from typing import List
from app.db import CurrencyRate, engine

router = APIRouter()

@router.get("/currency-data")
def get_currency_data(
    currencies: List[str] = Query(...), 
    start_date: str = Query(...), 
    end_date: str = Query(...)
):
    """
    Returns currency rates from start_date to end_date for selected currencies.
    """
    with Session(engine) as session:
        stmt = select(CurrencyRate).where(
            CurrencyRate.currency.in_(currencies),
            CurrencyRate.date >= start_date,
            CurrencyRate.date <= end_date
        ).order_by(CurrencyRate.date)
        results = session.exec(stmt).all()

    # Convert to JSON grouped by date
    data = {}
    for r in results:
        if r.date not in data:
            data[r.date] = {"date": r.date}
        data[r.date][r.currency] = r.exchange_rate_LKR

    return list(data.values())
