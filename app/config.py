import os
from dotenv import load_dotenv

load_dotenv()  # Load .env variables

POSTGRES_URI = os.getenv("POSTGRES_URI")
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", 5))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

FOREX_CURRENCY_API_KEY=os.getenv("FOREX_CURRENCY_API_KEY")

# Feature flag to enable Claude Haiku 4.5 for all clients by default.
# Can be overridden at runtime via the admin endpoint added in `main.py`.
CLAUDE_HAIKU45_ENABLED = os.getenv("CLAUDE_HAIKU45_ENABLED", "false").lower() in ("1", "true", "yes")

# Default model name used when the feature flag is off (services can import and use this helper)
DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-4o")