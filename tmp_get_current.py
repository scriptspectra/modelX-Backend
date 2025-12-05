from app.stability import get_current_snapshot
import json

if __name__ == '__main__':
    print(json.dumps(get_current_snapshot(), indent=2, ensure_ascii=False))
