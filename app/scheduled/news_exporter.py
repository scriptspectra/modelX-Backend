import json
from pathlib import Path
from sqlmodel import Session, select
from ..db import engine, NewsItem

# State file keeps track of the last exported max `id` so we only export new rows
STATE_PATH = Path(__file__).parent / "news_exporter_state.json"
# Output file (single JSON file in the backend folder)
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "news_updates.json"


def _load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"last_max_id": 0}
    return {"last_max_id": 0}


def _save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")


def export_new_news_to_json():
    """Export newly added NewsItem rows (since last export) to a single JSON file.

    The file `backend/news_updates.json` will be overwritten every run and will
    contain an array of the newly added rows since the last successful export.
    """
    try:
        state = _load_state()
        last_max_id = int(state.get("last_max_id", 0) or 0)

        with Session(engine) as session:
            stmt = select(NewsItem).where(NewsItem.id > last_max_id).order_by(NewsItem.id)
            results = session.exec(stmt).all()

        items = [r.dict() for r in results]

        # Ensure parent directory exists
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Write the newly added items (empty array if none)
        OUTPUT_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        if items:
            # update last_max_id to the last exported id
            state["last_max_id"] = items[-1]["id"]
            _save_state(state)

        print(f"news_exporter: exported {len(items)} new items to {OUTPUT_PATH}")
    except Exception as e:
        print(f"news_exporter: error exporting news: {e}")
