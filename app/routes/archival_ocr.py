from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.archival_ocr import ArchivalOCRPage
from app.models.book_asset import BookAsset
from app.models.preservation_event import PreservationEvent
from app.models.user import User
from app.schemas.archival_ocr import ArchivalOCRGenerateRequest, ArchivalOCRRead
from app.services.archival_ocr import extract_text, resolve_image, tesseract_version
from app.services.fixity import verify_asset_fixity

router = APIRouter(prefix="/archival-objects", tags=["archival-ocr"])


def _public_canvas(canvas_id: int, db: Session) -> tuple[ArchivalObject, ArchivalCanvas, BookAsset]:
    canvas = db.scalar(
        select(ArchivalCanvas)
        .join(ArchivalObject, ArchivalCanvas.archival_object_id == ArchivalObject.id)
        .join(BookAsset, ArchivalCanvas.asset_id == BookAsset.id)
        .options(selectinload(ArchivalCanvas.archival_object), selectinload(ArchivalCanvas.asset))
        .where(
            ArchivalCanvas.id == canvas_id,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
            BookAsset.mime_type.like("image/%"),
        )
    )
    if not canvas or not canvas.asset:
        raise HTTPException(status_code=404, detail="Archival canvas not found")
    return canvas.archival_object, canvas, canvas.asset


def _verify_source(asset: BookAsset, object_id: int) -> tuple[bool, str | None, str]:
    expected = asset.checksum_sha256.strip().lower()
    if not expected:
        return False, None, "Source asset has no recorded SHA-256 checksum"
    try:
        return verify_asset_fixity(asset.storage_key, expected)
    except (FileNotFoundError, ValueError) as exc:
        return False, None, str(exc)


@router.get("/{object_id}/canvases/{canvas_identifier}/ocr", response_model=list[ArchivalOCRRead])
def list_canvas_ocr(
    object_id: int,
    canvas_identifier: str,
    db: Session = Depends(get_db),
) -> list[ArchivalOCRRead]:
    canvas = db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.canvas_identifier == canvas_identifier))
    if not canvas:
        raise HTTPException(status_code=404, detail="Archival canvas not found")
    obj, canvas, _ = _public_canvas(canvas.id, db)
    if obj.id != object_id:
        raise HTTPException(status_code=404, detail="Archival canvas not found")
    if obj.rights and obj.rights.view_allowed is False:
        raise HTTPException(status_code=403, detail="OCR for this archival object is not publicly viewable")
    rows = db.scalars(
        select(ArchivalOCRPage)
        .where(ArchivalOCRPage.canvas_id == canvas.id, ArchivalOCRPage.status == "verified")
        .order_by(ArchivalOCRPage.created_at.desc())
    ).all()
    return [ArchivalOCRRead.model_validate(row) for row in rows]


@router.post("/admin/{object_id}/canvases/{canvas_id}/ocr", response_model=ArchivalOCRRead)
def generate_canvas_ocr(
    object_id: int,
    canvas_id: int,
    payload: ArchivalOCRGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalOCRRead:
    require_admin_user(current_user)

    obj, canvas, asset = _public_canvas(canvas_id, db)
    if obj.id != object_id:
        raise HTTPException(status_code=404, detail="Archival canvas not found")

    matches, actual_checksum, fixity_detail = _verify_source(asset, obj.id)
    if not matches or not actual_checksum:
        event = PreservationEvent(
            archival_object_id=obj.id,
            asset_id=asset.id,
            event_type="fixity_check",
            outcome="failure",
            agent=current_user.full_name or f"user:{current_user.id}",
            detail=f"OCR generation blocked: {fixity_detail}",
            source_storage_key=asset.storage_key,
            checksum=actual_checksum,
            checksum_algorithm="SHA-256",
        )
        db.add(event)
        db.commit()
        raise HTTPException(status_code=409, detail="Source asset failed preservation verification")

    try:
        path = resolve_image(asset.storage_key)
        text, engine_version = extract_text(path, payload.language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="OCR source image is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    existing = db.scalar(
        select(ArchivalOCRPage).where(
            ArchivalOCRPage.canvas_id == canvas.id,
            ArchivalOCRPage.language == payload.language,
            ArchivalOCRPage.engine == "tesseract",
        )
    )
    if existing:
        existing.source_asset_id = asset.id
        existing.source_checksum_sha256 = actual_checksum
        existing.text = text
        existing.engine_version = engine_version
        existing.status = "verified"
        existing.verified_at = datetime.now(timezone.utc)
        row = existing
    else:
        row = ArchivalOCRPage(
            archival_object_id=obj.id,
            canvas_id=canvas.id,
            source_asset_id=asset.id,
            source_checksum_sha256=actual_checksum,
            text=text,
            language=payload.language,
            engine="tesseract",
            engine_version=engine_version,
            status="verified",
            verified_at=datetime.now(timezone.utc),
        )
        db.add(row)

    db.flush()
    db.add(
        PreservationEvent(
            archival_object_id=obj.id,
            asset_id=asset.id,
            event_type="ocr_created",
            outcome="success",
            agent=current_user.full_name or f"user:{current_user.id}",
            detail=f"OCR generated for canvas {canvas.canvas_identifier}; source checksum verified before extraction.",
            source_storage_key=asset.storage_key,
            checksum=actual_checksum,
            checksum_algorithm="SHA-256",
        )
    )
    db.commit()
    db.refresh(row)
    return ArchivalOCRRead.model_validate(row)


@router.post("/admin/{object_id}/canvases/{canvas_id}/ocr/verify", response_model=ArchivalOCRRead)
def verify_canvas_ocr(
    object_id: int,
    canvas_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalOCRRead:
    require_admin_user(current_user)
    obj, canvas, asset = _public_canvas(canvas_id, db)
    if obj.id != object_id:
        raise HTTPException(status_code=404, detail="Archival canvas not found")

    row = db.scalar(
        select(ArchivalOCRPage)
        .where(ArchivalOCRPage.canvas_id == canvas.id)
        .order_by(ArchivalOCRPage.created_at.desc())
    )
    if not row:
        raise HTTPException(status_code=404, detail="OCR record not found")

    matches, actual_checksum, detail = _verify_source(asset, obj.id)
    checksum_matches = actual_checksum is not None and actual_checksum.lower() == row.source_checksum_sha256.lower()
    verified = matches and checksum_matches and asset.id == row.source_asset_id
    row.status = "verified" if verified else "stale"
    row.verified_at = datetime.now(timezone.utc) if verified else None

    db.add(
        PreservationEvent(
            archival_object_id=obj.id,
            asset_id=asset.id,
            event_type="ocr_verified",
            outcome="success" if verified else "failure",
            agent=current_user.full_name or f"user:{current_user.id}",
            detail=(
                "OCR source checksum still matches the verified access asset."
                if verified
                else f"OCR verification failed: {detail}; source_checksum_matches={checksum_matches}."
            ),
            source_storage_key=asset.storage_key,
            checksum=actual_checksum,
            checksum_algorithm="SHA-256",
        )
    )
    db.commit()
    db.refresh(row)
    return ArchivalOCRRead.model_validate(row)
