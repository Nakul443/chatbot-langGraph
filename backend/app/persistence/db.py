# database connection logic and session management

import os

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow
from psycopg_pool import AsyncConnectionPool

load_dotenv()

DB_URI = os.getenv("DATABASE_URL", "")

# asynchronous connection pool for PostgreSQL
# autocommit=True is required: LangGraph's checkpointer.setup() runs
# `CREATE INDEX CONCURRENTLY`, which Postgres refuses to run inside a transaction.
#
# Explicitly typed as AsyncConnectionPool[AsyncConnection[DictRow]] to match what
# AsyncPostgresSaver expects (its internal Conn = AsyncConnection[DictRow] | AsyncConnectionPool[AsyncConnection[DictRow]]).
# Without this annotation, static checkers infer a generic/untyped pool and flag a mismatch --
# at runtime it's a non-issue since AsyncPostgresSaver forces row_factory=dict_row on every
# cursor it opens itself, regardless of the pool's default row type.
connection_pool: AsyncConnectionPool[AsyncConnection[DictRow]] = AsyncConnectionPool(
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


async def create_users_table():
    """
    Creates the users table (id, email, password_hash) if it doesn't exist.
    Called once at app startup, alongside checkpointer.setup().
    """
    async with connection_pool.connection() as conn:
        # gen_random_uuid() requires pgcrypto (trusted extension, no superuser needed on PG13+)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )