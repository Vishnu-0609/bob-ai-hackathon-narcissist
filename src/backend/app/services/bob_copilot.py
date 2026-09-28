import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import PMCase, AMCase, Match, Reconciliation, AuditLog
from app.services.candidate_service import CandidateService
from app.services.bob_rationale import BobRationaleService
from app.services.bob_evidence_gap import BobEvidenceGapService
from app.services.bob_client import bob_client


class BobCopilotService:
    @staticmethod
    def _execute_controlled_tool(
        tool_name: str,
        params: Dict[str, Any],
        db: Session,
        incident_id: str,
    ) -> Any:
        """
        Executes strictly parameterized, safe Python/SQLAlchemy queries. Never executes raw SQL.
        """
        if tool_name == "get_candidates_for_pm":
            pm_identifier = params.get("pm_id") or params.get("body_number")
            pm = (
                db.query(PMCase)
                .filter((PMCase.id == pm_identifier) | (PMCase.body_number == pm_identifier))
                .first()
            )
            if not pm:
                return {"error": f"PM record '{pm_identifier}' not found."}
            res = CandidateService.get_or_calculate_candidates(db, str(pm.id), limit=3)
            return {
                "pm_body_number": pm.body_number,
                "candidates": [
                    {
                        "rank": c["candidate_rank"],
                        "am_case_number": c["am_case_number"],
                        "name": c["am_name"],
                        "score": c["match_score"],
                        "status": c["status"],
                        "contradiction_status": c["contradiction_status"],
                    }
                    for c in res.get("candidates", [])
                ],
            }

        elif tool_name == "explain_candidate_ranking":
            pm_id = params.get("pm_id")
            am_id = params.get("am_id")
            pm = db.query(PMCase).filter((PMCase.id == pm_id) | (PMCase.body_number == pm_id)).first()
            am = db.query(AMCase).filter((AMCase.id == am_id) | (AMCase.case_number == am_id)).first()
            if not pm or not am:
                return {"error": "PM or AM case not found."}
            from app.services.matching_engine import MatchingEngine
            engine = MatchingEngine()
            eval_res = engine.evaluate_pair(pm, am)
            rationale = BobRationaleService._generate_local_rationale(eval_res)
            return {"evaluation": eval_res, "rationale": rationale}

        elif tool_name == "filter_unidentified_bodies":
            query = db.query(PMCase).filter(PMCase.incident_id == incident_id)
            if params.get("sex"):
                query = query.filter(PMCase.sex.ilike(f"%{params['sex']}%"))
            if params.get("age_min") is not None:
                query = query.filter(PMCase.estimated_age_max >= int(params["age_min"]))
            if params.get("age_max") is not None:
                query = query.filter(PMCase.estimated_age_min <= int(params["age_max"]))
            if params.get("location"):
                query = query.filter(PMCase.recovery_location.ilike(f"%{params['location']}%"))

            results = query.limit(10).all()
            return [
                {
                    "body_number": p.body_number,
                    "sex": p.sex,
                    "age_range": f"{p.estimated_age_min}-{p.estimated_age_max}",
                    "height_cm": p.height_cm,
                    "location": p.recovery_location,
                }
                for p in results
            ]

        elif tool_name == "list_unresolved_contradictions":
            matches = (
                db.query(Match)
                .filter(
                    Match.incident_id == incident_id,
                    Match.contradiction_status.in_(["CONTRADICTION_REVIEW", "STRONG_CONTRADICTION"]),
                )
                .limit(10)
                .all()
            )
            return [
                {
                    "match_id": m.id,
                    "pm_id": m.pm_id,
                    "am_id": m.am_id,
                    "score": m.match_score,
                    "status": m.contradiction_status,
                }
                for m in matches
            ]

        elif tool_name == "get_audit_history":
            entity_id = params.get("entity_id")
            logs = (
                db.query(AuditLog)
                .filter(AuditLog.entity_id == entity_id)
                .order_by(AuditLog.timestamp.desc())
                .limit(5)
                .all()
            )
            return [
                {
                    "event_id": l.event_id,
                    "action": l.action,
                    "user_id": l.user_id,
                    "timestamp": l.timestamp.isoformat(),
                    "details": l.details,
                }
                for l in logs
            ]

        return {"error": f"Unknown tool: {tool_name}"}

    @staticmethod
    async def process_copilot_query(
        query: str,
        incident_id: str,
        context_pm_id: Optional[str],
        context_am_id: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        """
        Coordinates user questions, maps natural language to safe tools, and synthesizes responses.
        """
        lower = query.lower()
        tools_used: List[Dict[str, Any]] = []

        # Intent detection
        # 1. Why is AM-X ranked for PM-Y?
        why_match = re.search(r"why is\s+([a-z0-9\-_]+)\s+(?:ranked|associated|matched)", lower)
        pm_match = re.search(r"\b(pm[-_\s]?\d{1,4})\b", lower)
        am_match = re.search(r"\b(am[-_\s]?\d{1,4})\b", lower)

        target_pm = context_pm_id
        target_am = context_am_id

        if pm_match:
            target_pm = pm_match.group(1).replace(" ", "-").upper()
        if am_match:
            target_am = am_match.group(1).replace(" ", "-").upper()

        if "why" in lower and target_pm and target_am:
            tool_res = BobCopilotService._execute_controlled_tool(
                "explain_candidate_ranking",
                {"pm_id": target_pm, "am_id": target_am},
                db,
                incident_id,
            )
            tools_used.append({"tool": "explain_candidate_ranking", "parameters": {"pm_id": target_pm, "am_id": target_am}, "result": tool_res})
            rationale = tool_res.get("rationale", "Candidate evaluation completed.")
            return {
                "response": f"### Ranking Rationale for {target_am} ↔ {target_pm}\n\n{rationale}",
                "tools_used": tools_used,
                "suggested_actions": ["Open Candidate Reconciliation", "Generate Reconciliation PDF", "Inspect Evidence Graph"],
                "intent": "EXPLAIN_RANKING",
            }

        elif "candidate" in lower or ("show" in lower and target_pm):
            active_pm = target_pm or "PM-017"
            tool_res = BobCopilotService._execute_controlled_tool(
                "get_candidates_for_pm",
                {"pm_id": active_pm},
                db,
                incident_id,
            )
            tools_used.append({"tool": "get_candidates_for_pm", "parameters": {"pm_id": active_pm}, "result": tool_res})
            cands = tool_res.get("candidates", [])
            if not cands:
                resp = f"No candidate matches found yet for body {active_pm}."
            else:
                lines = [f"**Top candidates for {active_pm}:**\n"]
                for c in cands:
                    lines.append(f"{c['rank']}. **{c['am_case_number']}** ({c['name']}) — **Score: {c['score']}/100** | Status: `{c['status']}` | Contradictions: `{c['contradiction_status']}`")
                resp = "\n".join(lines)
            return {
                "response": resp,
                "tools_used": tools_used,
                "suggested_actions": [f"Reconcile {active_pm}", "View Evidence Graph", "Filter PM Cases"],
                "intent": "SHOW_CANDIDATES",
            }

        elif "contradict" in lower or "conflict" in lower:
            tool_res = BobCopilotService._execute_controlled_tool(
                "list_unresolved_contradictions",
                {},
                db,
                incident_id,
            )
            tools_used.append({"tool": "list_unresolved_contradictions", "parameters": {}, "result": tool_res})
            count = len(tool_res) if isinstance(tool_res, list) else 0
            return {
                "response": f"Found **{count} case pairs** with active anatomical or biological contradictions under review. Recommend inspecting these before final coordinator sign-off.",
                "tools_used": tools_used,
                "suggested_actions": ["Review Contradictions in Dashboard", "Filter Strong Contradictions"],
                "intent": "LIST_CONTRADICTIONS",
            }

        elif "filter" in lower or "male" in lower or "female" in lower or "age" in lower:
            # Extract filters safely
            f_sex = "MALE" if "male" in lower and "female" not in lower else ("FEMALE" if "female" in lower else None)
            tool_res = BobCopilotService._execute_controlled_tool(
                "filter_unidentified_bodies",
                {"sex": f_sex},
                db,
                incident_id,
            )
            tools_used.append({"tool": "filter_unidentified_bodies", "parameters": {"sex": f_sex}, "result": tool_res})
            return {
                "response": f"Found **{len(tool_res)} matching PM records** matching your criteria. Parameterized query executed safely with zero raw SQL.",
                "tools_used": tools_used,
                "suggested_actions": ["Open PM Records Table", "Run Matching Recalculation"],
                "intent": "FILTER_PM",
            }

        # General helpful response
        return {
            "response": (
                "I am your **IBM Bob DVI Coordinator Copilot**. I can help you investigate cases, explain candidate match scores, "
                "identify missing forensic evidence, draft reconciliation reports, and track audit history.\n\n"
                "**Try asking:**\n"
                "- *'Why is AM-042 ranked first for PM-017?'*\n"
                "- *'Show top candidates for PM-017'*\n"
                "- *'Show cases with conflicting scar or tattoo information'*\n"
                "- *'Filter unidentified male bodies'* "
            ),
            "tools_used": tools_used,
            "suggested_actions": ["Show PM-017 Candidates", "Audit Chain Integrity Status", "Evaluation Metrics Benchmark"],
            "intent": "GENERAL_QUERY",
        }
