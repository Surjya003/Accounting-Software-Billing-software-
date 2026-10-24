"""
Audit Trail Logging Service (Phase 4).
Records immutable audit logs of sensitive accounting actions (create, update, cancel, delete).
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.database.connection import get_session
from app.database.models import AuditLog
from app.services.auth_service import get_current_user

logger = logging.getLogger("BillFlow.Audit")


def log_audit(
    action: str,
    table_name: str,
    record_id: Optional[int] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> Optional[int]:
    """
    Records an audit log entry in the audit_logs table.
    Captures user context, timestamp, action, and JSON diffs.
    """
    try:
        user = get_current_user()
        user_id = user.get("id") if user else None
        username = user.get("username") if user else "System"

        old_str = json.dumps(old_values, default=str) if old_values else None
        new_str = json.dumps(new_values, default=str) if new_values else None

        with get_session() as session:
            entry = AuditLog(
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_str,
                new_values=new_str,
                notes=notes
            )
            session.add(entry)
            session.commit()
            return entry.id
    except Exception as e:
        logger.warning(f"Failed to record audit log: {e}")
        return None


def get_audit_trail(
    table_name: Optional[str] = None,
    record_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs matching query criteria."""
    with get_session() as session:
        q = session.query(AuditLog)
        if table_name:
            q = q.filter(AuditLog.table_name == table_name)
        if record_id:
            q = q.filter(AuditLog.record_id == record_id)
        if action:
            q = q.filter(AuditLog.action == action)
        entries = q.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit).all()
        return [e.to_dict() for e in entries]
