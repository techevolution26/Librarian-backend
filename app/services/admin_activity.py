from sqlalchemy.orm import Session

from app.models.admin_activity_log import AdminActivityLog
from app.models.user import User


def log_admin_activity(
    db: Session,
    admin: User,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    row = AdminActivityLog(
        admin_user_id=admin.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )

    db.add(row)