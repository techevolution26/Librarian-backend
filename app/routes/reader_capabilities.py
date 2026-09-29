from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.reader_capabilities import ReaderCapabilitiesRead, ReaderCapabilityRead
from app.services.reader_capabilities import (
    get_active_plan_for_reader_capabilities,
    list_advanced_reader_capabilities,
)

router = APIRouter(prefix="/reader/capabilities", tags=["reader-capabilities"])


@router.get("/{plan_code}", response_model=ReaderCapabilitiesRead)
def get_reader_capabilities(
    plan_code: str,
    db: Session = Depends(get_db),
) -> ReaderCapabilitiesRead:
    """Describe advanced-reader capabilities configured on an active plan.

    This is catalogue discovery only. It does not determine whether the
    current user owns or subscribes to the plan.
    """
    plan = get_active_plan_for_reader_capabilities(db, plan_code=plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail="Active plan not found")
    rows = list_advanced_reader_capabilities(db, plan_id=plan.id)
    return ReaderCapabilitiesRead(
        plan_code=plan.code,
        capabilities=[ReaderCapabilityRead.model_validate(row) for row in rows],
    )
