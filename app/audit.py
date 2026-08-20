from typing import Optional
from sqlalchemy.orm import Session

import logging
from . import model

logger = logging.getLogger(__name__)


def log_activity(
    db: Session,
    workspace_id: int,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    details: Optional[str] = None
):
    """
    Creates an immutable audit log entry for team activity tracking.
    Example:
        log_activity(db, ws_id, user_id, "TASK_CREATED", "task", task.id, "Created task 'Design UI'")
    """
    try:
        audit_entry = model.AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
