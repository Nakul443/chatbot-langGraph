# server file using fastMCP

from fastmcp import FastMCP
import os

# Initialize the FastMCP server instance
mcp = FastMCP("ProjectNotesServer")

@mcp.tool()
def get_project_status(project_name: str) -> str:
    """Get the current operational and deployment status of a specified project."""
    # Real logic can query a database, read a file, or check an API
    return f"Project '{project_name}' is currently active, containerized via Docker, and passing all checks."

@mcp.tool()
def search_local_files(query: str) -> str:
    """Search through local workspace directories or documentation notes for specific keywords."""
    # Real file search simulation or actual implementation
    return f"Found 3 matching references for query '{query}' in local markdown files."

if __name__ == "__main__":
    # Run via stdio transport so the client process can communicate with it securely
    mcp.run(transport="stdio")