from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.library_item import LibraryItem
from app.models.user import User
from app.schemas.book import BookRead
from app.schemas.profile import (
    ActivityItem,
    ProfileStat,
    ReadingProgressItem,
    UserProfileRead,
    UserProfileUpdate,
)

router = APIRouter(prefix="/profile", tags=["profile"])

AVATAR_STORAGE_DIR = Path("storage/avatars")
AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def load_library_rows(db: Session, user_id: int) -> list[LibraryItem]:
    return db.scalars(
        select(LibraryItem)
        .where(LibraryItem.user_id == user_id)
        .options(joinedload(LibraryItem.book))
        .order_by(LibraryItem.updated_at.desc(), LibraryItem.id.desc())
    ).all()


def build_profile_response(user: User, library_rows: list[LibraryItem]) -> UserProfileRead:
    favorite_books = [row.book for row in library_rows[:6]]
    recent_books = [row.book for row in library_rows[:4]]
    reading_rows = [row for row in library_rows if row.status == "reading"][:4]

    pages_read = sum(
        round((row.book.pages or 0) * ((row.progress or 0) / 100))
        for row in reading_rows
    )
    avg_rating = (
        round(sum(row.book.rating for row in library_rows) / len(library_rows), 1)
        if library_rows
        else 0.0
    )

    suggested_book = (
        favorite_books[1]
        if len(favorite_books) > 1
        else (favorite_books[0] if favorite_books else None)
    )

    return UserProfileRead(
        name=user.full_name,
        email=user.email,
        plan=user.plan,
        avatar=user.avatar_url,
        member_since="2026",
        library_status="Active",
        reading_mode=user.settings.reading_mode if user.settings else "scroll",
        preferences=["Productivity", "Business", "Mindset", "Design", "Non-fiction"],
        stats=[
            ProfileStat(label="Books saved", value=str(len(library_rows))),
            ProfileStat(label="Pages read", value=f"{pages_read:,}"),
            ProfileStat(label="Reading streak", value="7 days"),
            ProfileStat(label="Avg rating", value=str(avg_rating)),
        ],
        favorite_books=[BookRead.model_validate(book) for book in favorite_books],
        recent_books=[BookRead.model_validate(book) for book in recent_books],
        reading_progress=[
            ReadingProgressItem(
                id=row.book.id,
                title=row.book.title,
                progress=row.progress,
            )
            for row in reading_rows
        ],
        suggested_book=BookRead.model_validate(suggested_book) if suggested_book else None,
        recent_activity=[
            ActivityItem(
                id=row.book.id,
                title=row.book.title,
                action="Opened today" if index == 0 else "Viewed recently",
                href=f"/book/{row.book.id}",
            )
            for index, row in enumerate(library_rows[:4])
        ],
    )


@router.get("/", response_model=UserProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    db.refresh(current_user, attribute_names=["settings"])
    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(current_user, library_rows)


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

    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(current_user, library_rows)


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

    library_rows = load_library_rows(db, current_user.id)
    return build_profile_response(current_user, library_rows)