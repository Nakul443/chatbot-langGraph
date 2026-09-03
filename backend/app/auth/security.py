# Password hashing + JWT creation, shared by the auth routes and
# read by app/middleware/auth_middleware.py (must use the same secret/algorithm).

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

import bcrypt
import jwt

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # default 24h

def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain-text password against a bcrypt hash."""
    try:
        pwd_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(user_id: str) -> str:
    """
    Issues a JWT with `sub`=user_id, matching what
    app/middleware/auth_middleware.py expects on incoming requests.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)