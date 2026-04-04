from pydantic import BaseModel, ConfigDict, EmailStr


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUserRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    plan: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)