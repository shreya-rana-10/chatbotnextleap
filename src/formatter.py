import re
from datetime import datetime


def clip_sentences(text: str, limit: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentence for sentence in sentences[:limit] if sentence)


def format_answer(answer: str, url: str, scraped_at: str, max_sentences: int = 3) -> str:
    body = re.sub(r"https?://\S+", "", answer).strip()
    body = clip_sentences(body, max_sentences)
    if not body:
        body = "I couldn't form an answer from the retrieved source text."
    updated = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
    date_text = updated.strftime("%d %b %Y")
    return f"{body}\n\nSource: {url}\nLast updated from sources: {date_text}"
