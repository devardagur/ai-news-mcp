"""Entry point for the `ai-news-mcp` command. Routes each subcommand to its module."""

import argparse

from ai_news_mcp import fetcher, installer, server


def install() -> None:
    """Run once by the user: set up Claude Desktop, the daily job, and the first fetch."""
    installer.run()


def uninstall() -> None:
    """Run by the user to remove everything install set up, including the stored news."""
    installer.uninstall()


def fetch() -> None:
    """Run daily by launchd: fetch AI stories from Hacker News into the database."""
    fetcher.run()


def serve() -> None:
    """Started by Claude Desktop: run the MCP server over stdio."""
    server.run()


# Subcommand name -> (function to run, help text).
COMMANDS = {
    "install": (install, "Add the server to Claude Desktop, set up the daily job, run the first fetch."),
    "uninstall": (uninstall, "Remove the server from Claude Desktop, the daily job, and all stored data."),
    "fetch": (fetch, "Fetch today's AI news from Hacker News."),
    "serve": (serve, "Run the MCP server."),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-news-mcp", description="AI news from Hacker News for Claude Desktop.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        subparsers.add_parser(name, help=help_text)

    args = parser.parse_args()
    COMMANDS[args.command][0]()
