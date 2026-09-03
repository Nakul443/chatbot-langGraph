import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

# Set dummy env vars for testing before importing modules that might expect them
os.environ["LEGAL_RAG_MCP_URL"] = "http://mock-rag/mcp"
os.environ["WEB_SEARCH_API_KEY"] = "mock-tavily-key"
os.environ["MCP_SERVER_URL"] = "http://mock-mcp/mcp"
os.environ["OPENAI_API_KEY"] = "mock-openai-key"

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.builder import build_graph
from app.graph.state import State
from app.graph.tool_executor import custom_tool_executor
from app.tools import server

web_search = server.web_search


class TestMCPTools(unittest.TestCase):
    @patch("app.tools.server.requests.post")
    def test_web_search_success(self, mock_post):
        # Mock successful Tavily response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "url": "http://result1.com", "content": "This is content 1"},
                {"title": "Result 2", "url": "http://result2.com", "content": "This is content 2"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = web_search("test web query")
        self.assertIn("Result 1", result)
        self.assertIn("http://result1.com", result)
        self.assertIn("This is content 1", result)
        mock_post.assert_called_once_with(
            "https://api.tavily.com/search",
            json={
                "api_key": "mock-tavily-key",
                "query": "test web query",
                "search_depth": "basic"
            },
            timeout=15
        )

    @patch("app.tools.server.requests.post")
    def test_web_search_no_results(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = web_search("test web query")
        self.assertEqual(result, "No web search results found.")


class TestGraphBuild(unittest.TestCase):
    @patch("app.tools.mcp_tools.MultiServerMCPClient")
    def test_build_graph(self, mock_client_class):
        # Reset any global cache from other imports or runs
        import app.tools.mcp_tools
        app.tools.mcp_tools._client = None
        app.tools.mcp_tools._tools_cache = None

        # Mock MultiServerMCPClient instance and its get_tools method
        mock_client = MagicMock()
        
        # We need an async mock for get_tools
        async def mock_get_tools():
            return []  # Return empty list of tools for testing
            
        mock_client.get_tools = mock_get_tools
        mock_client_class.return_value = mock_client

        # Run async function build_graph
        graph = asyncio.run(build_graph())
        
        self.assertIsNotNone(graph)
        # Check that we have nodes we expect
        self.assertIn("chatbot", graph.nodes)
        self.assertIn("tools", graph.nodes)


class TestCustomToolExecutor(unittest.TestCase):
    def setUp(self):
        # Create a mock tool for ingest_pdf
        self.mock_ingest_tool = MagicMock()
        self.mock_ingest_tool.name = "ingest_pdf"
        
        async def mock_ainvoke(args):
            return f"Successfully ingested {args.get('filename')}"
        self.mock_ingest_tool.ainvoke = mock_ainvoke

    @patch("app.graph.tool_executor.get_mcp_tools")
    def test_multi_file_exact_match(self, mock_get_tools):
        mock_get_tools.return_value = [self.mock_ingest_tool]
        
        state: State = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ingest_pdf",
                            "args": {"filename": "contract.pdf"},
                            "id": "call_1"
                        }
                    ]
                )
            ],
            "user_id": "user123",
            "pending_upload": [
                {"filename": "receipt.pdf", "content_b64": "receipt_bytes"},
                {"filename": "contract.pdf", "content_b64": "contract_bytes"}
            ]
        }
        
        result = asyncio.run(custom_tool_executor(state))
        
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 1)
        self.assertIsInstance(result["messages"][0], ToolMessage)
        self.assertEqual(result["messages"][0].content, "Successfully ingested contract.pdf")
        self.assertIsNone(result["pending_upload"])

    @patch("app.graph.tool_executor.get_mcp_tools")
    def test_multi_file_case_insensitive_and_substring_match(self, mock_get_tools):
        mock_get_tools.return_value = [self.mock_ingest_tool]
        
        state: State = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ingest_pdf",
                            "args": {"filename": "CONTRACT"},
                            "id": "call_1"
                        }
                    ]
                )
            ],
            "user_id": "user123",
            "pending_upload": [
                {"filename": "receipt.pdf", "content_b64": "receipt_bytes"},
                {"filename": "contract.pdf", "content_b64": "contract_bytes"}
            ]
        }
        
        result = asyncio.run(custom_tool_executor(state))
        
        self.assertEqual(result["messages"][0].content, "Successfully ingested contract.pdf")

    @patch("app.graph.tool_executor.get_mcp_tools")
    def test_single_file_fallback(self, mock_get_tools):
        mock_get_tools.return_value = [self.mock_ingest_tool]
        
        # LLM calls ingest_pdf with no args or different name but there's only 1 pending upload
        state: State = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ingest_pdf",
                            "args": {},
                            "id": "call_1"
                        }
                    ]
                )
            ],
            "user_id": "user123",
            "pending_upload": [
                {"filename": "only_file.pdf", "content_b64": "only_bytes"}
            ]
        }
        
        result = asyncio.run(custom_tool_executor(state))
        self.assertEqual(result["messages"][0].content, "Successfully ingested only_file.pdf")

    @patch("app.graph.tool_executor.get_mcp_tools")
    def test_missing_file_error(self, mock_get_tools):
        mock_get_tools.return_value = [self.mock_ingest_tool]
        
        state: State = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ingest_pdf",
                            "args": {"filename": "missing.pdf"},
                            "id": "call_1"
                        }
                    ]
                )
            ],
            "user_id": "user123",
            "pending_upload": [
                {"filename": "receipt.pdf", "content_b64": "receipt_bytes"}
            ]
        }
        
        result = asyncio.run(custom_tool_executor(state))
        self.assertIn("Error: Could not find a pending upload matching the filename 'missing.pdf'", result["messages"][0].content)


if __name__ == "__main__":
    unittest.main()