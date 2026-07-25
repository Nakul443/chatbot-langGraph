# fastAPI gateway
# manages application lifecycle (opening and closing the database connection pool)
# initializes the compiled graph with the AsyncPostgresSaver checkpointer,
# and provides an asynchronous endpoint that streams the chat responses back token-by-token using Server-Sent Events (SSE)


import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from app.persistence.db import connection_pool, get_checkpointer
from app.graph.builder import build_graph_with_checkpointer

load_dotenv()

# request body schema for the /chat/stream endpoint
class ChatRequest(BaseModel):
    message: str
    thread_id: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager. 
    Opens the PostgreSQL connection pool and sets up checkpointer tables on startup,
    then safely closes the pool on shutdown.
    """
    # opening the connection pool
    await connection_pool.open()
    
    # initialize checkpoint tables in PostgreSQL if they don't exist yet
    async with await get_checkpointer() as checkpointer:
        await checkpointer.setup()
        
    yield
    # yield saves the function's internal state (variables and execution spot)
    # when the generator is called again, it resumes exactly where it left off
    
    # Close connection pool on application shutdown
    await connection_pool.close()

# Initialize FastAPI application with the lifespan handler
app = FastAPI(title="LangGraph MCP Chatbot API", lifespan=lifespan)

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    API endpoint that receives a message and thread_id, 
    resumes the LangGraph state from PostgreSQL, runs the graph, 
    and streams the response tokens back via Server-Sent Events (SSE).
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    if not request.thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required for state management.")

    async def event_generator():
        try:
            # 1. Instantiate the checkpointer and compile the graph for this request
            async with await get_checkpointer() as checkpointer:
                graph = await build_graph_with_checkpointer(checkpointer)
                
                # 2. Configure thread isolation
                config = {"configurable": {"thread_id": request.thread_id}}
                
                # 3. Format input payload for the graph state
                input_data = {"messages": [("user", request.message)]}
                
                # 4. Stream graph node outputs asynchronously
                # mode="updates" streams changes as nodes execute
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "langgraph-mcp-chatbot"}