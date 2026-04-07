from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.auth import AuthUserRead, LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def build_default_user_settings(user_id: int) -> UserSettings:
    return UserSettings(
        user_id=user_id,
        theme="dark",
        density="comfortable",
        reading_mode="scroll",
        font_size="medium",
        line_height="comfortable",
        auto_bookmark=True,
        show_progress_bar=True,
        email_updates=True,
        reading_reminders=True,
        product_announcements=False,
        profile_visibility="private",
        share_reading_activity=False,
    )


@router.post("/signup", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
) -> AuthUserRead:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    try:
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            plan="free",
            is_active=True,
        )
        db.add(user)
        db.flush()  # ensures user.id is available before creating settings

        settings = build_default_user_settings(user.id)
        db.add(settings)

        db.commit()
        db.refresh(user)

        return AuthUserRead.model_validate(user)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already in use") from exc
    except Exception:
        db.rollback()
        raise


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    token = create_access_token(user.id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )


@router.get("/me", response_model=AuthUserRead)
def me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    return AuthUserRead.model_validate(current_user)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="none",
        secure=True,
    )
    return {"status": "ok"}