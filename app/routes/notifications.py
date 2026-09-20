from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import decode_token, get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notifications import NotificationRead, UnreadCountRead
from app.services.notifications import notification_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])


def serialize(row: Notification) -> NotificationRead:
    return NotificationRead(
        id=row.id,
        type=row.type,
        title=row.title,
        body=row.body,
        data=row.data_json,
        read_at=row.read_at,
        created_at=row.created_at,
    )


@router.get("/", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationRead]:
    statement = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    rows = db.scalars(statement.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)).all()
    return [serialize(row) for row in rows]


@router.get("/unread-count", response_model=UnreadCountRead)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountRead:
    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    ) or 0
    return UnreadCountRead(unread=int(count))


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationRead:
    row = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.read_at = row.read_at or datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.post("/read-all", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    rows = db.scalars(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
        db.add(row)
    db.commit()


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return

    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        if not subject:
            raise ValueError("Missing subject")
        user_id = int(subject)
    except Exception:
        await websocket.close(code=4401, reason="Invalid authentication token")
        return

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4403, reason="Inactive user")
            return
    finally:
        db.close()

    await notification_manager.connect(user_id, websocket)
    try:
        await websocket.send_json({"event": "ready"})
        while True:
            # Client messages are optional keepalives. Realtime events are server-pushed.
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)
    except Exception:
        notification_manager.disconnect(user_id, websocket)
