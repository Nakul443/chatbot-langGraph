# MCP / external tool definitions bound to the LLM.
# Connects to app/tools/server.py (a FastMCP server) and loads real,
# runtime-discovered tools via langchain-mcp-adapters.

import asyncio
import os
from typing import Any
import httpx

from langchain_mcp_adapters.client import MultiServerMCPClient

_client: MultiServerMCPClient | None = None
_tools_cache: list | None = None
_lock = asyncio.Lock()


async def _probe_server(url: str, headers: dict | None = None) -> bool:
    """Probes if an HTTP server is reachable by making a quick request."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            # We use options or get; any response (even 401, 404, or 405) implies the server is online.
            await client.options(url, headers=headers)
            return True
    except httpx.HTTPStatusError:
        return True
    except httpx.InvalidURL:
        return False
    except Exception:
        # Try a quick GET as a fallback probe
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.get(url, headers=headers)
                return True
        except httpx.HTTPStatusError:
            return True
        except Exception:
            return False


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
        project_headers = {}
        if mcp_auth_token:
            connection_config["headers"] = {
                "Authorization": f"Bearer {mcp_auth_token}"
            }
            project_headers = {"Authorization": f"Bearer {mcp_auth_token}"}

        legal_rag_mcp_url = os.getenv("LEGAL_RAG_MCP_URL", "http://localhost:8003/mcp")
        legal_rag_auth_token = os.getenv("LEGAL_RAG_AUTH_TOKEN")

        legal_rag_connection_config: dict[str, Any] = {
            "transport": "streamable_http",
            "url": legal_rag_mcp_url,
        }
        rag_headers = {}
        if legal_rag_auth_token:
            legal_rag_connection_config["headers"] = {
                "Authorization": f"Bearer {legal_rag_auth_token}"
            }
            rag_headers = {"Authorization": f"Bearer {legal_rag_auth_token}"}

        # Dynamically probe servers to be resilient to offline instances during local development
        connections: dict[str, Any] = {}
        
        project_reachable = await _probe_server(mcp_server_url, headers=project_headers)
        if project_reachable:
            connections["project_server"] = connection_config
        else:
            print(f"⚠️ Warning: project MCP server is unreachable at {mcp_server_url}. Skipping.")

        rag_reachable = await _probe_server(legal_rag_mcp_url, headers=rag_headers)
        if rag_reachable:
            connections["legal_rag_server"] = legal_rag_connection_config
        else:
            print(f"⚠️ Warning: legal RAG MCP server is unreachable at {legal_rag_mcp_url}. Skipping.")

        if not connections:
            print("⚠️ Warning: No MCP servers are currently online/reachable. Returning empty tools list.")
            _tools_cache = []
            return _tools_cache

        _client = MultiServerMCPClient(connections)
        try:
            _tools_cache = await _client.get_tools()
        except Exception as e:
            print(f"⚠️ Warning: Failed to retrieve tools from MultiServerMCPClient: {e}. Falling back to empty list.")
            _tools_cache = []

    return _tools_cache