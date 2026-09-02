# file to handle the core business logic for streaming chat responses using LangGraph and PostgreSQL

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig

from app.graph.builder import build_graph_with_checkpointer
from app.persistence.db import get_checkpointer


# when user sends a message
# it hits the /chat/stream endpoint with {message, thread_id} + Authorization: Bearer <jwt> header
async def handle_chat_stream(message: str, thread_id: str, user_id: str) -> StreamingResponse:
    """
    Handles the core business logic for streaming chat responses using LangGraph and PostgreSQL.
    """
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required for state management.")

    # Scope the thread to the authenticated user so one user can never read/write
    # another user's conversation just by guessing/reusing a thread_id.
    scoped_thread_id = f"{user_id}:{thread_id}"

    async def event_generator():
        try:
            # 1. Instantiate the checkpointer (shares the app-wide connection pool)
            #    and compile the graph for this request.
            checkpointer = await get_checkpointer()
            graph = await build_graph_with_checkpointer(checkpointer)

            # 2. Configure thread isolation (scoped to the authenticated user)
            config: RunnableConfig = {"configurable": {"thread_id": scoped_thread_id}}

            # 3. Format input payload for the graph state
            input_data = {
                "messages": [("user", message)],
                "user_id": user_id,
            }

            # 4. Stream individual LLM tokens as they're generated (true
            #    token-by-token streaming, per architecture step 12).
            #    "messages" mode yields (message_chunk, metadata) tuples.
            async for msg_chunk, metadata in graph.astream(
                input_data, config=config, stream_mode="messages"
            ):
                # Only stream tokens coming from the chatbot node, not tool nodes
                content = getattr(msg_chunk, "content", msg_chunk)
                if isinstance(metadata, dict) and metadata.get("langgraph_node") == "chatbot" and content:
                    yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {e!s}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")