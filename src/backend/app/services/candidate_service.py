import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    PMCase,
    AMCase,
    Match,
    MatchEvidence,
    MatchVersion,
    Reconciliation,
)
from app.services.matching_engine import MatchingEngine
from app.services.audit_service import AuditService


class CandidateService:
    @staticmethod
    def calculate_input_hash(pm_case: PMCase, am_case: AMCase) -> str:
        data = {
            "pm_id": str(pm_case.id),
            "pm_updated": pm_case.updated_at.isoformat() if pm_case.updated_at else "",
            "pm_version": pm_case.version,
            "am_id": str(am_case.id),
            "am_updated": am_case.updated_at.isoformat() if am_case.updated_at else "",
            "am_version": am_case.version,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def get_or_calculate_candidates(
        db: Session,
        pm_id: str,
        limit: int = 3,
        force_recalculate: bool = False,
        user_id: str = "SYSTEM",
        user_role: str = "COORDINATOR",
    ) -> Dict[str, Any]:
        pm_case = db.query(PMCase).filter(PMCase.id == pm_id).first()
        if not pm_case:
            raise ValueError(f"PM Case {pm_id} not found.")

        # Retrieve all AM cases in same incident
        am_cases = db.query(AMCase).filter(AMCase.incident_id == pm_case.incident_id).all()
        if not am_cases:
            return {
                "pm_id": str(pm_case.id),
                "pm_body_number": str(pm_case.body_number),
                "candidates": [],
                "total_candidates_evaluated": 0,
                "calculation_timestamp": datetime.now(timezone.utc),
            }

        engine = MatchingEngine()
        evaluated_pairs = []

        for am in am_cases:
            eval_result = engine.evaluate_pair(pm_case, am)
            evaluated_pairs.append(eval_result)

        # Sort primarily by match_score descending, secondarily by data_completeness descending
        evaluated_pairs.sort(key=lambda x: (x["match_score"], x["data_completeness"]), reverse=True)

        top_candidates = evaluated_pairs[:limit]

        # Check existing reconciliation decisions
        reconciliations = db.query(Reconciliation).filter(Reconciliation.pm_id == pm_id).all()
        recon_map = {r.am_id: r.decision for r in reconciliations}

        # Persist / update matches and match versions
        for rank, cand in enumerate(top_candidates, start=1):
            cand["candidate_rank"] = rank
            am_id = cand["am_id"]
            cand["reconciliation_status"] = recon_map.get(am_id, "PENDING_REVIEW")

            # Look for existing match record
            existing_match = (
                db.query(Match)
                .filter(Match.pm_id == pm_id, Match.am_id == am_id)
                .first()
            )

            am_case = next(a for a in am_cases if str(a.id) == am_id)
            input_hash = CandidateService.calculate_input_hash(pm_case, am_case)

            if existing_match:
                # If recalculate or score changed, create new version
                new_version = existing_match.version + 1
                match_id = existing_match.id

                # Save historical version
                version_record = MatchVersion(
                    incident_id=pm_case.incident_id,
                    pm_id=pm_id,
                    am_id=am_id,
                    version=existing_match.version,
                    match_score=existing_match.match_score,
                    candidate_rank=existing_match.candidate_rank,
                    evidence_snapshot={"score": existing_match.match_score, "quality": existing_match.evidence_quality},
                    algorithm_version="1.0.0",
                    input_hash=input_hash,
                )
                db.add(version_record)

                # Update current match
                existing_match.match_score = cand["match_score"]
                existing_match.evidence_quality = cand["evidence_quality"]
                existing_match.data_completeness = cand["data_completeness"]
                existing_match.contradiction_status = cand["contradiction_status"]
                existing_match.candidate_rank = rank
                existing_match.status = cand["status"]
                existing_match.version = new_version
                existing_match.updated_at = datetime.now(timezone.utc)

                # Clear and re-populate evidence items
                db.query(MatchEvidence).filter(MatchEvidence.match_id == match_id).delete()
            else:
                new_match = Match(
                    incident_id=pm_case.incident_id,
                    pm_id=pm_id,
                    am_id=am_id,
                    match_score=cand["match_score"],
                    evidence_quality=cand["evidence_quality"],
                    data_completeness=cand["data_completeness"],
                    contradiction_status=cand["contradiction_status"],
                    candidate_rank=rank,
                    status=cand["status"],
                    version=1,
                )
                db.add(new_match)
                db.flush()
                match_id = new_match.id

            cand["match_id"] = match_id

            # Save MatchEvidence entries
            for item in cand["evidence_items"]:
                evidence_entry = MatchEvidence(
                    match_id=match_id,
                    field_name=item["field_name"],
                    am_value=str(item["am_value"]),
                    pm_value=str(item["pm_value"]),
                    comparison_result=item["comparison_result"],
                    weight=item["weight"],
                    score_awarded=item["score_awarded"],
                    contradiction=item["contradiction"],
                    notes=item["notes"],
                    provenance=item.get("provenance", {}),
                )
                db.add(evidence_entry)

        db.commit()

        # Audit the matching run
        AuditService.log_event(
            db=db,
            user_id=user_id,
            role=user_role,
            action="MATCH_CALCULATED" if not force_recalculate else "MATCH_RECALCULATED",
            entity_type="PM",
            entity_id=pm_id,
            details={
                "pm_body_number": pm_case.body_number,
                "top_candidates": [
                    {"am_id": c["am_id"], "am_case_number": c["am_case_number"], "score": c["match_score"]}
                    for c in top_candidates
                ],
                "evaluated_count": len(evaluated_pairs),
            },
        )

        return {
            "pm_id": str(pm_case.id),
            "pm_body_number": str(pm_case.body_number),
            "candidates": top_candidates,
            "total_candidates_evaluated": len(evaluated_pairs),
            "calculation_timestamp": datetime.now(timezone.utc),
        }
