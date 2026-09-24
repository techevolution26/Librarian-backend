from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_object import ArchivalObject
from app.models.archival_metadata import ArchivalMetadata
from app.models.archival_provenance import ArchivalProvenance
from app.models.archival_rights import ArchivalRights
from app.models.collection import Collection
from app.models.user import User
from app.schemas.archival_object import (
    ArchivalObjectCreate,
    ArchivalObjectRead,
    ArchivalObjectUpdate,
)

router = APIRouter(prefix="/archival-objects", tags=["archival-objects"])


def _read(row: ArchivalObject) -> ArchivalObjectRead:
    return ArchivalObjectRead(
        id=row.id,
        identifier=row.identifier,
        persistent_identifier=row.persistent_identifier,
        object_type=row.object_type,
        title=row.title,
        description=row.description,
        collection_id=row.collection_id,
        visibility=row.visibility,
        archived_at=row.archived_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        book_id=row.book.id if row.book else None,
        metadata=row.intellectual_metadata,
        provenance=row.provenance,
        rights=row.rights,
    )


@router.get("/", response_model=list[ArchivalObjectRead])
def list_archival_objects(db: Session = Depends(get_db)) -> list[ArchivalObjectRead]:
    rows = db.scalars(
        select(ArchivalObject)
        .where(ArchivalObject.archived_at.is_(None))
        .where(ArchivalObject.visibility == "published")
        .order_by(ArchivalObject.title.asc())
    ).all()
    return [_read(row) for row in rows]


@router.post("/admin", response_model=ArchivalObjectRead, status_code=201)
def create_archival_object(
    payload: ArchivalObjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectRead:
    require_admin_user(current_user)

    if db.scalar(
        select(ArchivalObject).where(ArchivalObject.identifier == payload.identifier)
    ):
        raise HTTPException(
            status_code=409, detail="Archival object identifier already exists"
        )
    if payload.collection_id is not None and not db.scalar(
        select(Collection).where(
            Collection.id == payload.collection_id, Collection.archived_at.is_(None)
        )
    ):
        raise HTTPException(status_code=404, detail="Collection not found")

    row = ArchivalObject(
        identifier=payload.identifier.strip(),
        object_type=payload.object_type,
        title=payload.title.strip(),
        description=payload.description,
        collection_id=payload.collection_id,
        visibility=payload.visibility,
    )
    if payload.metadata is not None:
        row.intellectual_metadata = ArchivalMetadata(**payload.metadata.model_dump())
    if payload.provenance is not None:
        row.provenance = ArchivalProvenance(**payload.provenance.model_dump())
    if payload.rights is not None:
        row.rights = ArchivalRights(**payload.rights.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.get("/admin/list", response_model=list[ArchivalObjectRead])
def admin_list_archival_objects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ArchivalObjectRead]:
    require_admin_user(current_user)
    rows = db.scalars(
        select(ArchivalObject).order_by(
            ArchivalObject.updated_at.desc(), ArchivalObject.id.desc()
        )
    ).all()
    return [_read(row) for row in rows]


@router.patch("/admin/{object_id}", response_model=ArchivalObjectRead)
def update_archival_object(
    object_id: int,
    payload: ArchivalObjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectRead:
    require_admin_user(current_user)
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")

    updates = payload.model_dump(exclude_unset=True)
    metadata_payload = updates.pop("metadata", None)
    provenance_payload = updates.pop("provenance", None)
    rights_payload = updates.pop("rights", None)
    if "identifier" in updates:
        identifier = updates["identifier"].strip()
        if db.scalar(
            select(ArchivalObject).where(
                ArchivalObject.identifier == identifier,
                ArchivalObject.id != object_id,
            )
        ):
            raise HTTPException(
                status_code=409, detail="Archival object identifier already exists"
            )
        updates["identifier"] = identifier
    if "title" in updates:
        updates["title"] = updates["title"].strip()
    if "collection_id" in updates and updates["collection_id"] is not None:
        if not db.scalar(
            select(Collection).where(
                Collection.id == updates["collection_id"],
                Collection.archived_at.is_(None),
            )
        ):
            raise HTTPException(status_code=404, detail="Collection not found")

    for field, value in updates.items():
        setattr(row, field, value)

    if metadata_payload is not None:
        if row.intellectual_metadata is None:
            row.intellectual_metadata = ArchivalMetadata(
                archival_object=row, **metadata_payload
            )
        else:
            for field, value in metadata_payload.items():
                setattr(row.intellectual_metadata, field, value)

    if provenance_payload is not None:
        if row.provenance is None:
            row.provenance = ArchivalProvenance(
                archival_object=row, **provenance_payload
            )
        else:
            for field, value in provenance_payload.items():
                setattr(row.provenance, field, value)

    if rights_payload is not None:
        if row.rights is None:
            row.rights = ArchivalRights(archival_object=row, **rights_payload)
        else:
            for field, value in rights_payload.items():
                setattr(row.rights, field, value)

    db.commit()
    db.refresh(row)
    return _read(row)


@router.patch("/admin/{object_id}/archive", response_model=ArchivalObjectRead)
def archive_archival_object(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectRead:
    require_admin_user(current_user)
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    if row.archived_at is None:
        row.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _read(row)


@router.get("/pid/{persistent_identifier}", response_model=ArchivalObjectRead)
def get_archival_object_by_persistent_identifier(
    persistent_identifier: str, db: Session = Depends(get_db)
) -> ArchivalObjectRead:
    row = db.scalar(
        select(ArchivalObject).where(
            ArchivalObject.persistent_identifier == persistent_identifier,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    return _read(row)


@router.get("/{object_id}", response_model=ArchivalObjectRead)
def get_archival_object(
    object_id: int, db: Session = Depends(get_db)
) -> ArchivalObjectRead:
    row = db.scalar(
        select(ArchivalObject).where(
            ArchivalObject.id == object_id,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    return _read(row)
