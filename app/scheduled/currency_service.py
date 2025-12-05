import requests
from datetime import date
from sqlmodel import Session, select
from ..db import engine, CurrencyRate
from ..config import FOREX_CURRENCY_API_KEY

URL = f"https://api.fastforex.io/fetch-all?from=LKR&api_key={FOREX_CURRENCY_API_KEY}"

def fetch_and_save_rates():
    print("Running daily currency fetch...")

    try:
        response = requests.get(URL)
        data = response.json()
        rates = data.get("results", {})

        today = date.today()
        today_str = today.isoformat()

        # Use a check-before-insert / update to make this idempotent
        # Store and compare the date as an ISO string to match existing DB column type
        with Session(engine) as session:
            for currency, value in rates.items():
                try:
                    rate_to_lkr = 1 / float(value)  # convert LKR->X to X->LKR

                    # Check existing record for same currency+date
                    existing = session.exec(
                        select(CurrencyRate).where(
                            CurrencyRate.currency == currency,
                            CurrencyRate.date == today_str,
                        )
                    ).one_or_none()

                    if existing:
                        # Update existing rate if changed
                        if existing.exchange_rate_LKR != rate_to_lkr:
                            existing.exchange_rate_LKR = rate_to_lkr
                            session.add(existing)
                            session.commit()
                    else:
                        entry = CurrencyRate(
                            currency=currency,
                            exchange_rate_LKR=rate_to_lkr,
                            date=today_str,
                        )
                        session.add(entry)
                        session.commit()

                except Exception as e:
                    # Rollback current transaction and continue with others
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    print(f"Error saving {currency}: {e}")

        print("Currency fetch completed!")

    except Exception as e:
        print(f"Failed to fetch rates: {e}")
