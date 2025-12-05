import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Any, Dict

# DB helpers
try:
    from app.schemas import NewsItemCreate
    from app.crud import create_news_item
except Exception:
    # when running in isolation the app package may not be importable
    NewsItemCreate = None
    create_news_item = None

# In-memory store for trends
youtube_trends = []
reddit_trends = []

def scrape_youtube_trending():
    """Scrape top 20 YouTube trending videos in Sri Lanka."""
    global youtube_trends
    url = "https://www.youtube.com/feed/trending?gl=LK&hl=en"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        titles = [t.text.strip() for t in soup.select("a#video-title")]
        youtube_trends = titles[:20]
        print("YouTube trending scraped:", len(youtube_trends))
    except Exception as e:
        print("Error scraping YouTube:", e)

def scrape_reddit_trending():
    """Scrape top 20 hot posts from Reddit /r/all."""
    global reddit_trends
    url = "https://www.reddit.com/r/srilanka/hot.json?limit=50"
    headers = {"User-Agent": "TrendScraper"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        reddit_trends = [i["data"]["title"] for i in data["data"]["children"]]
        print("Reddit trending scraped:", len(reddit_trends))
    except Exception as e:
        print("Error scraping Reddit:", e)


def scrape_reddit_and_insert(subreddit: str = "srilanka", limit: int = 20):
    """Fetch top posts from a subreddit via Reddit's JSON endpoint and insert into NewsItem table.

    Fields filled: title, description (selftext or empty), date (YYYY-MM-DD), time (HH:MM),
    source='reddit', category=link_flair_text or subreddit, url=permalink or full link,
    word_count, language='en', sentiment=None
    """
    if NewsItemCreate is None or create_news_item is None:
        print("DB helpers not available; skipping insert")
        return

    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "TrendScraper"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        items = data.get("data", {}).get("children", [])
        inserted = 0
        for node in items:
            d: Dict[str, Any] = node.get("data", {})
            title = d.get("title") or ""
            desc = d.get("selftext") or ""
            created = d.get("created_utc")
            try:
                dt = datetime.utcfromtimestamp(float(created)) if created else datetime.utcnow()
                date = dt.strftime("%Y-%m-%d")
                time = dt.strftime("%H:%M")
            except Exception:
                date = datetime.utcnow().strftime("%Y-%m-%d")
                time = datetime.utcnow().strftime("%H:%M")

            source = "reddit"
            category = d.get("link_flair_text") or subreddit
            permalink = d.get("permalink")
            url_full = f"https://reddit.com{permalink}" if permalink else d.get("url")
            text_for_count = (title + " " + desc).strip()
            wc = len(text_for_count.split()) if text_for_count else 0

            news = NewsItemCreate(
                title=title[:250],
                description=desc[:4000],
                date=date,
                time=time,
                source=source,
                category=category,
                url=url_full,
                word_count=wc,
                language="en",
                sentiment=None,
            )

            try:
                create_news_item(news)
                inserted += 1
            except Exception as e:
                # don't crash; log and continue
                print("Failed to insert news item:", e)

        print(f"Reddit: inserted {inserted}/{len(items)} items from r/{subreddit}")
        return inserted
    except Exception as e:
        print("Error fetching Reddit posts:", e)
        return 0

def scrape_all_trends():
    """Scrape both YouTube and Reddit trends."""
    scrape_youtube_trending()
    scrape_reddit_trending()
