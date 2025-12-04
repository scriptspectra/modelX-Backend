from textblob import TextBlob
from langdetect import detect

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
