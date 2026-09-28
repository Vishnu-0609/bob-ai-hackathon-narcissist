import io
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload, RequireRoles, UserRole
from app.models.entities import Report, Incident, PMCase, AMCase, Match, Reconciliation
from app.schemas import ReportCreateRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("", response_model=List[ReportResponse])
def list_reports(
    incident_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    query = db.query(Report)
    if incident_id:
        query = query.filter(Report.incident_id == incident_id)
    return query.order_by(Report.generated_at.desc()).all()


@router.post("", response_model=ReportResponse)
def generate_report(
    req: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireRoles([
        UserRole.ADMIN,
        UserRole.COORDINATOR,
        UserRole.DVI_COORDINATOR,
        UserRole.FORENSIC_REVIEWER,
    ])),
):
    try:
        report = ReportService.create_report_record(
            db=db,
            incident_id=req.incident_id,
            pm_id=req.pm_id,
            am_id=req.am_id,
            title=req.title,
            user_id=current_user.get("username", "COORDINATOR"),
            user_role=current_user.get("role", "COORDINATOR"),
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    rep = db.query(Report).filter((Report.id == report_id) | (Report.report_number == report_id)).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return rep


@router.get("/{report_id}/pdf")
def download_report_pdf(
    report_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    rep = db.query(Report).filter((Report.id == report_id) | (Report.report_number == report_id)).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")

    incident = db.query(Incident).filter(Incident.id == rep.incident_id).first()
    pm_case = db.query(PMCase).filter(PMCase.id == rep.pm_id).first()
    am_case = db.query(AMCase).filter(AMCase.id == rep.am_id).first()
    match = db.query(Match).filter(Match.pm_id == rep.pm_id, Match.am_id == rep.am_id).first()
    recon = db.query(Reconciliation).filter(Reconciliation.pm_id == rep.pm_id, Reconciliation.am_id == rep.am_id).first()

    content = rep.content_json or {}
    eval_data = content.get("evaluation", {})
    rationale = content.get("rationale", "")
    evidence_gaps = content.get("evidence_gaps", {})
    audit_id = content.get("audit_event_id", "AUD-000001")

    pdf_bytes = ReportService.generate_reconciliation_pdf(
        incident=incident,
        pm_case=pm_case,
        am_case=am_case,
        match=match,
        reconciliation=recon,
        evaluation_data=eval_data,
        rationale_text=rationale,
        evidence_gap_data=evidence_gaps,
        report_number=rep.report_number,
        audit_event_id=audit_id,
    )

    filename = f"{rep.report_number}_{pm_case.body_number}_{am_case.case_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/csv")
def download_report_csv(
    report_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    rep = db.query(Report).filter((Report.id == report_id) | (Report.report_number == report_id)).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")

    content = rep.content_json or {}
    evidence_items = content.get("evaluation", {}).get("evidence_items", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field", "AM Reported", "PM Observed", "Comparison Result", "Weight", "Score Awarded", "Contradiction", "Notes"])

    for item in evidence_items:
        writer.writerow([
            item.get("field_name"),
            item.get("am_value"),
            item.get("pm_value"),
            item.get("comparison_result"),
            item.get("weight"),
            item.get("score_awarded"),
            item.get("contradiction"),
            item.get("notes"),
        ])

    csv_data = output.getvalue()
    filename = f"{rep.report_number}_evidence_matrix.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
