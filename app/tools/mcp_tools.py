# MCP / external tool definitions bound to the LLM.
# Connects to app/tools/server.py (a FastMCP server) and loads real,
# runtime-discovered tools via langchain-mcp-adapters.

import asyncio
import os
from typing import Any

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

        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8002/mcp")
        mcp_auth_token = os.getenv("MCP_AUTH_TOKEN")

        connection_config: dict[str, Any] = {
            "transport": "streamable_http",
            "url": mcp_server_url,
        }
        if mcp_auth_token:
            connection_config["headers"] = {
                "Authorization": f"Bearer {mcp_auth_token}"
            }

        legal_rag_mcp_url = os.getenv("LEGAL_RAG_MCP_URL", "http://localhost:8003/mcp")
        legal_rag_auth_token = os.getenv("LEGAL_RAG_AUTH_TOKEN")

        legal_rag_connection_config: dict[str, Any] = {
            "transport": "streamable_http",
            "url": legal_rag_mcp_url,
        }
        if legal_rag_auth_token:
            legal_rag_connection_config["headers"] = {
                "Authorization": f"Bearer {legal_rag_auth_token}"
            }

        connections: dict[str, Any] = {
            "project_server": connection_config,
            "legal_rag_server": legal_rag_connection_config,
        }
        _client = MultiServerMCPClient(connections)

        _tools_cache = await _client.get_tools()

    return _tools_cache