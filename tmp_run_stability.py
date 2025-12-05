from app.stability import push_snapshot
import json, os, traceback

if __name__ == '__main__':
    path = os.path.join(os.path.dirname(__file__), 'news_updates.json')
    try:
        res = push_snapshot(path)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception as e:
        traceback.print_exc()
