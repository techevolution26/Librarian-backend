from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.settings import OnboardingPreferencesRead, OnboardingPreferencesUpdate, UserSettingsRead, UserSettingsUpdate
from app.models.user_settings import UserSettings

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


def ensure_user_settings(db: Session, user: User) -> UserSettings:
    if user.settings:
        return user.settings

    settings = UserSettings(
        user_id=user.id,
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
        preferred_genres=[],
        reading_goals=[],
        content_styles=[],
        preferred_lengths=[],
        weekly_target=None,
        onboarding_completed=False,
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)
    db.refresh(user)

    return settings



@router.get("/", response_model=UserSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsRead:
   settings = ensure_user_settings(db, current_user)
   return UserSettingsRead(
        account={
            "full_name": current_user.full_name,
            "email": current_user.email,
            "plan": current_user.plan,
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

@router.get("/onboarding", response_model=OnboardingPreferencesRead)
def get_onboarding_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingPreferencesRead:
    settings = ensure_user_settings(db, current_user)

    return OnboardingPreferencesRead(
        preferred_genres=settings.preferred_genres or [],
        reading_goals=settings.reading_goals or [],
        content_styles=settings.content_styles or [],
        preferred_lengths=settings.preferred_lengths or [],
        weekly_target=settings.weekly_target,
        onboarding_completed=settings.onboarding_completed,
    )


@router.patch("/onboarding", response_model=OnboardingPreferencesRead)
def update_onboarding_preferences(
    payload: OnboardingPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingPreferencesRead:
    settings = ensure_user_settings(db, current_user)

    settings.preferred_genres = payload.preferred_genres
    settings.reading_goals = payload.reading_goals
    settings.content_styles = payload.content_styles
    settings.preferred_lengths = payload.preferred_lengths
    settings.weekly_target = payload.weekly_target
    settings.onboarding_completed = payload.onboarding_completed

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return OnboardingPreferencesRead(
        preferred_genres=settings.preferred_genres or [],
        reading_goals=settings.reading_goals or [],
        content_styles=settings.content_styles or [],
        preferred_lengths=settings.preferred_lengths or [],
        weekly_target=settings.weekly_target,
        onboarding_completed=settings.onboarding_completed,
    )