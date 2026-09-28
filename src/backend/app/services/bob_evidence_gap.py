from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.services.bob_client import bob_client


class BobEvidenceGapService:
    @staticmethod
    def _local_evidence_gaps(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines evidence gaps and recommended verification workflows from structured comparison data.
        """
        supporting = candidate_data.get("supporting_evidence", [])
        contradictions = candidate_data.get("contradictions", [])
        unknown = candidate_data.get("unknown", [])

        available: List[str] = [item.get("field_name", "").replace("_", " ").title() for item in supporting]
        missing: List[str] = [item.get("field_name", "").replace("_", " ").title() for item in unknown]
        conflicts: List[str] = [
            f"**{c.get('field_name', '').replace('_', ' ').title()}** — {c.get('notes', 'Conflict observed')}"
            for c in contradictions
        ]

        recommendations: List[str] = []

        if any("dental" in item.get("field_name", "") for item in unknown):
            recommendations.append("📋 Request ante-mortem dental records or commission a post-mortem odontological chart.")

        if any("fingerprint" in item.get("field_name", "") for item in unknown) or candidate_data.get("data_completeness", 0) < 60:
            recommendations.append("🖐️ Attempt comparative dactyloscopic (fingerprint) examination if friction ridges are preserved.")

        if contradictions:
            recommendations.append("🔬 Arrange a re-examination of the flagged anatomical areas with a senior forensic pathologist.")

        if candidate_data.get("match_score", 0) >= 75 and not any("dental" in f.lower() for f in available):
            recommendations.append("🧬 Collect familial buccal swabs for STR/DNA profiling to confirm this candidate.")

        if not recommendations:
            recommendations.append("✅ Standard verification protocol is complete. Case is ready for coordinator review.")

        score = candidate_data.get("match_score", 0)
        completeness = candidate_data.get("data_completeness", "N/A")

        summary_lines = [
            f"## Evidence Gap Report",
            f"> **Match Score:** {score}/100 &nbsp;|&nbsp; **Data Completeness:** {completeness}%",
            "",
            f"Here's a quick picture of where this case stands:",
            f"- **{len(available)}** confirmed attributes are on record",
            f"- **{len(missing)}** attributes are missing or unverified",
            f"- **{len(conflicts)}** contradiction(s) need resolution before this case can move forward",
        ]

        return {
            "available_evidence": available,
            "missing_evidence": missing,
            "unresolved_contradictions": conflicts,
            "recommended_workflow": recommendations,
            "summary": "\n".join(summary_lines),
        }

    @staticmethod
    async def analyze_evidence_gaps(
        candidate_data: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes Evidence-Gap analysis with IBM Bob agent and local fallback.
        """
        prompt = (
            "You are Bob, a forensic evidence specialist helping DVI coordinators identify gaps in their case files.\n\n"
            "Look at the structured comparison package provided and explain — in plain, conversational language — "
            "what forensic evidence is already confirmed, what's missing, and what the coordinator should do next.\n\n"
            "Format your response with:\n"
            "- **What we have** — confirmed evidence points\n"
            "- **What's missing** — gaps that weaken the match\n"
            "- **Conflicts to resolve** — any contradicting data\n"
            "- **Recommended next steps** — specific, actionable follow-ups\n\n"
            "Be direct and practical. Avoid legal or probabilistic language."
        )

        api_result = await bob_client.call_bob_api(
            agent_name="EVIDENCE_GAP",
            payload={"candidate_evidence": candidate_data, "instruction": prompt},
            db=db,
        )

        if api_result.get("success") and "data" in api_result:
            return api_result["data"]

        return BobEvidenceGapService._local_evidence_gaps(candidate_data)
