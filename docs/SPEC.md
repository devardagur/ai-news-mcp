# ai-news-mcp — Spec

## Goal

Keeping up with AI news is hard. This project fetches AI news once a day, stores it locally, and lets the user read, summarize, and research it from Claude through MCP.

## Users

Open source, for anyone. Users install it with one command.

## MVP

### Source
- Hacker News only (top + best lists).
- Keep only AI-related stories, using a keyword filter on the title.
- Store all AI stories found in top + best.

### Fetching
- Runs every day at 09:00 local time.
- Fetches once a day. If today's fetch has not succeeded yet (computer off, asleep, or an error), it is retried every hour until 23:00.
- Scheduled by macOS launchd. Output is written to `~/.ai-news-mcp/fetch.log`.

### Storage
- SQLite at `~/.ai-news-mcp/news.db`.
- Metadata only: title, URL, source, score, comment count, date.
- Date is the story's post time on Hacker News.
- Each story also keeps the day it was first fetched (first seen). It never changes after that.
- Article text is not stored; it is fetched when requested.
- Article text must be extracted cleanly so Claude can read it well.
- Article text longer than 75,000 characters is cut. Claude tells the user and shares the link to the full article.
- Only web pages, plain text and PDFs up to 50 MB are downloaded. Other links (model files, archives, videos) are not downloaded; Claude shares the link instead.
- Keep 30 days. Older stories are deleted.

### MCP server
- Tools:
  - Latest news: stories first seen in the latest fetch (same list as the daily summary).
  - List news (by date or date range, up to 30 days back).
  - Search news by keyword in the title, with optional date range.
  - Get an article's text by ID, so Claude can summarize and research it.
- Prompt: "Today's AI news". It shows the stories first seen in the latest fetch, so each story appears in exactly one daily summary.
- Summarizing and research are done by Claude (the MCP client). No API key needed.

### Install
- Clone the repo, then run one command: `uv run ai-news-mcp install`
- It does:
  1. Adds the MCP server to Claude Desktop.
  2. Sets up the 09:00 launchd job.
  3. Runs the first fetch.
- Claude Desktop and launchd run the code from the cloned folder, so the folder must stay in place.

### Uninstall
- One command: `uv run ai-news-mcp uninstall`
- Claude Desktop must be quit first; otherwise uninstall stops without changing anything.
- It removes the Claude Desktop entry and the launchd job, and deletes the database and logs.
  The config looks as it did before install. Then the user deletes the cloned folder.

### Platform
- macOS only.
- Client: Claude Desktop only.

## Tech
- Python 3.12, uv
- Official `mcp` Python SDK
- SQLite
- `httpx` for HTTP, `trafilatura` for article text extraction, `pypdf` for PDF text extraction
