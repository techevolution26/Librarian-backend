from fastapi import HTTPException

from app.models.user import User


def require_admin_user(user: User) -> None:
    if getattr(user, "role", "USER") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

def require_archival_curator(user: User, curator_user_id: int | None) -> None:
    """Allow global admins or the curator explicitly assigned to an object.

    Community membership, annotation, and discussion permissions never satisfy
    this check. Archival mutation remains an explicit authority boundary.
    """
    if getattr(user, "role", "USER") == "ADMIN":
        return
    if curator_user_id != user.id:
        raise HTTPException(status_code=403, detail="Archival curator access required")
