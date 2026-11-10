from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from sqlalchemy import event
from sqlalchemy.orm import Session


class NotificationConnectionManager:
    """In-process realtime fan-out for development and single-worker deployments."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def _broadcast(self, user_id: int, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for websocket in tuple(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(user_id, websocket)

    def publish(self, user_id: int, payload: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(asyncio.create_task, self._broadcast(user_id, payload))


notification_manager = NotificationConnectionManager()

from app.models.notification import Notification

_PENDING_NOTIFICATION_PAYLOADS = "librarian_pending_notification_payloads"


@event.listens_for(Session, "after_commit")
def _publish_committed_notifications(session: Session) -> None:
    pending = session.info.pop(_PENDING_NOTIFICATION_PAYLOADS, [])
    for user_id, payload in pending:
        notification_manager.publish(user_id, payload)


@event.listens_for(Session, "after_rollback")
def _discard_rolled_back_notifications(session: Session) -> None:
    session.info.pop(_PENDING_NOTIFICATION_PAYLOADS, None)


def create_notification(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    row = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data_json=data,
    )
    db.add(row)
    db.flush()
    payload = {
        "event": "notification.created",
        "notification": {
            "id": row.id,
            "type": row.type,
            "title": row.title,
            "body": row.body,
            "data": row.data_json,
            "read_at": row.read_at.isoformat() if row.read_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }
    db.info.setdefault(_PENDING_NOTIFICATION_PAYLOADS, []).append((user_id, payload))
    return row
