"""WhiteNote MCP server entrypoint.

Usage:
    python -m src.mcp_server.server --transport http --host 0.0.0.0 --port 8765
    python -m src.mcp_server.server --transport stdio
"""
from __future__ import annotations

import argparse
import logging
import sys

from fastmcp import FastMCP

from src.config import Config
from src.mcp_server import tools_chat, tools_jobs, tools_papers, tools_zotero


def build_app() -> FastMCP:
    mcp = FastMCP(
        name="whitenote",
        instructions=(
            "WhiteNote exposes a personal arXiv feed. Typical agent flow:\n"
            "  1. `list_recent_papers` to see what's new.\n"
            "  2. `get_paper` for details, optionally `get_paper_summary` "
            "(enqueues a job if the summary isn't cached yet).\n"
            "  3. `chat_with_paper` to ask follow-ups against the full text.\n"
            "  4. `mark_paper` to record verdicts (liked/disliked/later/folder).\n"
            "  5. `save_to_zotero` to push keepers into the user's library."
        ),
    )
    tools_papers.register(mcp)
    tools_chat.register(mcp)
    tools_jobs.register(mcp)
    tools_zotero.register(mcp)
    return mcp


def _selftest() -> int:
    app = build_app()
    try:
        import asyncio

        tools = asyncio.run(app.get_tools())  # type: ignore[attr-defined]
        names = sorted(tools.keys() if isinstance(tools, dict) else (t.name for t in tools))
    except Exception:
        names = []
    print("WhiteNote MCP server — registered tools:")
    for name in names:
        print(f"  - {name}")
    if not names:
        print("  (tool introspection unavailable on this FastMCP version)")
    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(description="WhiteNote MCP server")
    parser.add_argument(
        "--transport",
        choices=["http", "stdio", "sse"],
        default=Config.mcp.transport,
    )
    parser.add_argument("--host", default=Config.mcp.host)
    parser.add_argument("--port", type=int, default=Config.mcp.port)
    parser.add_argument("--selftest", action="store_true", help="List tools and exit.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("whitenote.mcp")

    if args.selftest:
        sys.exit(_selftest())

    app = build_app()

    if args.transport == "stdio":
        logger.info("Starting MCP server on stdio")
        app.run(transport="stdio")
    else:
        # FastMCP exposes streamable HTTP at /mcp/ and SSE at /sse/.
        transport = "sse" if args.transport == "sse" else "streamable-http"
        logger.info(
            "Starting MCP server on http://%s:%d (transport=%s)",
            args.host, args.port, transport,
        )
        app.run(transport=transport, host=args.host, port=args.port)


if __name__ == "__main__":
    cli()
