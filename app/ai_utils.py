import os
import json
from typing import Literal
from .config import CLAUDE_HAIKU45_ENABLED, DEFAULT_MODEL_NAME

MODEL_FLAG_FILE = os.path.join(os.path.dirname(__file__), "..", "model_flag.json")

def get_selected_model() -> str:
    """Return the model name to use based on runtime flag (persisted file) or env var.

    Order of precedence:
    1. Persisted flag in `model_flag.json` (if present)
    2. Environment variable `CLAUDE_HAIKU45_ENABLED`
    3. Default model from `DEFAULT_MODEL_NAME`
    """
    try:
        if os.path.exists(MODEL_FLAG_FILE):
            with open(MODEL_FLAG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                enabled = bool(data.get("claude_haiku45_enabled", CLAUDE_HAIKU45_ENABLED))
        else:
            enabled = bool(CLAUDE_HAIKU45_ENABLED)
    except Exception:
        enabled = bool(CLAUDE_HAIKU45_ENABLED)

    return "claude-haiku-4.5" if enabled else DEFAULT_MODEL_NAME
