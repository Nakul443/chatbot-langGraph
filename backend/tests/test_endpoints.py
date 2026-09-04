import asyncio

# Mock env vars before import
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["LEGAL_RAG_MCP_URL"] = "http://mock-rag/mcp"
os.environ["WEB_SEARCH_API_KEY"] = "mock-tavily-key"
os.environ["MCP_SERVER_URL"] = "http://mock-mcp/mcp"
os.environ["GEMINI_API_KEY"] = "mock-gemini-key"
os.environ["GOOGLE_API_KEY"] = "mock-google-key"

from fastapi import HTTPException

from app.controllers.chat_controller import handle_get_history, handle_get_threads


class TestChatEndpoints(unittest.TestCase):

    @patch("app.persistence.db.connection_pool")
    def test_handle_get_threads_success(self, mock_pool):
        # Set up async mock for connection and cursor
        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        
        # Configure mock_pool to yield mock_conn when connection() is called
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn
        
        # conn.cursor() is a sync call returning an async context manager
        mock_conn.cursor = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cur
        
        # Mock rows returned by DB
        mock_rows = [
            {"thread_id": "user-123:thread-abc", "last_updated": "2026-09-03T12:00:00+00:00"},
            {"thread_id": "user-123:thread-xyz", "last_updated": "2026-09-03T11:00:00+00:00"}
        ]
        mock_cur.fetchall.return_value = mock_rows

        # Call function via asyncio.run
        result = asyncio.run(handle_get_threads("user-123"))

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["thread_id"], "thread-abc")
        self.assertEqual(result[0]["updated_at"], "2026-09-03T12:00:00+00:00")
        self.assertEqual(result[0]["preview"], "Last updated: 2026-09-03T12:00:00+00:00")
        
        self.assertEqual(result[1]["thread_id"], "thread-xyz")  # strip prefix test
        self.assertEqual(result[1]["updated_at"], "2026-09-03T11:00:00+00:00")

        # Verify SQL execution
        mock_cur.execute.assert_called_once()
        query_arg = mock_cur.execute.call_args[0][0]
        params_arg = mock_cur.execute.call_args[0][1]
        self.assertIn("SELECT thread_id, max(checkpoint->>'ts')", query_arg)
        self.assertEqual(params_arg, ("user-123:%",))

    @patch("app.controllers.chat_controller.build_graph_with_checkpointer")
    @patch("app.controllers.chat_controller.get_checkpointer")
    def test_handle_get_history_success(self, mock_get_checkpointer, mock_build_graph):
        # Setup mocks
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer

        mock_graph = AsyncMock()
        mock_build_graph.return_value = mock_graph

        # Mock messages returned by state
        mock_msg1 = MagicMock()
        mock_msg1.type = "human"
        mock_msg1.content = "Hello bot"

        mock_msg2 = MagicMock()
        mock_msg2.type = "ai"
        mock_msg2.content = "Hello human"

        mock_state = MagicMock()
        mock_state.metadata = {"step": 1}
        mock_state.values = {"messages": [mock_msg1, mock_msg2]}
        mock_graph.aget_state.return_value = mock_state

        # Call function
        result = asyncio.run(handle_get_history("thread-abc", "user-123"))

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {"role": "user", "content": "Hello bot"})
        self.assertEqual(result[1], {"role": "assistant", "content": "Hello human"})

        # Verify aget_state called with proper config
        mock_graph.aget_state.assert_called_once_with({
            "configurable": {"thread_id": "user-123:thread-abc"}
        })

    @patch("app.controllers.chat_controller.build_graph_with_checkpointer")
    @patch("app.controllers.chat_controller.get_checkpointer")
    def test_handle_get_history_not_found(self, mock_get_checkpointer, mock_build_graph):
        mock_checkpointer = MagicMock()
        mock_get_checkpointer.return_value = mock_checkpointer

        mock_graph = AsyncMock()
        mock_build_graph.return_value = mock_graph

        # Mock state to return None metadata, meaning thread not found / does not belong to user
        mock_state = MagicMock()
        mock_state.metadata = None
        mock_graph.aget_state.return_value = mock_state

        # Verify that HTTPException 404 is raised
        with self.assertRaises(HTTPException) as context:
            asyncio.run(handle_get_history("thread-xyz", "user-123"))
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Thread not found.")


if __name__ == "__main__":
    unittest.main()
