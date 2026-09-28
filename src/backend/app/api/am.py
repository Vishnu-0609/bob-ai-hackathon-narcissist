from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload, RequireRoles, UserRole
from app.models.entities import AMCase, ExtractionReview, PMCase
from app.schemas import (
    AMCaseCreate,
    AMCaseUpdate,
    AMCaseResponse,
    ExtractionRequest,
    ExtractionReviewSubmission,
)
from app.services.bob_extraction import BobExtractionService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/am", tags=["Ante-Mortem Records"])


@router.get("", response_model=List[AMCaseResponse])
def list_am_cases(
    incident_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sex: Optional[str] = Query(None),
    blood_group: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    query = db.query(AMCase)
    if incident_id:
        query = query.filter(AMCase.incident_id == incident_id)
    if sex:
        query = query.filter(AMCase.sex == sex.upper())
    if blood_group:
        query = query.filter(AMCase.blood_group == blood_group.upper())
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (AMCase.name.ilike(search_filter))
            | (AMCase.case_number.ilike(search_filter))
            | (AMCase.physical_description.ilike(search_filter))
        )
    return query.order_by(AMCase.case_number.asc()).all()


@router.get("/{am_id}", response_model=AMCaseResponse)
def get_am_case(
    am_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    am = db.query(AMCase).filter((AMCase.id == am_id) | (AMCase.case_number == am_id)).first()
    if not am:
        raise HTTPException(status_code=404, detail="AM Record not found")
    return am


@router.post("", response_model=AMCaseResponse)
def create_am_case(
    case_in: AMCaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.AM_TEAM, UserRole.FIELD_OPERATOR])),
):
    am = AMCase(
        incident_id=case_in.incident_id,
        case_number=case_in.case_number,
        name=case_in.name,
        age=case_in.age,
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
        dental_notes=case_in.dental_notes,
        medical_history=case_in.medical_history,
        implants=case_in.implants,
        last_seen_location=case_in.last_seen_location,
        last_seen_time=case_in.last_seen_time,
        source=case_in.source,
        source_type=case_in.source_type or "FAMILY_INTERVIEW",
        provenance_details=case_in.provenance_details or {
            "source_type": case_in.source_type or "FAMILY_INTERVIEW",
            "captured_by": current_user.get("username", "USER"),
            "extracted_by": "MANUAL_ENTRY",
            "reviewed_by": current_user.get("username", "USER"),
            "review_status": "HUMAN_VERIFIED",
        },
        version=1,
        created_by=current_user.get("username", "SYSTEM"),
    )
    db.add(am)
    db.commit()
    db.refresh(am)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="AM_CREATED",
        entity_type="AM",
        entity_id=am.case_number,
        details={"case_number": am.case_number, "name": am.name, "sex": am.sex},
    )

    return am


@router.put("/{am_id}", response_model=AMCaseResponse)
def update_am_case(
    am_id: str,
    case_update: AMCaseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.AM_TEAM, UserRole.FIELD_OPERATOR])),
):
    am = db.query(AMCase).filter((AMCase.id == am_id) | (AMCase.case_number == am_id)).first()
    if not am:
        raise HTTPException(status_code=404, detail="AM Record not found")

    old_data = {
        "name": am.name,
        "age": am.age,
        "sex": am.sex,
        "height_cm": am.height_cm,
        "blood_group": am.blood_group,
        "version": am.version,
    }

    update_dict = case_update.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if k in ("sex", "blood_group") and v:
            v = str(v).upper()
        setattr(am, k, v)

    am.version = am.version + 1
    am.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(am)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="AM_UPDATED",
        entity_type="AM",
        entity_id=am.case_number,
        details={"version": am.version, "changes": list(update_dict.keys()), "old_snapshot": old_data},
    )

    return am


@router.post("/extract")
async def extract_am_narrative(
    req: ExtractionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_payload),
):
    """
    Submits narrative text or voice transcript to Bob AM Extraction Agent.
    Creates a pending review record.
    """
    extraction_res = await BobExtractionService.extract_am_profile(
        text=req.text,
        incident_id=req.incident_id,
        db=db,
    )

    review_entry = ExtractionReview(
        entity_type="AM",
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
        entity_type="AM_EXTRACTION",
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


@router.post("/review", response_model=AMCaseResponse)
def review_and_save_am(
    submission: ExtractionReviewSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR, UserRole.AM_TEAM, UserRole.FIELD_OPERATOR])),
):
    """
    Human operator approves or edits Bob-extracted data before authoritative DB entry.
    """
    data = submission.approved_data
    case_num = submission.case_identifier or f"AM-{db.query(AMCase).count() + 1:03d}"

    am = db.query(AMCase).filter((AMCase.case_number == case_num) | (AMCase.id == case_num)).first()
    if am:
        if data.get("name"):
            am.name = data.get("name")
        if data.get("age") is not None:
            am.age = data.get("age")
        if data.get("sex"):
            am.sex = (data.get("sex") or "").upper() or None
        if data.get("height_cm") is not None:
            am.height_cm = data.get("height_cm")
        if data.get("weight_kg") is not None:
            am.weight_kg = data.get("weight_kg")
        if data.get("blood_group"):
            am.blood_group = (data.get("blood_group") or "").upper() or None
        if data.get("physical_description"):
            am.physical_description = data.get("physical_description")
        if data.get("scars"):
            am.scars = data.get("scars")
        if data.get("birthmarks"):
            am.birthmarks = data.get("birthmarks")
        if data.get("tattoos"):
            am.tattoos = data.get("tattoos")
        if data.get("clothing"):
            am.clothing = data.get("clothing")
        if data.get("jewellery"):
            am.jewellery = data.get("jewellery")
        if data.get("last_seen_location"):
            am.last_seen_location = data.get("last_seen_location")
        am.version = (am.version or 0) + 1
        am.updated_at = datetime.now(timezone.utc)
    else:
        am = AMCase(
            incident_id=submission.incident_id,
            case_number=case_num,
            name=data.get("name") or "Unknown Family Report",
            age=data.get("age"),
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
            dental_notes=data.get("dental_notes"),
            medical_history=data.get("medical_history"),
            implants=data.get("implants") or [],
            last_seen_location=data.get("last_seen_location"),
            last_seen_time=data.get("last_seen_time"),
            source="Family Narrative (Bob Extraction)",
            source_type="FAMILY_INTERVIEW",
            provenance_details={
                "source_type": "FAMILY_INTERVIEW",
                "extracted_by": "IBM_BOB",
                "review_status": "HUMAN_VERIFIED",
                "reviewed_by": current_user.get("username", "USER"),
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "notes": submission.notes,
            },
            version=1,
            created_by=current_user.get("username", "SYSTEM"),
        )
        db.add(am)

    if submission.review_id:
        rev = db.query(ExtractionReview).filter(ExtractionReview.id == submission.review_id).first()
        if rev:
            rev.status = submission.decision
            rev.approved_json = data
            rev.reviewed_by = current_user.get("username", "USER")
            rev.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(am)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "SYSTEM"),
        role=current_user.get("role", "FIELD_OPERATOR"),
        action="BOB_EXTRACTION_REVIEWED",
        entity_type="AM",
        entity_id=am.case_number,
        details={"case_number": am.case_number, "decision": submission.decision, "reviewer": current_user.get("username")},
    )

    return am
