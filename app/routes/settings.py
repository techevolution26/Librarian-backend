from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def build_settings_response(user: User) -> UserSettingsRead:
    if not user.settings:
        raise HTTPException(status_code=404, detail="No settings found")

    settings = user.settings

    return UserSettingsRead(
        account={
            "full_name": user.full_name,
            "email": user.email,
            "plan": user.plan,
        },
        appearance={
            "theme": settings.theme,
            "density": settings.density,
            "reading_mode": settings.reading_mode,
        },
        reading={
            "font_size": settings.font_size,
            "line_height": settings.line_height,
            "auto_bookmark": settings.auto_bookmark,
            "show_progress_bar": settings.show_progress_bar,
        },
        notifications={
            "email_updates": settings.email_updates,
            "reading_reminders": settings.reading_reminders,
            "product_announcements": settings.product_announcements,
        },
        privacy={
            "profile_visibility": settings.profile_visibility,
            "share_reading_activity": settings.share_reading_activity,
        },
    )


@router.get("/", response_model=UserSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsRead:
    db.refresh(current_user, attribute_names=["settings"])
    return build_settings_response(current_user)


@router.patch("/", response_model=UserSettingsRead)
def update_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsRead:
    db.refresh(current_user, attribute_names=["settings"])

    if not current_user.settings:
        raise HTTPException(status_code=404, detail="No settings found")

    settings = current_user.settings
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(settings, field, value)

    db.add(settings)
    db.commit()
    db.refresh(settings)
    db.refresh(current_user)

    return build_settings_response(current_user)