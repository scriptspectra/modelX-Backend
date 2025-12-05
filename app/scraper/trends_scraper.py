import requests
from bs4 import BeautifulSoup

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
    url = "https://www.reddit.com/r/srilanka/hot.json?limit=20"
    headers = {"User-Agent": "TrendScraper"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        reddit_trends = [i["data"]["title"] for i in data["data"]["children"]]
        print("Reddit trending scraped:", len(reddit_trends))
    except Exception as e:
        print("Error scraping Reddit:", e)

def scrape_all_trends():
    """Scrape both YouTube and Reddit trends."""
    scrape_youtube_trending()
    scrape_reddit_trending()
