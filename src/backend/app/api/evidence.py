from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.models.entities import Match, MatchEvidence, PMCase, AMCase, ImageEvidence

router = APIRouter(prefix="/evidence", tags=["Evidence & Provenance"])


@router.get("/{match_id}/graph")
def get_evidence_graph(
    match_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Constructs node-link graph data for visual evidence graph renderer,
    including multimodal Gemini image evidence nodes and verification provenance.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match record not found")

    pm = db.query(PMCase).filter(PMCase.id == match.pm_id).first()
    am = db.query(AMCase).filter(AMCase.id == match.am_id).first()
    if not pm or not am:
        raise HTTPException(status_code=404, detail="Associated PM or AM record not found")

    evidence_items = db.query(MatchEvidence).filter(MatchEvidence.match_id == match.id).all()
    am_images = db.query(ImageEvidence).filter((ImageEvidence.am_id == am.id) | (ImageEvidence.am_id == am.case_number)).all()
    pm_images = db.query(ImageEvidence).filter((ImageEvidence.pm_id == pm.id) | (ImageEvidence.pm_id == pm.body_number)).all()

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
            "image_count": len(am_images),
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
            "image_count": len(pm_images),
        },
    ]

    edges = []

    # Add Image Nodes for AM
    for img in am_images:
        img_node_id = f"img-am-{img.id[:8]}"
        nodes.append({
            "id": img_node_id,
            "label": f"AM Image: {img.image_type}",
            "sublabel": f"Model: {img.gemini_model}",
            "type": "IMAGE_EVIDENCE",
            "group": "AM_IMAGE",
            "source": "IMAGE",
            "source_type": "AM_PHOTO",
            "image_id": img.id,
            "gemini_model": img.gemini_model,
            "sha256": img.sha256,
            "human_review_status": img.human_review_status,
            "timestamp": img.uploaded_at.isoformat() if img.uploaded_at else "",
            "details": {
                "filename": img.original_filename,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "review_status": img.human_review_status,
            },
        })
        edges.append({
            "id": f"edge-am-img-{img.id[:8]}",
            "source": "node-am",
            "target": img_node_id,
            "label": "Photo",
            "type": "IMAGE_LINK",
            "status": img.human_review_status,
        })

    # Add Image Nodes for PM
    for img in pm_images:
        img_node_id = f"img-pm-{img.id[:8]}"
        nodes.append({
            "id": img_node_id,
            "label": f"PM Image: {img.image_type}",
            "sublabel": f"Model: {img.gemini_model}",
            "type": "IMAGE_EVIDENCE",
            "group": "PM_IMAGE",
            "source": "IMAGE",
            "source_type": "PM_PHOTO",
            "image_id": img.id,
            "gemini_model": img.gemini_model,
            "sha256": img.sha256,
            "human_review_status": img.human_review_status,
            "timestamp": img.uploaded_at.isoformat() if img.uploaded_at else "",
            "details": {
                "filename": img.original_filename,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "review_status": img.human_review_status,
            },
        })
        edges.append({
            "id": f"edge-pm-img-{img.id[:8]}",
            "source": "node-pm",
            "target": img_node_id,
            "label": "Forensic Photo",
            "type": "IMAGE_LINK",
            "status": img.human_review_status,
        })

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
            "provenance": item.provenance or {},
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

        # If attribute matches and image evidence exists for this field, link images to attribute node
        if f_name in ("clothing", "tattoos", "scars", "jewellery"):
            for img in am_images:
                edges.append({
                    "id": f"edge-attr-amimg-{idx}-{img.id[:8]}",
                    "source": f"img-am-{img.id[:8]}",
                    "target": attr_node_id,
                    "label": "Observed",
                    "type": "IMAGE_OBSERVATION",
                    "status": "MATCH",
                })
            for img in pm_images:
                edges.append({
                    "id": f"edge-attr-pmimg-{idx}-{img.id[:8]}",
                    "source": f"img-pm-{img.id[:8]}",
                    "target": attr_node_id,
                    "label": "Observed",
                    "type": "IMAGE_OBSERVATION",
                    "status": "MATCH",
                })

    return {
        "match_id": match.id,
        "match_score": match.match_score,
        "evidence_quality": match.evidence_quality,
        "nodes": nodes,
        "edges": edges,
        "summary": f"{len(evidence_items)} forensic observations and {len(am_images) + len(pm_images)} image evidence items evaluated.",
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
    am_images = db.query(ImageEvidence).filter((ImageEvidence.am_id == am.id) | (ImageEvidence.am_id == am.case_number)).all()
    pm_images = db.query(ImageEvidence).filter((ImageEvidence.pm_id == pm.id) | (ImageEvidence.pm_id == pm.body_number)).all()

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
            "images": [
                {
                    "id": img.id,
                    "image_type": img.image_type,
                    "sha256": img.sha256,
                    "gemini_model": img.gemini_model,
                    "human_review_status": img.human_review_status,
                    "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else "",
                }
                for img in am_images
            ],
        },
        "pm_case": {
            "body_number": pm.body_number,
            "examiner": pm.examiner,
            "recovery_location": pm.recovery_location,
            "provenance": pm.provenance_details,
            "created_by": pm.created_by,
            "created_at": pm.created_at.isoformat(),
            "images": [
                {
                    "id": img.id,
                    "image_type": img.image_type,
                    "sha256": img.sha256,
                    "gemini_model": img.gemini_model,
                    "human_review_status": img.human_review_status,
                    "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else "",
                }
                for img in pm_images
            ],
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

