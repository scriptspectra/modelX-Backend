import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from langdetect import detect
from datetime import datetime
from urllib.parse import urljoin

BASE_URLS = {
    "tech": "https://www.adaderana.lk/moretechnews.php",
    "entertainment": "https://www.adaderana.lk/more-entertainment-news.php",
    "hot": "https://www.adaderana.lk/hot-news/"
}

def compute_word_count(text: str) -> int:
    return len(text.split())

def compute_sentiment(text: str) -> float:
    try:
        return TextBlob(text).sentiment.polarity
    except:
        return 0.0

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def parse_datetime(date_text: str):
    try:
        date_text = " ".join(date_text.split())  # normalize spaces
        dt = datetime.strptime(date_text, "%B %d, %Y %I:%M %p")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception as e:
        now = datetime.now()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

def scrape_adaderana(category: str, pages=1):
    news_items = []
    base_url = BASE_URLS[category]

    for page in range(1, pages + 1):
        url = f"{base_url}?pageno={page}" if category == "hot" else base_url
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        # --- Hot News ---
        if category == "hot":
            articles = soup.select("div.news-story div.story-text")
            for article in articles:
                title_tag = article.select_one("h2.hidden-xs a") or article.select_one("h2.visible-xs a") or article.select_one("h2 a")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                news_url = title_tag['href']
                description = article.select_one("p").get_text(strip=True) if article.select_one("p") else title

                date_span = article.select_one("div.comments span")
                date_str, time_str = parse_datetime(date_span.get_text(strip=True)) if date_span else parse_datetime("")

                comments_tag = article.select_one("div.comments a")
                comments = comments_tag.get_text(strip=True) if comments_tag else "(0)Comments"

                news_items.append({
                    "title": title,
                    "description": description,
                    "date": date_str,
                    "time": time_str,
                    "source": "Adaderana.lk",
                    "category": "Hot",
                    "url": news_url,
                    "word_count": compute_word_count(description),
                    "language": detect_language(description),
                    "sentiment": compute_sentiment(description),
                    "comments": comments
                })

        # --- Tech & Entertainment ---
        else:
            # select all story-text blocks inside main columns
            articles = soup.select("div.col-lg-7.col-sm-8.col-xs-12 .story-text")
            for article in articles:
                title_tag = article.select_one("h4 a")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                news_url = urljoin("https://www.adaderana.lk/", title_tag['href'])
                description = article.select_one("p").get_text(strip=True) if article.select_one("p") else title

                # Detect category from nearest <h3> heading
                parent_h3 = article.find_previous("h3")
                detected_category = parent_h3.get_text(strip=True) if parent_h3 else category.capitalize()

                # parse date
                date_span = article.select_one("div.col-xs-12.comments span")
                date_str, time_str = parse_datetime(date_span.get_text(strip=True)) if date_span else parse_datetime("")

                comments_tag = article.select_one("a[data-disqus-identifier], div.comments a")
                comments = comments_tag.get_text(strip=True) if comments_tag else "(0)Comments"

                news_items.append({
                    "title": title,
                    "description": description,
                    "date": date_str,
                    "time": time_str,
                    "source": "Adaderana.lk",
                    "category": detected_category,
                    "url": news_url,
                    "word_count": compute_word_count(description),
                    "language": detect_language(description),
                    "sentiment": compute_sentiment(description),
                    "comments": comments
                })

    return news_items

def scrape_news():
    all_news = []
    for category in ["tech", "entertainment", "hot"]:
        all_news.extend(scrape_adaderana(category, pages=5))
    return all_news

if __name__ == "__main__":
    news = scrape_news()
    print(f"Total articles scraped: {len(news)}")
    for item in news:
        print(item["title"], item["date"], item["category"])
