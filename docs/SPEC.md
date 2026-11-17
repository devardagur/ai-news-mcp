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
- If the computer was off at 09:00, the missed fetch runs on the next wake/boot.
- Scheduled by macOS launchd.

### Storage
- SQLite at `~/.ai-news-mcp/news.db`.
- Metadata only: title, URL, source, score, comment count, date.
- Article text is not stored; it is fetched when requested.
- Keep 30 days. Older stories are deleted.

### MCP server
- Tools:
  - List news (by date or date range, up to 30 days back).
  - Search news by keyword in the title, with optional date range.
  - Get an article's text by URL/ID, so Claude can summarize and research it.
- Prompt: "Today's AI news".
- Summarizing and research are done by Claude (the MCP client). No API key needed.

### Install
- One command: `uvx ai-news-mcp install`
- It does:
  1. Adds the MCP server to Claude Desktop.
  2. Sets up the 09:00 launchd job.
  3. Runs the first fetch.

### Platform
- macOS only.
- Client: Claude Desktop only.

## Tech
- Python 3.12, uv
- Official `mcp` Python SDK
- SQLite
- Published to PyPI
