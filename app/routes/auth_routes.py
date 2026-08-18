from fastapi import APIRouter

from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse
from app.controllers.auth_controller import login_user, signup_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest) -> TokenResponse:
    return await signup_user(request.email, request.password)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    return await login_user(request.email, request.password)