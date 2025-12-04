import os
from dotenv import load_dotenv

load_dotenv()  # Load .env variables

POSTGRES_URI = os.getenv("POSTGRES_URI")
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", 5))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
