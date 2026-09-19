from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUserRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    plan: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)