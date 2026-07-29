# JWT-based authentication & session validation middleware.
# Expects: Authorization: Bearer <jwt>
# On success, attaches request.state.user_id so downstream code
# (routes/controllers) can scope data (e.g. thread_id ownership) to that user.

import os
import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization header."},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired."})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token."})

        user_id = payload.get("sub")
        if not user_id:
            return JSONResponse(
                status_code=401, content={"detail": "Token missing 'sub' (user id) claim."}
            )

        # Available to route handlers/controllers via request.state.user_id
        request.state.user_id = user_id

        return await call_next(request)