from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_connection import UserConnection
from app.schemas.connections import (
    ConnectionUserRead,
    UserConnectionAction,
    UserConnectionCreate,
    UserConnectionRead,
)

router = APIRouter(prefix="/connections", tags=["connections"])


def serialize_connection(row: UserConnection) -> UserConnectionRead:
    return UserConnectionRead(
        id=row.id,
        status=row.status,
        relationship_type=row.relationship_type,
        created_at=row.created_at,
        requester=ConnectionUserRead.model_validate(row.requester),
        addressee=ConnectionUserRead.model_validate(row.addressee),
    )


@router.get("/", response_model=list[UserConnectionRead])
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserConnectionRead]:
    rows = db.scalars(
        select(UserConnection).where(
            or_(
                UserConnection.requester_id == current_user.id,
                UserConnection.addressee_id == current_user.id,
            )
        )
    ).all()

    return [serialize_connection(row) for row in rows]


@router.post("/invite", response_model=UserConnectionRead, status_code=201)
def invite_connection(
    payload: UserConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserConnectionRead:
    target = db.scalar(select(User).where(User.email == payload.email))
    if not target:
      raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_user.id:
      raise HTTPException(status_code=400, detail="Cannot connect to yourself")

    existing = db.scalar(
        select(UserConnection).where(
            or_(
                and_(
                    UserConnection.requester_id == current_user.id,
                    UserConnection.addressee_id == target.id,
                ),
                and_(
                    UserConnection.requester_id == target.id,
                    UserConnection.addressee_id == current_user.id,
                ),
            )
        )
    )
    if existing:
      raise HTTPException(status_code=409, detail="Connection already exists")

    row = UserConnection(
        requester_id=current_user.id,
        addressee_id=target.id,
        relationship_type=payload.relationship_type,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_connection(row)


@router.post("/{connection_id}/action", response_model=UserConnectionRead)
def connection_action(
    connection_id: int,
    payload: UserConnectionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserConnectionRead:
    row = db.scalar(select(UserConnection).where(UserConnection.id == connection_id))
    if not row:
      raise HTTPException(status_code=404, detail="Connection not found")

    if payload.action == "accept":
      if row.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to accept")
      row.status = "accepted"
    elif payload.action == "decline":
      if row.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to decline")
      row.status = "declined"
    elif payload.action == "block":
      if current_user.id not in {row.requester_id, row.addressee_id}:
        raise HTTPException(status_code=403, detail="Not allowed to block")
      row.status = "blocked"
    else:
      raise HTTPException(status_code=400, detail="Invalid action")

    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_connection(row)

@router.get("/accepted", response_model=list[ConnectionUserRead])
def list_accepted_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConnectionUserRead]:
    rows = db.scalars(
        select(UserConnection).where(
            UserConnection.status == "accepted",
            or_(
                UserConnection.requester_id == current_user.id,
                UserConnection.addressee_id == current_user.id,
            ),
        )
    ).all()

    users: list[User] = []
    for row in rows:
        other_user = row.addressee if row.requester_id == current_user.id else row.requester
        users.append(other_user)

    return [ConnectionUserRead.model_validate(user) for user in users]