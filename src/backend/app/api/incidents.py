from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload, RequireRoles, UserRole
from app.models.entities import Incident, AMCase, PMCase, Match
from app.schemas import IncidentCreate, IncidentResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentResponse])
def get_incidents(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    results = []
    for inc in incidents:
        am_count = db.query(AMCase).filter(AMCase.incident_id == inc.id).count()
        pm_count = db.query(PMCase).filter(PMCase.incident_id == inc.id).count()
        matched_count = (
            db.query(Match)
            .filter(Match.incident_id == inc.id, Match.match_score >= 80)
            .distinct(Match.pm_id)
            .count()
        )
        res = IncidentResponse(
            id=inc.id,
            name=inc.name,
            location=inc.location,
            date=inc.date or datetime.now(timezone.utc),
            description=inc.description,
            status=inc.status,
            created_at=inc.created_at or datetime.now(timezone.utc),
            updated_at=inc.updated_at or datetime.now(timezone.utc),
            am_count=am_count,
            pm_count=pm_count,
            matched_count=matched_count,
        )
        results.append(res)
    return results


@router.post("", response_model=IncidentResponse)
def create_incident(
    inc_in: IncidentCreate,
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR])),
    db: Session = Depends(get_db),
):
    inc = Incident(
        name=inc_in.name,
        location=inc_in.location,
        date=inc_in.date or datetime.now(timezone.utc),
        description=inc_in.description,
        status=inc_in.status,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "COORDINATOR"),
        action="INCIDENT_CREATED",
        entity_type="INCIDENT",
        entity_id=inc.id,
        details={"name": inc.name, "location": inc.location},
    )

    return IncidentResponse(
        id=inc.id,
        name=inc.name,
        location=inc.location,
        date=inc.date,
        description=inc.description,
        status=inc.status,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        am_count=0,
        pm_count=0,
        matched_count=0,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: str,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    am_count = db.query(AMCase).filter(AMCase.incident_id == inc.id).count()
    pm_count = db.query(PMCase).filter(PMCase.incident_id == inc.id).count()
    matched_count = (
        db.query(Match)
        .filter(Match.incident_id == inc.id, Match.match_score >= 80)
        .distinct(Match.pm_id)
        .count()
    )

    return IncidentResponse(
        id=inc.id,
        name=inc.name,
        location=inc.location,
        date=inc.date or datetime.now(timezone.utc),
        description=inc.description,
        status=inc.status,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        am_count=am_count,
        pm_count=pm_count,
        matched_count=matched_count,
    )
