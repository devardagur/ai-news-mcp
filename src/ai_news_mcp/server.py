"""MCP server for Claude Desktop: tools to list, search and read AI news, plus the daily summary prompt."""

from datetime import date, timedelta

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ai_news_mcp import db, fetcher

# WARNING log level keeps routine "HTTP Request" lines out of the logs.
mcp = MCPServer("ai-news", log_level="WARNING")

# Long PDFs can be hundreds of thousands of characters; the start is enough for a summary.
MAX_ARTICLE_CHARS = 75_000


def _parse_range(start_date: str | None, end_date: str | None) -> tuple[date, date]:
    # Dates are YYYY-MM-DD. Missing start means the oldest kept day; missing end means today.
    # ToolError messages are shown to Claude, so it can fix the call.
    today = date.today()
    oldest = today - timedelta(days=db.KEEP_DAYS)
    try:
        start = date.fromisoformat(start_date) if start_date else oldest
        end = date.fromisoformat(end_date) if end_date else today
    except ValueError:
        raise ToolError("Dates must be in YYYY-MM-DD format.")
    if start < oldest:
        raise ToolError(f"Only the last {db.KEEP_DAYS} days are kept. The earliest date is {oldest}.")
    if end < start:
        raise ToolError("end_date must not be before start_date.")
    return start, end


@mcp.tool()
def latest_news() -> dict:
    """Get the AI news that first appeared in the latest daily fetch from Hacker News.
    Use this for questions like "what's new today?" or "what's new in AI?".
    Each story has an id; pass it to get_article to read the article."""
    day = db.get_last_fetch_date()
    if day is None:
        raise ToolError("No AI news has been fetched yet. The user should run `ai-news-mcp fetch` first.")
    return {"fetch_date": day.isoformat(), "stories": db.list_new_stories(day)}


@mcp.tool()
def list_news(start_date: str, end_date: str | None = None) -> list[dict]:
    """List AI news from Hacker News posted between start_date and end_date (YYYY-MM-DD, both inclusive).
    Leave end_date empty for a single day. Only the last 30 days are available.
    For "what's new today?" questions, use latest_news instead.
    Each story has an id; pass it to get_article to read the article."""
    return db.list_stories(*_parse_range(start_date, end_date or start_date))


@mcp.tool()
def search_news(keyword: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Search AI news whose title contains the keyword (case-insensitive).
    Optional start_date and end_date (YYYY-MM-DD) limit the post date. A missing start_date means 30 days ago,
    a missing end_date means today."""
    return db.search_stories(keyword, *_parse_range(start_date, end_date))


@mcp.tool()
def get_article(story_id: int) -> str:
    """Get the readable text of a story's article by its id, to summarize or research it.
    Works for web pages, PDFs and Hacker News text posts."""
    story = db.get_story(story_id)
    if story is None:
        raise ToolError(f"No story with id {story_id}.")

    # Errors are returned as text so Claude can tell the user and still share the link.
    try:
        text = fetcher.fetch_article_text(story)
    except Exception as error:
        return f"Could not read the article ({error}). URL: {story['url']}"
    if not text:
        return f"No readable text was found in the article. URL: {story['url']}"
    if len(text) > MAX_ARTICLE_CHARS:
        text = text[:MAX_ARTICLE_CHARS] + (
            "\n\n(Truncated: the article is too long, only the first part is shown. "
            "Tell the user the summary covers only this part and share the link to read the full article.)"
        )
    return f"# {story['title']}\nURL: {story['url']}\n\n{text}"


@mcp.prompt(title="Today's AI news")
def todays_ai_news() -> str:
    """Summarize the AI news that arrived in the latest daily fetch."""
    return (
        "Call the latest_news tool and give me a short summary of the stories. "
        "Group related stories and start with the most important ones. "
        "Use get_article to read the articles you need, and include the link for each story you mention. "
        "If there are no stories, tell me."
    )


def run() -> None:
    """Run the server over stdio. Claude Desktop starts this as a background process."""
    mcp.run()
