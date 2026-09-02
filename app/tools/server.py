# server file using fastMCP

import os

import requests
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# Define Authorization Middleware for security
# this function checks for the presence of a valid Bearer token in the Authorization header of incoming requests to the MCP server.
# If the token is missing or invalid, it returns a 401 Unauthorized response.
class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # We only protect HTTP/SSE routes, typically /mcp or sub-endpoints
        # Skip health check or general endpoints if necessary
        if request.url.path.startswith("/mcp"):
            expected_token = os.getenv("MCP_AUTH_TOKEN")
            if expected_token:
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        {"detail": "Unauthorized: Missing or invalid Authorization header"},
                        status_code=401
                    )
                token = auth_header.split(" ", 1)[1]
                if token != expected_token:
                    return JSONResponse(
                        {"detail": "Unauthorized: Invalid token"},
                        status_code=401
                    )
        
        response = await call_next(request)
        return response

# Initialize the FastMCP server instance
mcp = FastMCP("ProjectNotesServer")

@mcp.tool()
def search_rag(query: str) -> str:
    """Search the Legal-RAG knowledge base using hybrid search and CrossEncoder reranking."""
    rag_url = os.getenv("RAG_SERVICE_URL")
    if not rag_url:
        return "RAG service URL is not configured."
    try:
        response = requests.post(rag_url, json={"query": query}, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            if "results" in data:
                return str(data["results"])
            elif "response" in data:
                return str(data["response"])
            elif "answer" in data:
                return str(data["answer"])
            return str(data)
        return str(data)
    except requests.RequestException as e:
        return f"Error querying RAG service: {e}"
    except Exception as e:
        return f"Unexpected error querying RAG service: {e}"

@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for up-to-date information on a given topic."""
    api_key = os.getenv("WEB_SEARCH_API_KEY") or os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Web search API key is not configured."
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic"
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return "No web search results found."
        
        formatted_results = []
        for r in results[:5]:  # Limit to top 5 results
            formatted_results.append(
                f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('content')}\n"
            )
        return "\n".join(formatted_results)
    except requests.RequestException as e:
        return f"Error performing web search: {e}"
    except Exception as e:
        return f"Unexpected error performing web search: {e}"

if __name__ == "__main__":
    # Run via streamable-http transport on port 8002 so it can be reached as a network service
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002,
        middleware=[Middleware(BearerAuthMiddleware)]
    )