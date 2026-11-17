# CLAUDE.md

MCP server that fetches AI news from Hacker News daily and serves it to Claude Desktop. Full spec: [docs/SPEC.md](docs/SPEC.md).

## Stack
- Python 3.12, uv
- Official `mcp` Python SDK
- SQLite at `~/.ai-news-mcp/news.db`

## Structure
```
ai-news-mcp/
├── pyproject.toml
├── CLAUDE.md
├── docs/
│   └── SPEC.md
└── src/ai_news_mcp/
    ├── __init__.py
    ├── cli.py         # Commands: install, fetch, serve
    ├── server.py      # MCP tools and prompt
    ├── fetcher.py     # Hacker News fetch and AI filter
    ├── db.py          # SQLite access and 30-day cleanup
    └── installer.py   # Claude Desktop config and launchd job
```

## Scope
- MVP: Hacker News only, macOS only, Claude Desktop only.
- Store metadata only, 30 days.
- Summarizing is done by Claude, not by the server.

## Code rules
- Keep the code clean and simple. No over-engineering.
- Comments: one or two sentences at most, only where needed.

## Working rules
- Do not add anything that is not in the spec or was not asked for.
- If something new seems needed during development, ask first.
