from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.models.entities import PMCase, MatchVersion
from app.schemas import TopCandidatesResponse, CandidateMatch
from app.services.candidate_service import CandidateService
from app.services.bob_rationale import BobRationaleService
from app.services.bob_evidence_gap import BobEvidenceGapService

router = APIRouter(prefix="/matching", tags=["Deterministic Matching"])


@router.get("/{pm_id}/candidates", response_model=TopCandidatesResponse)
async def get_pm_candidates(
    pm_id: str,
    limit: int = Query(3, ge=1, le=10),
    include_ai: bool = Query(True),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Computes/retrieves Top-3 candidate AM profiles for a PM record using the deterministic scoring engine.
    """
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")

    result = CandidateService.get_or_calculate_candidates(
        db=db,
        pm_id=str(pm.id),
        limit=limit,
        user_id=payload.get("sub", "SYSTEM"),
        user_role=payload.get("role", "COORDINATOR"),
    )

    # Attach Bob rationale and evidence gaps to the candidates
    if include_ai:
        for cand in result.get("candidates", []):
            if not cand.get("bob_rationale"):
                cand["bob_rationale"] = await BobRationaleService.generate_rationale(cand, db=db)
            if not cand.get("evidence_gaps"):
                cand["evidence_gaps"] = await BobEvidenceGapService.analyze_evidence_gaps(cand, db=db)

    return TopCandidatesResponse(
        pm_id=result["pm_id"],
        pm_body_number=result["pm_body_number"],
        candidates=result["candidates"],
        total_candidates_evaluated=result["total_candidates_evaluated"],
        calculation_timestamp=result["calculation_timestamp"],
    )


@router.post("/{pm_id}/recalculate", response_model=TopCandidatesResponse)
async def recalculate_pm_candidates(
    pm_id: str,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Forces recalculation of matches and creates a new MatchVersion audit snapshot.
    """
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")

    result = CandidateService.get_or_calculate_candidates(
        db=db,
        pm_id=str(pm.id),
        limit=limit,
        force_recalculate=True,
        user_id=payload.get("sub", "SYSTEM"),
        user_role=payload.get("role", "COORDINATOR"),
    )

    for cand in result.get("candidates", []):
        cand["bob_rationale"] = await BobRationaleService.generate_rationale(cand, db=db)
        cand["evidence_gaps"] = await BobEvidenceGapService.analyze_evidence_gaps(cand, db=db)

    return TopCandidatesResponse(
        pm_id=result["pm_id"],
        pm_body_number=result["pm_body_number"],
        candidates=result["candidates"],
        total_candidates_evaluated=result["total_candidates_evaluated"],
        calculation_timestamp=result["calculation_timestamp"],
    )


@router.get("/versions/{pm_id}")
def get_match_versions(
    pm_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Returns historical versions of match calculations for forensic traceability.
    """
    pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PM Record not found")

    versions = (
        db.query(MatchVersion)
        .filter(MatchVersion.pm_id == str(pm.id))
        .order_by(MatchVersion.version.desc(), MatchVersion.calculated_at.desc())
        .all()
    )

    return [
        {
            "id": v.id,
            "version": v.version,
            "am_id": v.am_id,
            "match_score": v.match_score,
            "candidate_rank": v.candidate_rank,
            "algorithm_version": v.algorithm_version,
            "calculated_at": v.calculated_at.isoformat(),
            "input_hash": v.input_hash,
        }
        for v in versions
    ]
