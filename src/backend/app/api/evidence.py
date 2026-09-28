from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.models.entities import Match, MatchEvidence, PMCase, AMCase

router = APIRouter(prefix="/evidence", tags=["Evidence & Provenance"])


@router.get("/{match_id}/graph")
def get_evidence_graph(
    match_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Constructs node-link graph data for visual evidence graph renderer.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match record not found")

    pm = db.query(PMCase).filter(PMCase.id == match.pm_id).first()
    am = db.query(AMCase).filter(AMCase.id == match.am_id).first()
    if not pm or not am:
        raise HTTPException(status_code=404, detail="Associated PM or AM record not found")

    evidence_items = db.query(MatchEvidence).filter(MatchEvidence.match_id == match.id).all()

    nodes = [
        {
            "id": "node-am",
            "label": f"AM: {am.case_number}",
            "sublabel": am.name,
            "type": "AM_CASE",
            "group": "AM",
            "source": am.source or "Family Report",
            "source_type": am.source_type or "FAMILY_INTERVIEW",
            "details": am.provenance_details or {},
        },
        {
            "id": "node-pm",
            "label": f"PM: {pm.body_number}",
            "sublabel": f"Examiner: {pm.examiner or 'Mortuary'}",
            "type": "PM_CASE",
            "group": "PM",
            "source": pm.recovery_location or "Field Observation",
            "source_type": "MORTUARY_EXAM",
            "details": pm.provenance_details or {},
        },
    ]

    edges = []

    for idx, item in enumerate(evidence_items):
        f_name = item.field_name
        attr_node_id = f"attr-{f_name}-{idx}"
        res = item.comparison_result  # MATCH, MISMATCH, UNKNOWN, NOT_AVAILABLE

        nodes.append({
            "id": attr_node_id,
            "label": f_name.replace("_", " ").title(),
            "sublabel": f"{item.am_value or '-'} ↔ {item.pm_value or '-'}",
            "type": "ATTRIBUTE",
            "group": "EVIDENCE",
            "result": res,
            "score": item.score_awarded,
            "weight": item.weight,
            "notes": item.notes,
            "contradiction": item.contradiction,
        })

        # Edge AM -> Attribute
        edges.append({
            "id": f"edge-am-{idx}",
            "source": "node-am",
            "target": attr_node_id,
            "label": str(item.am_value or "None")[:20],
            "type": "EVIDENCE_LINK",
            "status": res,
        })

        # Edge Attribute -> PM
        edges.append({
            "id": f"edge-pm-{idx}",
            "source": attr_node_id,
            "target": "node-pm",
            "label": str(item.pm_value or "None")[:20],
            "type": "EVIDENCE_LINK",
            "status": res,
        })

    return {
        "match_id": match.id,
        "match_score": match.match_score,
        "evidence_quality": match.evidence_quality,
        "nodes": nodes,
        "edges": edges,
        "summary": f"{len(evidence_items)} forensic observations evaluated.",
    }


@router.get("/{match_id}/provenance")
def get_evidence_provenance(
    match_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pm = db.query(PMCase).filter(PMCase.id == match.pm_id).first()
    am = db.query(AMCase).filter(AMCase.id == match.am_id).first()
    evidence_items = db.query(MatchEvidence).filter(MatchEvidence.match_id == match.id).all()

    return {
        "match_id": match.id,
        "am_case": {
            "case_number": am.case_number,
            "name": am.name,
            "source": am.source,
            "source_type": am.source_type,
            "provenance": am.provenance_details,
            "created_by": am.created_by,
            "created_at": am.created_at.isoformat(),
        },
        "pm_case": {
            "body_number": pm.body_number,
            "examiner": pm.examiner,
            "recovery_location": pm.recovery_location,
            "provenance": pm.provenance_details,
            "created_by": pm.created_by,
            "created_at": pm.created_at.isoformat(),
        },
        "evidence_items": [
            {
                "field_name": item.field_name,
                "am_value": item.am_value,
                "pm_value": item.pm_value,
                "comparison_result": item.comparison_result,
                "score_awarded": item.score_awarded,
                "contradiction": item.contradiction,
                "provenance": item.provenance,
            }
            for item in evidence_items
        ],
    }
