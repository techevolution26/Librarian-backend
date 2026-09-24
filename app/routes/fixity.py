from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.preservation_event import PreservationEvent
from app.models.user import User
from app.schemas.fixity import FixityVerificationRead, ObjectFixityVerificationRead
from app.schemas.preservation_event import PreservationEventRead
from app.services.fixity import verify_asset_fixity

router = APIRouter(prefix="/fixity", tags=["preservation"])


def _read_event(row: PreservationEvent) -> PreservationEventRead:
    return PreservationEventRead.model_validate(row)


def _verify_asset(
    asset: BookAsset,
    object_id: int,
    current_user: User,
    db: Session,
    verified_at: datetime,
) -> FixityVerificationRead:
    expected = asset.checksum_sha256.strip().lower()
    if not expected:
        raise HTTPException(status_code=400, detail="Asset has no recorded checksum")

    try:
        matches, actual, detail = verify_asset_fixity(asset.storage_key, expected)
    except ValueError as exc:
        matches, actual, detail = False, None, str(exc)

    event = PreservationEvent(
        archival_object_id=object_id,
        asset_id=asset.id,
        event_type="fixity_check",
        event_date=verified_at,
        outcome="success" if matches else "failure",
        agent=current_user.full_name or f"user:{current_user.id}",
        detail=detail,
        source_storage_key=asset.storage_key,
        checksum=actual,
        checksum_algorithm="SHA-256",
    )
    db.add(event)
    db.flush()

    return FixityVerificationRead(
        asset_id=asset.id,
        archival_object_id=object_id,
        expected_checksum=expected,
        actual_checksum=actual,
        matches=matches,
        verified_at=verified_at,
        event=_read_event(event),
    )


@router.post("/admin/assets/{asset_id}/verify", response_model=FixityVerificationRead)
def verify_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FixityVerificationRead:
    require_admin_user(current_user)

    asset = db.scalar(select(BookAsset).where(BookAsset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    object_id = db.scalar(select(Book.archival_object_id).where(Book.id == asset.book_id))
    if object_id is None:
        raise HTTPException(status_code=400, detail="Asset is not linked to an archival object")

    verified_at = datetime.now(timezone.utc)
    result = _verify_asset(asset, object_id, current_user, db, verified_at)
    db.commit()
    return result


@router.post("/admin/objects/{object_id}/verify", response_model=ObjectFixityVerificationRead)
def verify_object_assets(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ObjectFixityVerificationRead:
    require_admin_user(current_user)

    if not db.scalar(select(ArchivalObject.id).where(ArchivalObject.id == object_id)):
        raise HTTPException(status_code=404, detail="Archival object not found")

    assets = db.scalars(
        select(BookAsset)
        .join(Book, Book.id == BookAsset.book_id)
        .where(Book.archival_object_id == object_id)
        .where(BookAsset.is_current.is_(True))
        .order_by(BookAsset.id)
    ).all()

    verified_at = datetime.now(timezone.utc)
    results: list[FixityVerificationRead] = []
    for asset in assets:
        try:
            results.append(_verify_asset(asset, object_id, current_user, db, verified_at))
        except HTTPException:
            # Preserve the append-only audit trail for an asset without a checksum.
            event = PreservationEvent(
                archival_object_id=object_id,
                asset_id=asset.id,
                event_type="fixity_check",
                event_date=verified_at,
                outcome="failure",
                agent=current_user.full_name or f"user:{current_user.id}",
                detail="Fixity verification could not run because the asset has no recorded checksum.",
                source_storage_key=asset.storage_key,
                checksum_algorithm="SHA-256",
            )
            db.add(event)
            db.flush()
            results.append(
                FixityVerificationRead(
                    asset_id=asset.id,
                    archival_object_id=object_id,
                    expected_checksum="",
                    actual_checksum=None,
                    matches=False,
                    verified_at=verified_at,
                    event=_read_event(event),
                )
            )

    db.commit()
    return ObjectFixityVerificationRead(
        archival_object_id=object_id,
        verified_at=verified_at,
        checked=len(results),
        passed=sum(result.matches for result in results),
        failed=sum(not result.matches for result in results),
        results=results,
    )
