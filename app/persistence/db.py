# database connection logic and session management

import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

load_dotenv()


DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# asynchronous connection pool for PostgreSQL
# autocommit=True is required: LangGraph's checkpointer.setup() runs
# `CREATE INDEX CONCURRENTLY`, which Postgres refuses to run inside a transaction.
connection_pool = AsyncConnectionPool(
    conninfo=DB_URI,
    max_size=20,
    open=False,
    kwargs={"autocommit": True},
)

async def get_checkpointer() -> AsyncPostgresSaver:
    """
    Creates and returns an instance of AsyncPostgresSaver using the connection pool.
    """
    checkpointer = AsyncPostgresSaver(connection_pool)
    return checkpointer