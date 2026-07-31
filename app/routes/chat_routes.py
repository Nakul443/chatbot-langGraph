# file to define the chat routes for the FastAPI application

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.controllers.chat_controller import handle_chat_stream

router = APIRouter(prefix="/chat", tags=["Chat"])

# this is the request model for the /chat/stream endpoint, which expects a JSON payload with a message and a thread_id
class ChatRequest(BaseModel):
    message: str
    thread_id: str

# POST: /chat/stream
@router.post("/stream")
async def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """
    HTTP route endpoint for streaming chat responses.
    business logic and graph execution sent to the chat controller
    `user_id` is set by AuthMiddleware after verifying the JWT
    """
    user_id = http_request.state.user_id # set by authMiddleware after JWT verification
    return await handle_chat_stream(request.message, request.thread_id, user_id)