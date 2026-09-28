from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload, RequireRoles, UserRole
from app.models.entities import PMCase, ExtractionReview
from app.schemas import (
    PMCaseCreate,
    PMCaseUpdate,
    PMCaseResponse,
    ExtractionRequest,
    ExtractionReviewSubmission,
)
from app.services.bob_extraction import BobExtractionService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/pm", tags=["Post-Mortem Records"])


@router.get("", response_model=List[PMCaseResponse])
def list_pm_cases(
    incident_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sex: Optional[str] = Query(None),
    blood_group: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    query = db.query(PMCase)
    if incident_id:
        query = query.filter(PMCase.incident_id == incident_id)
    if sex:
        query = query.filter(PMCase.sex == sex.upper())
    if blood_group:
        query = query.filter(PMCase.blood_group == blood_group.upper())
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PMCase.body_number.ilike(search_filter))
            | (PMCase.physical_description.ilike(search_filter))
            | (PMCase.recovery_location.ilike(search_filter))
        )
    return query.order_by(PMCase.body_number.asc()).all()


@router.get("/{pm_id}", response_model=PMCaseResponse)
def get_pm_case(
    pm_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")
    return pm


@router.post("", response_model=PMCaseResponse)
def create_pm_case(
    case_in: PMCaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.PM_TEAM, UserRole.FIELD_OPERATOR])),
):
    pm = PMCase(
        incident_id=case_in.incident_id,
        body_number=case_in.body_number,
        estimated_age_min=case_in.estimated_age_min,
        estimated_age_max=case_in.estimated_age_max,
        sex=case_in.sex.upper() if case_in.sex else None,
        height_cm=case_in.height_cm,
        weight_kg=case_in.weight_kg,
        blood_group=case_in.blood_group.upper() if case_in.blood_group else None,
        physical_description=case_in.physical_description,
        scars=case_in.scars,
        birthmarks=case_in.birthmarks,
        tattoos=case_in.tattoos,
        clothing=case_in.clothing,
        jewellery=case_in.jewellery,
        dental_findings=case_in.dental_findings,
        medical_findings=case_in.medical_findings,
        implants=case_in.implants,
        fingerprint_status=case_in.fingerprint_status or "NOT_AVAILABLE",
        dna_status=case_in.dna_status or "NOT_AVAILABLE",
        recovery_location=case_in.recovery_location,
        examiner=case_in.examiner or current_user.get("username", "Forensic Examiner"),
        provenance_details=case_in.provenance_details or {
            "source_type": "MORTUARY_OBSERVATION",
            "captured_by": current_user.get("username", "USER"),
            "extracted_by": "MANUAL_ENTRY",
            "reviewed_by": current_user.get("username", "USER"),
            "review_status": "HUMAN_VERIFIED",
        },
        version=1,
        created_by=current_user.get("username", "SYSTEM"),
    )
    db.add(pm)
    db.commit()
    db.refresh(pm)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="PM_CREATED",
        entity_type="PM",
        entity_id=pm.body_number,
        details={"body_number": pm.body_number, "sex": pm.sex, "examiner": pm.examiner},
    )

    return pm


@router.put("/{pm_id}", response_model=PMCaseResponse)
def update_pm_case(
    pm_id: str,
    case_update: PMCaseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.PM_TEAM, UserRole.FIELD_OPERATOR])),
):
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")

    old_data = {
        "body_number": pm.body_number,
        "sex": pm.sex,
        "height_cm": pm.height_cm,
        "blood_group": pm.blood_group,
        "version": pm.version,
    }

    update_dict = case_update.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if k in ("sex", "blood_group") and v:
            v = str(v).upper()
        setattr(pm, k, v)

    pm.version = pm.version + 1
    pm.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pm)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="PM_UPDATED",
        entity_type="PM",
        entity_id=pm.body_number,
        details={"version": pm.version, "changes": list(update_dict.keys()), "old_snapshot": old_data},
    )

    return pm


@router.post("/extract")
async def extract_pm_notes(
    req: ExtractionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_payload),
):
    """
    Submits mortuary examiner notes to Bob PM Extraction Agent.
    """
    extraction_res = await BobExtractionService.extract_pm_profile(
        text=req.text,
        incident_id=req.incident_id,
        db=db,
    )

    review_entry = ExtractionReview(
        entity_type="PM",
        raw_text=req.text,
        extracted_json=extraction_res.get("data", {}),
        approved_json={},
        status="PENDING_REVIEW",
        extracted_by=extraction_res.get("source", "IBM_BOB"),
    )
    db.add(review_entry)
    db.commit()
    db.refresh(review_entry)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="BOB_EXTRACTION_REQUESTED",
        entity_type="PM_EXTRACTION",
        entity_id=review_entry.id,
        details={"source": extraction_res.get("source"), "text_length": len(req.text)},
    )

    return {
        "review_id": review_entry.id,
        "extracted_data": extraction_res.get("data", {}),
        "source": extraction_res.get("source"),
        "raw_text": req.text,
        "review_required": True,
    }


@router.post("/review", response_model=PMCaseResponse)
def review_and_save_pm(
    submission: ExtractionReviewSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.PM_TEAM, UserRole.FIELD_OPERATOR])),
):
    """
    Forensic operator verifies or adjusts Bob-extracted PM observations before database persistence.
    """
    data = submission.approved_data
    body_num = submission.case_identifier or f"PM-{db.query(PMCase).count() + 1:03d}"

    pm = db.query(PMCase).filter((PMCase.body_number == body_num) | (PMCase.id == body_num)).first()
    if pm:
        if data.get("estimated_age_min") is not None:
            pm.estimated_age_min = data.get("estimated_age_min")
        if data.get("estimated_age_max") is not None:
            pm.estimated_age_max = data.get("estimated_age_max")
        if data.get("sex"):
            pm.sex = (data.get("sex") or "").upper() or None
        if data.get("height_cm") is not None:
            pm.height_cm = data.get("height_cm")
        if data.get("weight_kg") is not None:
            pm.weight_kg = data.get("weight_kg")
        if data.get("blood_group"):
            pm.blood_group = (data.get("blood_group") or "").upper() or None
        if data.get("physical_description"):
            pm.physical_description = data.get("physical_description")
        if data.get("scars"):
            pm.scars = data.get("scars")
        if data.get("birthmarks"):
            pm.birthmarks = data.get("birthmarks")
        if data.get("tattoos"):
            pm.tattoos = data.get("tattoos")
        if data.get("clothing"):
            pm.clothing = data.get("clothing")
        if data.get("jewellery"):
            pm.jewellery = data.get("jewellery")
        if data.get("recovery_location"):
            pm.recovery_location = data.get("recovery_location")
        pm.version = (pm.version or 0) + 1
        pm.updated_at = datetime.now(timezone.utc)
    else:
        pm = PMCase(
            incident_id=submission.incident_id,
            body_number=body_num,
            estimated_age_min=data.get("estimated_age_min"),
            estimated_age_max=data.get("estimated_age_max"),
            sex=(data.get("sex") or "").upper() or None,
            height_cm=data.get("height_cm"),
            weight_kg=data.get("weight_kg"),
            blood_group=(data.get("blood_group") or "").upper() or None,
            physical_description=data.get("physical_description") or "",
            scars=data.get("scars") or [],
            birthmarks=data.get("birthmarks") or [],
            tattoos=data.get("tattoos") or [],
            clothing=data.get("clothing") or [],
            jewellery=data.get("jewellery") or [],
            dental_findings=data.get("dental_findings"),
            medical_findings=data.get("medical_findings"),
            implants=data.get("implants") or [],
            recovery_location=data.get("recovery_location"),
            examiner=data.get("examiner") or current_user.get("username", "Examiner"),
            provenance_details={
                "source_type": "MORTUARY_OBSERVATION",
                "extracted_by": "IBM_BOB",
                "review_status": "HUMAN_VERIFIED",
                "reviewed_by": current_user.get("username", "USER"),
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "notes": submission.notes,
            },
            version=1,
            created_by=current_user.get("username", "SYSTEM"),
        )
        db.add(pm)

    if submission.review_id:
        rev = db.query(ExtractionReview).filter(ExtractionReview.id == submission.review_id).first()
        if rev:
            rev.status = submission.decision
            rev.approved_json = data
            rev.reviewed_by = current_user.get("username", "USER")
            rev.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(pm)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="BOB_EXTRACTION_REVIEWED",
        entity_type="PM",
        entity_id=pm.body_number,
        details={"body_number": pm.body_number, "decision": submission.decision, "reviewer": current_user.get("username")},
    )

    return pm
