from fastapi import HTTPException
from psycopg.rows import dict_row

from app.auth.schemas import TokenResponse
from app.auth.security import create_access_token, hash_password, verify_password
from app.persistence.db import connection_pool


async def signup_user(email: str, password: str) -> TokenResponse:
    password_hash = hash_password(password)

    # Check if the email is already registered, and if not, insert the new user into the database.
    async with connection_pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = await cur.fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered.")

        await cur.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (email, password_hash),
        )
        row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create user.")

    user_id = str(row["id"])
    token = create_access_token(user_id)
    return TokenResponse(access_token=token)


async def login_user(email: str, password: str) -> TokenResponse:
    async with connection_pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, password_hash FROM users WHERE email = %s", (email,)
        )
        row = await cur.fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(str(row["id"]))
    return TokenResponse(access_token=token)