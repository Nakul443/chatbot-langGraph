# file to define the chat routes for the FastAPI application

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.controllers.chat_controller import (
    handle_chat_stream,
    handle_chat_upload,
    handle_get_history,
    handle_get_threads,
)

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


# POST: /chat/upload
@router.post("/upload")
async def chat_upload(
    http_request: Request,
    files: list[UploadFile] = File(...),
    thread_id: str = Form(...),
    message: str = Form(None)
) -> StreamingResponse:
    """
    HTTP route endpoint for uploading PDF files.
    Validates files, triggers the graph execution with the files payload
    in the state, and streams the response back to the client.
    `user_id` is set by AuthMiddleware after verifying the JWT.
    """
    user_id = http_request.state.user_id # set by authMiddleware after JWT verification
    return await handle_chat_upload(files, thread_id, user_id, message)


# GET: /chat/threads
@router.get("/threads")
async def get_threads(http_request: Request) -> list[dict]:
    """
    Retrieves the list of conversation threads for the authenticated user.
    """
    user_id = http_request.state.user_id
    return await handle_get_threads(user_id)


# GET: /chat/history/{thread_id}
@router.get("/history/{thread_id}")
async def get_history(thread_id: str, http_request: Request) -> list[dict]:
    """
    Retrieves the full message history for the specified thread.
    """
    user_id = http_request.state.user_id
    return await handle_get_history(thread_id, user_id)