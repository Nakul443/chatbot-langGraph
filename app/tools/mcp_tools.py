# MCP / external tool definitions bound to the LLM.
# Replace these stub tools with real MCP client calls
# (e.g. via langchain-mcp-adapters) when your MCP server is ready.

import sys
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools():
    """
    Dynamically initializes an MCP client connection to the local server 
    and loads real runtime tools via langchain-mcp-adapters.
    """
    # Configure the client to spin up our server script via stdio
    client = MultiServerMCPClient({
        "project_server": {
            "transport": "stdio",
            "command": sys.executable,  # Uses the active virtual environment python interpreter
            "args": [os.path.abspath("app/tools/server.py")],
        }
    })
    
    # Retrieve and return the dynamically discovered tools
    tools = await client.get_tools()
    return tools