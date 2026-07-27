# MCP / external tool definitions bound to the LLM.
# Replace these stub tools with real MCP client calls
# (e.g. via langchain-mcp-adapters) when your MCP server is ready.

from langchain_core.tools import tool


@tool
def get_project_status(project_name: str) -> str:
    """Look up the current status of a named project."""
    # TODO: replace with a real MCP tool call / DB / API lookup
    return f"Project '{project_name}' is currently on track. Last update: 2 days ago."


@tool
def search_documents(query: str) -> str:
    """Search internal documents/files for a given query."""
    # TODO: replace with a real MCP tool call (file search, vector DB, etc.)
    return f"Found 3 documents matching '{query}'."


# All tools exposed to the graph
tools = [get_project_status, search_documents]