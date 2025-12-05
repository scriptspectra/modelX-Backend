from app.stability_store import get_recent_snapshots
import json

if __name__ == '__main__':
    snaps = get_recent_snapshots(limit=5)
    print(json.dumps(snaps, indent=2, ensure_ascii=False))
