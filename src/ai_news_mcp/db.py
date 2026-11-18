"""SQLite storage for AI stories. Used by the fetcher (write) and the MCP server (read)."""

import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".ai-news-mcp" / "news.db"
KEEP_DAYS = 30

# stories: one row per HN story, keyed by HN id.
#   posted_at is the HN post time; first_seen is the day we first fetched it (YYYY-MM-DD).
# meta: small key/value store, e.g. the date of the last successful fetch.
SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    score INTEGER NOT NULL,
    comments INTEGER NOT NULL,
    posted_at INTEGER NOT NULL,
    first_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stories_first_seen ON stories (first_seen);
CREATE INDEX IF NOT EXISTS idx_stories_posted_at ON stories (posted_at);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    """Open the database, creating the folder and tables on first use."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _day_start(day: date) -> int:
    # Dates are local calendar days; posted_at is a Unix timestamp.
    return int(datetime.combine(day, time.min).timestamp())


def _date_range(start: date, end: date) -> tuple[int, int]:
    # End is inclusive, so the range runs until the start of the next day.
    return _day_start(start), _day_start(end + timedelta(days=1))


def _to_dict(row: sqlite3.Row) -> dict:
    # Turn the timestamp into a readable local time for Claude.
    story = dict(row)
    story["posted_at"] = datetime.fromtimestamp(story["posted_at"]).isoformat(timespec="minutes")
    return story


def save_stories(stories: list[dict], day: date) -> None:
    """Insert new stories with first_seen set to day.
    If a story already exists, refresh its title, URL, score and comment count; first_seen stays as it was."""
    rows = [{**story, "first_seen": day.isoformat()} for story in stories]
    with closing(connect()) as conn, conn:
        conn.executemany(
            """
            INSERT INTO stories (id, title, url, source, score, comments, posted_at, first_seen)
            VALUES (:id, :title, :url, :source, :score, :comments, :posted_at, :first_seen)
            ON CONFLICT (id) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                score = excluded.score,
                comments = excluded.comments
            """,
            rows,
        )


def list_stories(start: date, end: date) -> list[dict]:
    """Return stories posted between start and end (both inclusive), newest first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM stories WHERE posted_at >= ? AND posted_at < ? ORDER BY posted_at DESC",
            _date_range(start, end),
        ).fetchall()
    return [_to_dict(row) for row in rows]


def list_new_stories(day: date) -> list[dict]:
    """Return stories first seen on the given day, newest first. Used for the daily summary."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM stories WHERE first_seen = ? ORDER BY posted_at DESC",
            (day.isoformat(),),
        ).fetchall()
    return [_to_dict(row) for row in rows]


def search_stories(keyword: str, start: date, end: date) -> list[dict]:
    """Return stories whose title contains the keyword (case-insensitive), newest first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM stories
            WHERE title LIKE ? AND posted_at >= ? AND posted_at < ?
            ORDER BY posted_at DESC
            """,
            (f"%{keyword}%", *_date_range(start, end)),
        ).fetchall()
    return [_to_dict(row) for row in rows]


def get_story(story_id: int) -> dict | None:
    """Return one story by its HN id, or None if it is not stored."""
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    return _to_dict(row) if row else None


def delete_old_stories() -> int:
    """Delete stories posted more than 30 days ago. Returns how many were deleted."""
    cutoff = _day_start(date.today() - timedelta(days=KEEP_DAYS))
    with closing(connect()) as conn, conn:
        return conn.execute("DELETE FROM stories WHERE posted_at < ?", (cutoff,)).rowcount


def get_last_fetch_date() -> date | None:
    """Return the day of the last successful fetch, or None if there was none."""
    with closing(connect()) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = 'last_fetch_date'").fetchone()
    return date.fromisoformat(row["value"]) if row else None


def set_last_fetch_date(day: date) -> None:
    """Record the day of a successful fetch, so it is not repeated the same day."""
    with closing(connect()) as conn, conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('last_fetch_date', ?)"
            " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (day.isoformat(),),
        )
