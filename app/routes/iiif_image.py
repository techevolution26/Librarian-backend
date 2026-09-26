from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.asset_storage_location import AssetStorageLocation
from app.models.book_asset import BookAsset
from app.schemas.iiif_image import IIIFImageInfo
from app.services.iiif_image import (
    IIIF_CONTEXT,
    info_document,
    inspect_image,
    parse_request,
    render_image,
)
from app.services.storage import get_storage_backend


router = APIRouter(prefix="/iiif/3", tags=["iiif-image"])


def _public_canvas(identifier: str, db: Session) -> tuple[ArchivalObject, ArchivalCanvas, BookAsset, AssetStorageLocation]:
    canvas = db.scalar(
        select(ArchivalCanvas)
        .join(ArchivalObject, ArchivalCanvas.archival_object_id == ArchivalObject.id)
        .join(BookAsset, ArchivalCanvas.asset_id == BookAsset.id)
        .options(selectinload(ArchivalCanvas.archival_object), selectinload(ArchivalCanvas.asset))
        .where(
            ArchivalCanvas.canvas_identifier == identifier,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
            BookAsset.mime_type.like("image/%"),
        )
    )
    if not canvas or not canvas.asset:
        raise HTTPException(status_code=404, detail="IIIF image not found")

    location = db.scalar(
        select(AssetStorageLocation)
        .where(
            AssetStorageLocation.asset_id == canvas.asset.id,
            AssetStorageLocation.status == "active",
        )
        .order_by(AssetStorageLocation.is_primary.desc(), AssetStorageLocation.created_at.asc())
    )
    if not location:
        raise HTTPException(status_code=404, detail="IIIF image storage location not found")
    return canvas.archival_object, canvas, canvas.asset, location


def _service_url(request: Request, identifier: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/iiif/3/{quote(identifier, safe=':._-')}"


def _resolve_image_path(location: AssetStorageLocation) -> Path:
    backend = get_storage_backend()
    if location.provider != backend.provider:
        raise HTTPException(
            status_code=503,
            detail=f"IIIF image storage provider '{location.provider}' is not available on this deployment",
        )
    if location.replication_status not in {"none", "verified"}:
        raise HTTPException(status_code=503, detail="IIIF image storage copy is not verified")
    return backend.resolve(location.storage_key)


@router.get("/{identifier}/info.json", response_model=IIIFImageInfo)
def get_image_info(identifier: str, request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    obj, _, _, location = _public_canvas(identifier, db)
    if obj.rights and obj.rights.view_allowed is False:
        raise HTTPException(status_code=403, detail="Viewing this archival image is not permitted")
    try:
        path = _resolve_image_path(location)
        info = inspect_image(path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="IIIF image storage backend is unavailable") from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="IIIF image is unavailable") from exc

    rights = obj.rights.license if obj.rights else None
    document = info_document(
        identifier,
        _service_url(request, identifier),
        info.width,
        info.height,
        rights=rights,
    )
    validated = IIIFImageInfo.model_validate(document)
    return JSONResponse(
        content=validated.model_dump(by_alias=True, exclude_none=True),
        media_type=f'application/ld+json;profile="{IIIF_CONTEXT}"',
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/{identifier}/{region}/{size}/{rotation}/{quality}.{format}")
def get_image(
    identifier: str,
    region: str,
    size: str,
    rotation: str,
    quality: str,
    format: str,
    db: Session = Depends(get_db),
) -> Response:
    obj, _, _, location = _public_canvas(identifier, db)
    if obj.rights and obj.rights.view_allowed is False:
        raise HTTPException(status_code=403, detail="Viewing this archival image is not permitted")
    try:
        image_request = parse_request(region, size, rotation, quality, format)
        path = _resolve_image_path(location)
        body, media_type = render_image(path, image_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="IIIF image storage backend is unavailable") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IIIF image is unavailable") from exc

    response = Response(content=body, media_type=media_type)
    response.headers["Cache-Control"] = "public, max-age=86400, immutable"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
