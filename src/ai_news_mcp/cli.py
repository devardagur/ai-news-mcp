import argparse


def install() -> None:
    raise SystemExit("install: not implemented yet")


def fetch() -> None:
    raise SystemExit("fetch: not implemented yet")


def serve() -> None:
    raise SystemExit("serve: not implemented yet")


COMMANDS = {
    "install": (install, "Add the server to Claude Desktop, set up the daily job, run the first fetch."),
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
