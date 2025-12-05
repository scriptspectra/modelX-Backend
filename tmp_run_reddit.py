from app.scraper.trends_scraper import scrape_reddit_and_insert

if __name__ == '__main__':
    inserted = scrape_reddit_and_insert(subreddit='srilanka', limit=50)
    print('Inserted:', inserted)
