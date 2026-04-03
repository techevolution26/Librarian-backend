from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def get_default_user_with_settings(db: Session) -> User:
    user = db.scalar(
        select(User)
        .options(joinedload(User.settings))
        .order_by(User.id)
    )
    if not user:
        raise HTTPException(status_code=404, detail="No user found")
    return user


@router.get("/", response_model=UserSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> UserSettingsRead:
    user = get_default_user_with_settings(db)

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


@router.patch("/", response_model=UserSettingsRead)
def update_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
) -> UserSettingsRead:
    user = get_default_user_with_settings(db)

    if not user.settings:
      raise HTTPException(status_code=404, detail="No settings found")

    settings = user.settings
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(settings, field, value)

    db.add(settings)
    db.commit()
    db.refresh(settings)
    db.refresh(user)

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