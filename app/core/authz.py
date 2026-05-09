from fastapi import HTTPException

from app.models.user import User


def require_admin_user(user: User) -> None:
    if getattr(user, "role", "USER") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")