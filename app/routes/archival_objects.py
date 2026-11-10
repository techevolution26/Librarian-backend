from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user, require_archival_curator
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_object import ArchivalObject
from app.models.archival_metadata import ArchivalMetadata
from app.models.archival_provenance import ArchivalProvenance
from app.models.archival_rights import ArchivalRights
from app.models.collection import Collection
from app.models.user import User
from app.schemas.archival_rights import ArchivalRightsReviewRequest
from app.services.admin_activity import log_admin_activity
from app.schemas.archival_object import (
    ArchivalObjectAdminRead,
    ArchivalObjectCreate,
    ArchivalObjectCuratorUpdate,
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
        curator_user_id=row.curator_user_id,
        visibility=row.visibility,
        archived_at=row.archived_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        book_id=row.book.id if row.book else None,
        metadata=row.intellectual_metadata,
        provenance=row.provenance,
        rights=row.rights,
    )


def _admin_read(row: ArchivalObject) -> ArchivalObjectAdminRead:
    return ArchivalObjectAdminRead.model_validate({**_read(row).model_dump(), "curator_user_id": row.curator_user_id})


@router.get("/", response_model=list[ArchivalObjectRead])
def list_archival_objects(db: Session = Depends(get_db)) -> list[ArchivalObjectRead]:
    rows = db.scalars(
        select(ArchivalObject)
        .where(ArchivalObject.archived_at.is_(None))
        .where(ArchivalObject.visibility == "published")
        .order_by(ArchivalObject.title.asc())
    ).all()
    return [_read(row) for row in rows]


@router.post("/admin", response_model=ArchivalObjectAdminRead, status_code=201)
def create_archival_object(
    payload: ArchivalObjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    require_admin_user(current_user)

    if db.scalar(select(ArchivalObject).where(ArchivalObject.identifier == payload.identifier)):
        raise HTTPException(status_code=409, detail="Archival object identifier already exists")
    if payload.curator_user_id is not None and not db.scalar(
        select(User).where(User.id == payload.curator_user_id, User.is_active.is_(True))
    ):
        raise HTTPException(status_code=404, detail="Curator user not found")
    if payload.collection_id is not None and not db.scalar(
        select(Collection).where(Collection.id == payload.collection_id, Collection.archived_at.is_(None))
    ):
        raise HTTPException(status_code=404, detail="Collection not found")

    row = ArchivalObject(
        identifier=payload.identifier.strip(),
        object_type=payload.object_type,
        title=payload.title.strip(),
        description=payload.description,
        collection_id=payload.collection_id,
        curator_user_id=payload.curator_user_id,
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
    return _admin_read(row)


@router.get("/admin/list", response_model=list[ArchivalObjectAdminRead])
def admin_list_archival_objects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ArchivalObjectAdminRead]:
    require_admin_user(current_user)
    rows = db.scalars(
        select(ArchivalObject).order_by(ArchivalObject.updated_at.desc(), ArchivalObject.id.desc())
    ).all()
    return [_admin_read(row) for row in rows]


@router.get("/admin/{object_id}", response_model=ArchivalObjectAdminRead)
def admin_get_archival_object(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    require_archival_curator(current_user, row.curator_user_id)
    return _admin_read(row)


@router.patch("/admin/{object_id}", response_model=ArchivalObjectAdminRead)
def update_archival_object(
    object_id: int,
    payload: ArchivalObjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    require_archival_curator(current_user, row.curator_user_id)

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
            raise HTTPException(status_code=409, detail="Archival object identifier already exists")
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
            row.intellectual_metadata = ArchivalMetadata(archival_object=row, **metadata_payload)
        else:
            for field, value in metadata_payload.items():
                setattr(row.intellectual_metadata, field, value)

    if provenance_payload is not None:
        if row.provenance is None:
            row.provenance = ArchivalProvenance(archival_object=row, **provenance_payload)
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
    return _admin_read(row)


@router.patch("/admin/{object_id}/archive", response_model=ArchivalObjectAdminRead)
def archive_archival_object(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    require_archival_curator(current_user, row.curator_user_id)
    if row.archived_at is None:
        row.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _admin_read(row)


@router.patch("/admin/{object_id}/curator", response_model=ArchivalObjectAdminRead)
def assign_archival_curator(
    object_id: int,
    payload: ArchivalObjectCuratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    """Assign or clear the explicit curator for an archival object.

    Only a global admin can delegate archival authority. A community member's
    Circle role never grants curator authority.
    """
    require_admin_user(current_user)
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")

    if payload.curator_user_id is not None:
        curator = db.scalar(
            select(User).where(User.id == payload.curator_user_id, User.is_active.is_(True))
        )
        if not curator:
            raise HTTPException(status_code=404, detail="Curator user not found")
        row.curator_user_id = curator.id
    else:
        row.curator_user_id = None

    db.add(row)
    db.commit()
    db.refresh(row)
    return _admin_read(row)




@router.post("/admin/{object_id}/rights-review", response_model=ArchivalObjectAdminRead)
def review_archival_rights(
    object_id: int,
    payload: ArchivalRightsReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalObjectAdminRead:
    """Record an explicit, auditable decision for online access to an object."""
    row = db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    require_archival_curator(current_user, row.curator_user_id)
    if payload.decision == "allow" and not (payload.rights_source and payload.rights_source.strip()):
        raise HTTPException(status_code=400, detail="An evidence source is required before approving online viewing")

    if row.rights is None:
        row.rights = ArchivalRights(archival_object=row)
    rights = row.rights
    rights.rights_statement = payload.rights_statement
    rights.rights_holder = payload.rights_holder
    rights.rights_source = payload.rights_source
    rights.license = payload.license
    rights.access_conditions = payload.access_conditions
    rights.reproduction_conditions = payload.reproduction_conditions
    rights.attribution = payload.attribution
    rights.notes = payload.notes
    rights.download_allowed = payload.download_allowed
    rights.redistribution_allowed = payload.redistribution_allowed
    rights.commercial_use_allowed = payload.commercial_use_allowed
    rights.view_allowed = True if payload.decision == "allow" else False if payload.decision == "deny" else None
    rights.verified_at = datetime.now(timezone.utc) if payload.decision != "pending" else None
    rights.verified_by = (current_user.full_name or f"user:{current_user.id}") if payload.decision != "pending" else None

    linked_book = row.book
    if payload.decision == "allow":
        row.visibility = "published" if linked_book and linked_book.visibility == "published" else "draft"
    elif payload.decision == "deny":
        row.visibility = "restricted"
    else:
        row.visibility = "draft"

    log_admin_activity(
        db,
        current_user,
        action="archival_object.rights_reviewed",
        entity_type="archival_object",
        entity_id=row.id,
        metadata={"decision": payload.decision, "book_id": linked_book.id if linked_book else None},
    )
    db.commit()
    db.refresh(row)
    return _admin_read(row)


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
def get_archival_object(object_id: int, db: Session = Depends(get_db)) -> ArchivalObjectRead:
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
