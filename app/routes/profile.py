from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
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

# Storage configuration
AVATAR_STORAGE_DIR = Path("storage/avatars")
AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# --- Helpers ---

def get_default_user(db: Session) -> User:
    """Fetch the primary user for the demo/profile."""
    user = db.scalar(
        select(User)
        .options(joinedload(User.settings))
        .order_by(User.id)
    )
    if not user:
        raise HTTPException(status_code=404, detail="No user found")
    return user

def load_library_rows(db: Session, user_id: int) -> list[LibraryItem]:
    """Fetch user library items with book details."""
    return db.scalars(
        select(LibraryItem)
        .where(LibraryItem.user_id == user_id)
        .options(joinedload(LibraryItem.book))
        .order_by(LibraryItem.updated_at.desc(), LibraryItem.id.desc())
    ).all()

def build_profile_response(user: User, library_rows: list[LibraryItem]) -> UserProfileRead:
    """Transforms database models into the complex UserProfileRead schema."""
    favorite_books = [row.book for row in library_rows[:6]]
    recent_books = [row.book for row in library_rows[:4]]
    reading_rows = [row for row in library_rows if row.status == "reading"][:4]

    # Calculate stats
    pages_read = sum(
        round((row.book.pages or 0) * ((row.progress or 0) / 100))
        for row in reading_rows
    )
    avg_rating = (
        round(sum(row.book.rating for row in library_rows) / len(library_rows), 1)
        if library_rows
        else 0.0
    )

    # Pick a suggested book from favorites
    suggested_book = favorite_books[1] if len(favorite_books) > 1 else (
        favorite_books[0] if favorite_books else None
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

# --- Routes ---

@router.get("/", response_model=UserProfileRead)
def get_profile(db: Session = Depends(get_db)) -> UserProfileRead:
    user = get_default_user(db)
    library_rows = load_library_rows(db, user.id)
    return build_profile_response(user, library_rows)

@router.patch("/", response_model=UserProfileRead)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> UserProfileRead:
    user = get_default_user(db)
    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates:
        existing = db.scalar(
            select(User).where(User.email == updates["email"], User.id != user.id)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")

    for field, value in updates.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)

    library_rows = load_library_rows(db, user.id)
    return build_profile_response(user, library_rows)

@router.post("/avatar", response_model=UserProfileRead)
async def upload_avatar(
    request: Request,
    avatar_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    user = get_default_user(db)

    if avatar_file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(
            status_code=400,
            detail="Avatar must be PNG, JPEG, or WEBP",
        )

    # Save file
    suffix = Path(avatar_file.filename or "avatar").suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = AVATAR_STORAGE_DIR / filename

    file_bytes = await avatar_file.read()
    destination.write_bytes(file_bytes)

    # Update user URL
    avatar_url = str(request.base_url).rstrip("/") + f"/static/avatars/{filename}"
    user.avatar_url = avatar_url

    db.add(user)
    db.commit()
    db.refresh(user)

    library_rows = load_library_rows(db, user.id)
    return build_profile_response(user, library_rows)
