import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.library_item import LibraryItem
from app.models.user import User
from app.schemas.book import BookRead
from app.schemas.profile import (
    ActivityItem,
    ProfileStat,
    ReadingProgressItem,
    SidebarSummaryRead,
    UserProfileRead,
    UserProfileUpdate,
)

router = APIRouter(prefix="/profile", tags=["profile"])

STORAGE_ROOT = Path(os.getenv("STORAGE_DIR", "./storage"))
AVATAR_STORAGE_DIR = STORAGE_ROOT / "avatars"
AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def load_library_rows(db: Session, user_id: int) -> list[LibraryItem]:
    return db.scalars(
        select(LibraryItem)
        .where(LibraryItem.user_id == user_id)
        .options(joinedload(LibraryItem.book))
        .order_by(LibraryItem.updated_at.desc(), LibraryItem.id.desc())
    ).all()


def calculate_reading_streak_days(library_rows: list[LibraryItem]) -> int:
    read_dates = {
        row.last_read_at.astimezone(timezone.utc).date()
        for row in library_rows
        if row.last_read_at is not None
    }

    if not read_dates:
        return 0

    today = datetime.now(timezone.utc).date()

    # If user read yesterday but not today, still show the active streak.
    current = today if today in read_dates else today - timedelta(days=1)

    streak = 0
    while current in read_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


def build_user_preferences(user: User) -> list[str]:
    if not user.settings:
        return []

    values: list[str] = []

    values.extend(user.settings.preferred_genres or [])
    values.extend(user.settings.reading_goals or [])
    values.extend(user.settings.content_styles or [])
    values.extend(user.settings.preferred_lengths or [])

    if user.settings.weekly_target:
        values.append(user.settings.weekly_target)

    return list(dict.fromkeys(values))


def get_member_since(user: User) -> str:
    created_at = getattr(user, "created_at", None)

    if isinstance(created_at, datetime):
        return str(created_at.year)

    return "New"


def get_library_status(library_rows: list[LibraryItem]) -> str:
    if not library_rows:
        return "Getting started"

    if any(row.status == "reading" for row in library_rows):
        return "Reading"

    if any(row.status == "finished" for row in library_rows):
        return "Active"

    return "Saved"


def get_pages_read(library_rows: list[LibraryItem]) -> int:
    total = 0

    for row in library_rows:
        pages = row.book.pages or 0
        progress = row.progress or 0

        if row.status == "finished":
            total += pages
        else:
            total += round(pages * (progress / 100))

    return total


def get_average_rating(library_rows: list[LibraryItem]) -> float:
    rated_rows = [
        row for row in library_rows
        if row.book is not None and row.book.rating is not None
    ]

    if not rated_rows:
        return 0.0

    return round(
        sum(row.book.rating for row in rated_rows) / len(rated_rows),
        1,
    )


def get_recent_action(row: LibraryItem, index: int) -> str:
    if row.status == "finished":
        return "Finished recently"

    if row.status == "reading":
        return "Reading now"

    if row.status == "saved":
        return "Saved for later"

    return "Viewed recently" if index > 0 else "Opened recently"


def pick_suggested_book(
    db: Session,
    user: User,
    library_rows: list[LibraryItem],
) -> Book | None:
    library_book_ids = {row.book_id for row in library_rows}
    preferred_genres = set()

    if user.settings:
        preferred_genres = {
            genre.lower()
            for genre in (user.settings.preferred_genres or [])
        }

    candidates = db.scalars(
        select(Book)
        .order_by(Book.rating.desc(), Book.id.desc())
        .limit(50)
    ).all()

    for book in candidates:
        if book.id in library_book_ids:
            continue

        book_genres = {genre.lower() for genre in book.genres}
        if preferred_genres and preferred_genres.intersection(book_genres):
            return book

    for book in candidates:
        if book.id not in library_book_ids:
            return book

    return library_rows[0].book if library_rows else None


def build_profile_response(
    db: Session,
    user: User,
    library_rows: list[LibraryItem],
) -> UserProfileRead:
    favorite_books = [row.book for row in library_rows[:6] if row.book is not None]
    recent_books = [row.book for row in library_rows[:4] if row.book is not None]
    reading_rows = [
        row for row in library_rows
        if row.status == "reading" and row.book is not None
    ][:4]

    pages_read = get_pages_read(library_rows)
    avg_rating = get_average_rating(library_rows)
    streak = calculate_reading_streak_days(library_rows)
    preferences = build_user_preferences(user)
    suggested_book = pick_suggested_book(db, user, library_rows)

    return UserProfileRead(
        name=user.full_name,
        email=user.email,
        plan=user.plan,
        avatar=user.avatar_url,
        member_since=get_member_since(user),
        library_status=get_library_status(library_rows),
        reading_mode=user.settings.reading_mode if user.settings else "scroll",
        preferences=(
            user.settings.preferred_genres
            if user.settings and user.settings.preferred_genres
            else []
            ),
        stats=[
            ProfileStat(label="Books saved", value=str(len(library_rows))),
            ProfileStat(label="Pages read", value=f"{pages_read:,}"),
            ProfileStat(label="Reading streak", value=f"{streak} days"),
            ProfileStat(label="Avg rating", value=f"{avg_rating:.1f}"),
        ],
        favorite_books=[
            BookRead.model_validate(book)
            for book in favorite_books
        ],
        recent_books=[
            BookRead.model_validate(book)
            for book in recent_books
        ],
        reading_progress=[
            ReadingProgressItem(
                id=row.book.id,
                title=row.book.title,
                progress=row.progress or 0,
            )
            for row in reading_rows
        ],
        suggested_book=(
            BookRead.model_validate(suggested_book)
            if suggested_book
            else None
        ),
        recent_activity=[
            ActivityItem(
                id=row.book.id,
                title=row.book.title,
                action=get_recent_action(row, index),
                href=f"/book/{row.book.id}",
            )
            for index, row in enumerate(library_rows[:4])
            if row.book is not None
        ],
    )


@router.get("/", response_model=UserProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    db.refresh(current_user, attribute_names=["settings"])
    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(db, current_user, library_rows)


@router.patch("/", response_model=UserProfileRead)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates:
        existing = db.scalar(
            select(User).where(
                User.email == updates["email"],
                User.id != current_user.id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")

    for field, value in updates.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    db.refresh(current_user, attribute_names=["settings"])

    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(db, current_user, library_rows)


@router.post("/avatar", response_model=UserProfileRead)
async def upload_avatar(
    request: Request,
    avatar_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    if avatar_file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(
            status_code=400,
            detail="Avatar must be PNG, JPEG, or WEBP",
        )

    suffix = Path(avatar_file.filename or "avatar").suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = AVATAR_STORAGE_DIR / filename

    file_bytes = await avatar_file.read()
    destination.write_bytes(file_bytes)

    avatar_url = str(request.base_url).rstrip("/") + f"/static/avatars/{filename}"
    current_user.avatar_url = avatar_url

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    db.refresh(current_user, attribute_names=["settings"])

    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(db, current_user, library_rows)


@router.get("/sidebar-summary", response_model=SidebarSummaryRead)
def get_sidebar_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SidebarSummaryRead:
    library_rows = load_library_rows(db, current_user.id)
    streak = calculate_reading_streak_days(library_rows)

    return SidebarSummaryRead(
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        reading_streak_days=streak,
    )