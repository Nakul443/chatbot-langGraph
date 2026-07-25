# fastAPI gateway
# manages application lifecycle (opening and closing the database connection pool)
# initializes the compiled graph with the AsyncPostgresSaver checkpointer,
# and provides an asynchronous endpoint that streams the chat responses back token-by-token using Server-Sent Events (SSE)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.persistence.db import connection_pool, get_checkpointer
from app.routes.chat_routes import router as chat_router
from app.middleware.logging_middleware import RequestLoggingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager. 
    Opens the PostgreSQL connection pool and sets up checkpointer tables on startup,
    then safely closes the pool on shutdown.
    """
    await connection_pool.open()
    
    async with await get_checkpointer() as checkpointer:
        await checkpointer.setup()
        
    yield
    
    await connection_pool.close()

# Initialize FastAPI application with lifespan
app = FastAPI(title="LangGraph MCP Chatbot API", lifespan=lifespan)

# Register custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(chat_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "langgraph-mcp-chatbot"}