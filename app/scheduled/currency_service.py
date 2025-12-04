import requests
from datetime import date
from sqlmodel import Session
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

        with Session(engine) as session:
            for currency, value in rates.items():
                try:
                    rate_to_lkr = 1 / float(value)  # convert LKR->X to X->LKR

                    entry = CurrencyRate(
                        currency=currency,
                        exchange_rate_LKR=rate_to_lkr,
                        date=today
                    )
                    session.add(entry)
                    session.commit()
                except Exception as e:
                    print(f"Error saving {currency}: {e}")

        print("Currency fetch completed!")

    except Exception as e:
        print(f"Failed to fetch rates: {e}")
