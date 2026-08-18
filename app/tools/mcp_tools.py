# MCP / external tool definitions bound to the LLM.
# Connects to app/tools/server.py (a FastMCP server) and loads real,
# runtime-discovered tools via langchain-mcp-adapters.

import sys
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

_client: MultiServerMCPClient | None = None
_tools_cache: list | None = None
_lock = asyncio.Lock()


async def get_mcp_tools():
    """
    initializes a single MCP client connection and caches the
    discovered tools. Without this cache, every call would spin up a fresh
    stdio subprocess (server.py) -- expensive, and leaves zombie processes
    if the client is never closed. The client/tools are created once and
    reused for the lifetime of the app process.
    """
    global _client, _tools_cache

    if _tools_cache is not None:
        return _tools_cache

    async with _lock:
        # re-check after acquiring the lock in case another coroutine
        # populated the cache while we were waiting on it
        if _tools_cache is not None:
            return _tools_cache

        _client = MultiServerMCPClient({
            "project_server": {
                "transport": "stdio",
                "command": sys.executable,  # Uses the active virtual environment's python interpreter
                "args": [os.path.abspath("app/tools/server.py")],
            }
        })

        _tools_cache = await _client.get_tools()

    return _tools_cache