# file to handle the core business logic for streaming chat responses using LangGraph and PostgreSQL

import base64

from fastapi import HTTPException, UploadFile
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


async def handle_chat_upload(files: list[UploadFile], thread_id: str, user_id: str) -> StreamingResponse:
    """
    Handles file upload, converts them to base64, updates the graph state with
    the files and triggers an ingestion instruction message in the stream.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required for state management.")

    # Read and encode file content to base64
    pending_files = []
    filenames = []
    for file in files:
        try:
            file_bytes = await file.read()
            content_b64 = base64.b64encode(file_bytes).decode("utf-8")
            pending_files.append({
                "filename": file.filename,
                "content_b64": content_b64
            })
            filenames.append(file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file {file.filename}: {e!s}")

    scoped_thread_id = f"{user_id}:{thread_id}"

    async def event_generator():
        try:
            checkpointer = await get_checkpointer()
            graph = await build_graph_with_checkpointer(checkpointer)

            config: RunnableConfig = {"configurable": {"thread_id": scoped_thread_id}}

            # Format the trigger message so LLM knows files have been uploaded and can decide to call ingest_pdf
            filenames_str = ", ".join(f"`{name}`" for name in filenames)
            trigger_message = f"I've uploaded the following file(s): {filenames_str} — please index them."

            input_data = {
                "messages": [("user", trigger_message)],
                "user_id": user_id,
                "pending_upload": pending_files
            }

            async for msg_chunk, metadata in graph.astream(
                input_data, config=config, stream_mode="messages"
            ):
                content = getattr(msg_chunk, "content", msg_chunk)
                if isinstance(metadata, dict) and metadata.get("langgraph_node") == "chatbot" and content:
                    yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {e!s}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def handle_get_threads(user_id: str) -> list[dict]:
    """
    Retrieves all thread IDs for the authenticated user, ordered by most recently updated.
    Strips the user_id prefix before returning.
    """
    from psycopg.rows import dict_row

    from app.persistence.db import connection_pool

    query = """
        SELECT thread_id, max(checkpoint->>'ts') as last_updated
        FROM checkpoints
        WHERE thread_id LIKE %s
        GROUP BY thread_id
        ORDER BY last_updated DESC
    """

    # async with connection pool is responsible for acquiring and releasing a connection from the pool
    # a single `async with` statement is used with multiple contexts to optimize resource management
    # the query uses a parameterized LIKE clause to filter threads belonging to the user
    # the point of thse two loops was to strip the user_id prefix from the thread_id before returning it to the client

    # It runs a SQL query against Postgres asking "give me every row where the thread key starts with <user_id>:",
    # using a connection borrowed from the pool,
    # and pulls all the matching rows back as a list of dictionaries (one dict per row, column names as keys)
    async with connection_pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query, (f"{user_id}:%",))
        rows = await cur.fetchall()

    threads = []
    for row in rows:
        full_thread_id = row["thread_id"]
        last_updated = row["last_updated"]
        
        # Strip "{user_id}:" prefix
        if ":" in full_thread_id:
            _, actual_thread_id = full_thread_id.split(":", 1)
        else:
            actual_thread_id = full_thread_id

        threads.append({
            "thread_id": actual_thread_id,
            "updated_at": last_updated,
            "preview": f"Last updated: {last_updated}"
        })

    return threads


async def handle_get_history(thread_id: str, user_id: str) -> list[dict]:
    """
    Loads the full message history for a specific thread, verifies ownership,
    and returns it as a plain JSON list of {role, content} messages, in order.
    """
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required.")

    # Scope the thread to the authenticated user so one user can never read/write
    # another user's conversation just by guessing/reusing a thread_id.
    scoped_thread_id = f"{user_id}:{thread_id}"

    checkpointer = await get_checkpointer()
    graph = await build_graph_with_checkpointer(checkpointer)

    config: RunnableConfig = {"configurable": {"thread_id": scoped_thread_id}}

    # Load the state of the graph for this thread
    state = await graph.aget_state(config)

    # If the thread does not exist (or has no metadata/checkpoints), state.metadata is None.
    # Return 404 to verify the thread belongs to the requesting user and exists.
    if state.metadata is None:
        raise HTTPException(status_code=404, detail="Thread not found.")

    messages = state.values.get("messages", [])
    
    # Map messages to plain JSON list of {role, content}
    history = []
    for msg in messages:
        # standard mapping of roles
        role = "user"
        if msg.type == "human":
            role = "user"
        elif msg.type == "ai":
            role = "assistant"
        elif msg.type == "system":
            role = "system"
        elif msg.type == "tool":
            role = "tool"
        else:
            role = msg.type  # fallback

        history.append({
            "role": role,
            "content": msg.content
        })

    return history