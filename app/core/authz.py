from fastapi import HTTPException

from app.models.user import User


def require_admin_user(user: User) -> None:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")