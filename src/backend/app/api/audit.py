from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.models.entities import AuditLog
from app.schemas import AuditLogItem, AuditVerifyResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Tamper-Evident Audit Trail"])


@router.get("", response_model=List[AuditLogItem])
def list_audit_events(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)

    return query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit).all()


@router.get("/verify", response_model=AuditVerifyResponse)
def verify_audit_chain(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Validates SHA-256 hash continuity across all immutable audit log entries.
    """
    verification = AuditService.verify_integrity(db)
    return AuditVerifyResponse(
        valid=verification["valid"],
        events_checked=verification["events_checked"],
        broken_at=verification.get("broken_at"),
        last_event_hash=verification.get("last_event_hash"),
        verification_time_ms=verification.get("verification_time_ms", 0.0),
    )
