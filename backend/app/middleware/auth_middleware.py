# JWT-based authentication & session validation middleware.
# Expects => Authorization: Bearer <jwt>
# On success, attaches request.state.user_id so downstream code
# (routes/controllers) can scope data (e.g. thread_id ownership) to that user.
# scope data means that the user_id is used to filter or validate access to resources in the database,
# ensuring that users can only access their own data or data they are authorized to view.

import os

import jwt
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

# Fetching secret dynamically inside dispatch or evaluating on load after load_dotenv
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


# jwt will be verified everywhere except these public paths, which are accessible without authentication
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc", "/auth/signup", "/auth/login", "/favicon.ico"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        # if this runs, we don't really need the JWT to avoid the chicken-egg problem
        # this line checks for the Authorization header and validates the JWT token.
        # If valid, it extracts the user_id and attaches it to request.state.user_id for downstream use.
        # If invalid or missing, it returns a 401 Unauthorized response.

        # the chicken-egg problem here would be that
        # if the JWT is required for all requests,
        # including the login/signup routes, then users wouldn't be able to obtain a JWT in the first place.
        # By allowing public access to certain paths,
        # we can avoid this issue and allow users to authenticate and obtain a JWT before accessing protected resources.

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