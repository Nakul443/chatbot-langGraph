# file for request tracking and logging

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("uvicorn.error")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(f"Path: {request.url.path} | Method: {request.method} | Duration: {process_time:.4f}s | Status: {response.status_code}")

        return response