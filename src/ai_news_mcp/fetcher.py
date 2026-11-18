"""Fetch Hacker News top + best stories, keep the AI-related ones, and save them to the database."""

import asyncio
import re
from datetime import date
from pathlib import Path

import httpx

from ai_news_mcp import db

HN_API = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_PAGE = "https://news.ycombinator.com/item?id={id}"
LISTS = ("topstories", "beststories")
MAX_PARALLEL = 20
RETRY_DELAYS = (1, 2)  # Seconds to wait before the 2nd and 3rd attempt.

# Names of models and companies, plus general terms that usually appear when a new model is announced.
AI_KEYWORDS = [
    "AI", "LLM", "GPT", "Claude", "Anthropic", "OpenAI", "Gemini", "machine learning",
    "neural", "transformer", "diffusion", "agent", "Llama", "Mistral", "DeepSeek",
    "ML", "Copilot", "Grok", "Qwen", "Kimi", "Phi", "Gemma", "Sora", "Midjourney",
    "Hugging Face", "xAI", "Perplexity", "Cursor",
    "language model", "frontier model", "foundation model", "open-weights", "open weights",
    "reasoning model", "AGI", "chatbot", "deep learning", "reinforcement learning",
    "fine-tuning", "inference", "RAG",
]

# Whole words only, so "AI" does not match "said". An optional "s" allows plurals like "LLMs".
AI_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in AI_KEYWORDS) + r")s?\b", re.IGNORECASE)


def is_ai_story(title: str) -> bool:
    return AI_PATTERN.search(title) is not None


async def _get_json(client: httpx.AsyncClient, path: str):
    # Up to 3 attempts, since short network or HN hiccups usually pass on a retry.
    # If the last attempt also fails, the error is raised.
    for delay in (*RETRY_DELAYS, None):
        try:
            response = await client.get(f"{HN_API}/{path}.json")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if delay is None:
                raise
            await asyncio.sleep(delay)


async def _get_story_ids(client: httpx.AsyncClient) -> list[int]:
    # Union of both lists, in order, without duplicates.
    ids: dict[int, None] = {}
    for name in LISTS:
        ids.update(dict.fromkeys(await _get_json(client, name)))
    return list(ids)


async def _get_item(client: httpx.AsyncClient, item_id: int, limit: asyncio.Semaphore) -> dict | None:
    # If an item still fails after its retries, the whole fetch fails and is retried later.
    # HN returns null for some removed items; that is a valid answer, not an error.
    async with limit:
        return await _get_json(client, f"item/{item_id}")


def _to_story(item: dict) -> dict:
    return {
        "id": item["id"],
        "title": item["title"],
        # Text posts like "Ask HN" have no URL, so link to the HN discussion page.
        "url": item.get("url") or HN_ITEM_PAGE.format(id=item["id"]),
        "source": "hackernews",
        "score": item.get("score", 0),
        "comments": item.get("descendants", 0),
        "posted_at": item["time"],
    }


async def fetch_ai_stories() -> list[dict]:
    """Download all top + best stories and return the AI-related ones."""
    limit = asyncio.Semaphore(MAX_PARALLEL)
    async with httpx.AsyncClient(timeout=10) as client:
        ids = await _get_story_ids(client)
        items = await asyncio.gather(*(_get_item(client, i, limit) for i in ids))

    return [
        _to_story(item)
        for item in items
        if item
        and item.get("type") == "story"
        and not item.get("dead")
        and not item.get("deleted")
        and is_ai_story(item.get("title", ""))
    ]


def run(path: Path = db.DB_PATH) -> None:
    """Fetch once per day. If today's fetch already succeeded, do nothing."""
    today = date.today()
    if db.get_last_fetch_date(path) == today:
        print("Already fetched today.")
        return

    stories = asyncio.run(fetch_ai_stories())
    db.save_stories(stories, path)
    deleted = db.delete_old_stories(path)
    # Only mark the day as done after everything succeeded, so a failed fetch is retried.
    db.set_last_fetch_date(today, path)
    print(f"Saved {len(stories)} AI stories, deleted {deleted} old ones.")
