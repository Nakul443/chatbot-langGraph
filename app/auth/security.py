# Password hashing + JWT creation, shared by the auth routes and
# read by app/middleware/auth_middleware.py (must use the same secret/algorithm).

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # default 24h

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, key_hex = password_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return secrets.compare_digest(key, new_key)
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