from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload, RequireRoles, UserRole
from app.models.entities import Reconciliation, PMCase, AMCase, Match
from app.schemas import ReconciliationDecisionRequest, ReconciliationResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/reconciliation", tags=["Human Reconciliation"])


@router.get("/{pm_id}", response_model=List[ReconciliationResponse])
def get_pm_reconciliations(
    pm_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")

    return (
        db.query(Reconciliation)
        .filter(Reconciliation.pm_id == str(pm.id))
        .order_by(Reconciliation.reviewed_at.desc())
        .all()
    )


@router.post("", response_model=ReconciliationResponse)
def submit_reconciliation_decision(
    req: ReconciliationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([
        UserRole.ADMIN,
        UserRole.COORDINATOR,
        UserRole.DVI_COORDINATOR,
        UserRole.FORENSIC_REVIEWER,
    ])),
):
    """
    Submits human forensic decision for a candidate match.
    Valid decisions: CONFIRMED_BY_FORENSIC_TEAM, REJECTED, NEEDS_REVIEW, PENDING_REVIEW
    """
    pm = db.query(PMCase).filter((PMCase.id == req.pm_id) | (PMCase.body_number == req.pm_id)).first()
    am = db.query(AMCase).filter((AMCase.id == req.am_id) | (AMCase.case_number == req.am_id)).first()

    if not pm or not am:
        raise HTTPException(status_code=404, detail="PM or AM record not found")

    allowed_decisions = [
        "CONFIRMED_BY_FORENSIC_TEAM",
        "REJECTED",
        "NEEDS_REVIEW",
        "PENDING_REVIEW",
    ]
    if req.decision not in allowed_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{req.decision}'. Allowed: {allowed_decisions}",
        )

    # Find or create reconciliation record
    recon = (
        db.query(Reconciliation)
        .filter(Reconciliation.pm_id == str(pm.id), Reconciliation.am_id == str(am.id))
        .first()
    )

    now = datetime.now(timezone.utc)
    username = current_user.get("username", "COORDINATOR")

    if recon:
        recon.decision = req.decision
        recon.reason = req.reason
        recon.coordinator_comment = req.coordinator_comment
        recon.forensic_notes = req.forensic_notes
        recon.reviewed_by = username
        recon.reviewed_at = now
    else:
        recon = Reconciliation(
            incident_id=pm.incident_id,
            pm_id=str(pm.id),
            am_id=str(am.id),
            decision=req.decision,
            reason=req.reason,
            coordinator_comment=req.coordinator_comment,
            forensic_notes=req.forensic_notes,
            reviewed_by=username,
            reviewed_at=now,
        )
        db.add(recon)

    # Update Match status
    match = db.query(Match).filter(Match.pm_id == str(pm.id), Match.am_id == str(am.id)).first()
    if match:
        match.status = req.decision
        match.updated_at = now

    db.commit()
    db.refresh(recon)

    # Log immutable audit event
    action_type = f"RECONCILIATION_{req.decision}"
    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "COORDINATOR"),
        action=action_type,
        entity_type="RECONCILIATION",
        entity_id=f"{pm.body_number}<->{am.case_number}",
        details={
            "pm_body_number": pm.body_number,
            "am_case_number": am.case_number,
            "decision": req.decision,
            "reason": req.reason,
            "coordinator_comment": req.coordinator_comment,
            "reviewer": username,
        },
    )

    return recon
