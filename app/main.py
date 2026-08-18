# fastAPI gateway
# manages application lifecycle (opening and closing the database connection pool)
# initializes the compiled graph with the AsyncPostgresSaver checkpointer,
# and provides an asynchronous endpoint that streams the chat responses back token-by-token using Server-Sent Events (SSE)

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.persistence.db import connection_pool, create_users_table, get_checkpointer
from app.routes.auth_routes import router as auth_router
from app.routes.chat_routes import router as chat_router


# this is the main entrypoint for the FastAPI application, which is run by uvicorn in production
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager. 
    Opens the PostgreSQL connection pool and sets up checkpointer + users tables on startup,
    then safely closes the pool on shutdown.
    """
    await connection_pool.open()

    # builds an AsyncPostgresSaver checkpointer and sets up the necessary tables in the database
    checkpointer = await get_checkpointer()
    await checkpointer.setup() # creates checkpoint tables if they don't exist

    await create_users_table()  # creates the users table (for signup/login) if it doesn't exist

    yield
    
    await connection_pool.close()

# initialising fastAPI application with title and lifespan context manager
app = FastAPI(title="LangGraph MCP Chatbot API", lifespan=lifespan)

# middleware for logging requests and handling authentication
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthMiddleware)

# include routers
app.include_router(chat_router)
app.include_router(auth_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "langgraph-mcp-chatbot"}