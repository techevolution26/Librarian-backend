from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.collection import Collection
from app.models.user import User
from app.schemas.collection import CollectionCreate, CollectionRead, CollectionUpdate

router = APIRouter(prefix="/collections", tags=["collections"])


def _read(row: Collection) -> CollectionRead:
    return CollectionRead(
        id=row.id,
        identifier=row.identifier,
        title=row.title,
        description=row.description,
        curator=row.curator,
        institution=row.institution,
        geographic_scope=row.geographic_scope,
        date_start=row.date_start,
        date_end=row.date_end,
        subjects=row.subjects,
        rights_statement=row.rights_statement,
        visibility=row.visibility,
        archived_at=row.archived_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/admin", response_model=CollectionRead, status_code=201)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    require_admin_user(current_user)

    existing = db.scalar(select(Collection).where(Collection.identifier == payload.identifier))
    if existing:
        raise HTTPException(status_code=409, detail="Collection identifier already exists")

    row = Collection(
        identifier=payload.identifier.strip(),
        title=payload.title.strip(),
        description=payload.description,
        curator=payload.curator,
        institution=payload.institution,
        geographic_scope=payload.geographic_scope,
        date_start=payload.date_start,
        date_end=payload.date_end,
        subjects=payload.subjects,
        rights_statement=payload.rights_statement,
        visibility=payload.visibility,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.get("/admin/list", response_model=list[CollectionRead])
def admin_list_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionRead]:
    require_admin_user(current_user)

    rows = db.scalars(
        select(Collection).order_by(Collection.updated_at.desc(), Collection.id.desc())
    ).all()
    return [_read(row) for row in rows]


@router.patch("/admin/{collection_id}", response_model=CollectionRead)
def update_collection(
    collection_id: int,
    payload: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    require_admin_user(current_user)

    row = db.scalar(select(Collection).where(Collection.id == collection_id))
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")

    updates = payload.model_dump(exclude_unset=True)
    if "identifier" in updates:
        existing = db.scalar(
            select(Collection).where(
                Collection.identifier == updates["identifier"].strip(),
                Collection.id != collection_id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Collection identifier already exists")
        updates["identifier"] = updates["identifier"].strip()
    if "title" in updates:
        updates["title"] = updates["title"].strip()

    for field, value in updates.items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return _read(row)


@router.patch("/admin/{collection_id}/archive", response_model=CollectionRead)
def archive_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    require_admin_user(current_user)

    row = db.scalar(select(Collection).where(Collection.id == collection_id))
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")
    if row.archived_at is None:
        row.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _read(row)

@router.get("/", response_model=list[CollectionRead])
def list_collections(db: Session = Depends(get_db)) -> list[CollectionRead]:
    rows = db.scalars(
        select(Collection)
        .where(Collection.archived_at.is_(None))
        .where(Collection.visibility == "published")
        .order_by(Collection.title.asc())
    ).all()
    return [_read(row) for row in rows]


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(collection_id: int, db: Session = Depends(get_db)) -> CollectionRead:
    row = db.scalar(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.archived_at.is_(None),
            Collection.visibility == "published",
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _read(row)


