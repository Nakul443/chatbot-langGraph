from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.persistence.db import get_checkpointer
from app.graph.builder import build_graph_with_checkpointer

async def handle_chat_stream(message: str, thread_id: str) -> StreamingResponse:
    """
    Handles the core business logic for streaming chat responses using LangGraph and PostgreSQL.
    """
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required for state management.")

    async def event_generator():
        try:
            # 1. Instantiate the checkpointer and compile the graph for this request
            async with await get_checkpointer() as checkpointer:
                graph = await build_graph_with_checkpointer(checkpointer)

                # 2. Configure thread isolation
                config = {"configurable": {"thread_id": thread_id}}

                # 3. Format input payload for the graph state
                input_data = {"messages": [("user", message)]}

                # 4. Stream graph node outputs asynchronously
                async for event in graph.astream(input_data, config=config, stream_mode="updates"):
                    if "chatbot" in event:
                        ai_message = event["chatbot"]["messages"][-1]
                        content = ai_message.content
                        if content:
                            # Yield chunk formatted for Server-Sent Events
                            yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")