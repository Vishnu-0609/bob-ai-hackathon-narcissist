import json
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.entities import PMCase, AMCase, Match, Reconciliation, AuditLog
from app.services.candidate_service import CandidateService
from app.services.bob_rationale import BobRationaleService
from app.services.bob_evidence_gap import BobEvidenceGapService
from app.services.bob_client import bob_client


# ---------------------------------------------------------------------------
# Natural-language feature extraction helpers
# ---------------------------------------------------------------------------

_COLORS = [
    "red", "blue", "green", "yellow", "black", "white", "grey", "gray",
    "brown", "orange", "pink", "purple", "violet", "navy", "maroon",
    "beige", "cream", "khaki", "olive", "cyan", "turquoise", "gold", "silver",
]

_CLOTHING_ITEMS = [
    "shirt", "t-shirt", "tshirt", "top", "blouse", "kurta", "kurti",
    "jeans", "pants", "trousers", "shorts", "skirt", "saree", "sari",
    "jacket", "coat", "hoodie", "sweater", "dress", "salwar", "dhoti",
    "shoes", "sandals", "chappal", "socks", "cap", "hat", "dupatta",
]

_BODY_FEATURES = {
    "scar": "scars",
    "burn": "scars",
    "birthmark": "birthmarks",
    "mole": "birthmarks",
    "tattoo": "tattoos",
}

_JEWELLERY_ITEMS = ["ring", "watch", "chain", "bracelet", "necklace", "bangle", "earring"]

_SEX_KEYWORDS = {
    "MALE": ["boy", "man", "male", "he", "his", "brother", "son", "father", "uncle", "husband"],
    "FEMALE": ["girl", "woman", "female", "she", "her", "sister", "daughter", "mother", "aunt", "wife"],
}


def _extract_nl_features(query: str) -> Dict[str, Any]:
    """
    Parses a free-text natural language query into structured search filters.
    Handles queries like:
      - "find a red shirt boy"
      - "look for woman with tattoo on arm around 30 years"
      - "man with scar wearing blue jeans, around 160cm"
    """
    lower = query.lower()
    filters: Dict[str, Any] = {}

    # --- Sex ---
    for sex, keywords in _SEX_KEYWORDS.items():
        if any(k in lower for k in keywords):
            filters["sex"] = sex
            break

    # --- Age ---
    # "around 30", "30 years", "30-35", "aged 30"
    range_m = re.search(r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years|yrs|yr)?", lower)
    single_m = re.search(r"(?:around|about|aged?|age)\s*(\d{1,2})\s*(?:years|yrs|yr)?", lower)
    bare_age = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?)\s+(?:old)?", lower)
    if range_m:
        filters["age_min"] = int(range_m.group(1))
        filters["age_max"] = int(range_m.group(2))
    elif single_m:
        val = int(single_m.group(1))
        filters["age_min"] = max(0, val - 5)
        filters["age_max"] = val + 5
    elif bare_age:
        val = int(bare_age.group(1))
        filters["age_min"] = max(0, val - 5)
        filters["age_max"] = val + 5

    # --- Height ---
    cm_m = re.search(r"(\d{2,3})\s*(?:cm|centimeters?)", lower)
    ft_m = re.search(r"(\d)[''′](\d{1,2})?|(\d)\s*(?:feet|ft)\s*(\d{1,2})?\s*(?:in|inches?)?", lower)
    if cm_m:
        filters["height_cm"] = float(cm_m.group(1))
    elif ft_m:
        ft = int(ft_m.group(1) or ft_m.group(3) or 5)
        inch = int(ft_m.group(2) or ft_m.group(4) or 0)
        filters["height_cm"] = round((ft * 12 + inch) * 2.54, 1)

    # --- Clothing (color + item combinations) ---
    clothing_terms: List[str] = []
    for color in _COLORS:
        for item in _CLOTHING_ITEMS:
            pattern = rf"\b{color}\s+{item}\b"
            if re.search(pattern, lower):
                clothing_terms.append(f"{color} {item}")
        # color alone next to a clothing word within 4 words
        if color in lower:
            for item in _CLOTHING_ITEMS:
                if item in lower and color not in [t.split()[0] for t in clothing_terms]:
                    # colour and item both mentioned, treat as loose pair
                    clothing_terms.append(f"{color} {item}")
                    break

    # Standalone clothing items with no colour
    for item in _CLOTHING_ITEMS:
        if item in lower and not any(item in t for t in clothing_terms):
            clothing_terms.append(item)

    if clothing_terms:
        filters["clothing_keywords"] = list(dict.fromkeys(clothing_terms))  # deduplicate preserving order

    # --- Scars / Tattoos / Birthmarks ---
    for keyword, field in _BODY_FEATURES.items():
        if keyword in lower:
            # try to capture body location after keyword
            loc_m = re.search(rf"{keyword}\s*(?:on|at|near|across)?\s*([a-z\s]{{3,25}})", lower)
            loc = loc_m.group(1).strip() if loc_m else None
            filters.setdefault("body_marks", []).append({"type": field, "location": loc})

    # --- Jewellery ---
    for j in _JEWELLERY_ITEMS:
        if j in lower:
            filters.setdefault("jewellery_keywords", []).append(j)

    # --- Blood group ---
    bg_m = re.search(r"\b(a|b|ab|o)\s*([+-]|positive|negative)\b", lower)
    if bg_m:
        g = bg_m.group(1).upper()
        sign = "+" if "+" in bg_m.group(2) or "pos" in bg_m.group(2) else "-"
        filters["blood_group"] = f"{g}{sign}"

    # --- Location keyword ---
    loc_keywords = ["near", "at", "from", "around", "location", "found at", "recovered at"]
    for lk in loc_keywords:
        loc_m = re.search(rf"{lk}\s+([a-z\s\-]{{3,40}}?)(?:\s*,|\s*$|\s+with|\s+wearing|\s+aged)", lower)
        if loc_m:
            filters["location"] = loc_m.group(1).strip()
            break

    return filters


def _json_contains_keyword(json_field: Any, keywords: List[str]) -> bool:
    """
    Checks if a JSON list field (list of strings or dicts) contains any of the given keywords.
    """
    if not json_field:
        return False
    text = json.dumps(json_field).lower()
    return any(k.lower() in text for k in keywords)


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

        elif tool_name == "search_by_description":
            # -----------------------------------------------------------------
            # Natural-language description search across PM and AM records
            # Searches: sex, age range, height, clothing, scars/tattoos/marks,
            #           jewellery, blood group, and recovery/last-seen location.
            # -----------------------------------------------------------------
            filters = params.get("filters", {})
            record_type = params.get("record_type", "BOTH")  # PM, AM, or BOTH
            results: Dict[str, List[Dict]] = {"pm_records": [], "am_records": []}

            # --- PM search ---
            if record_type in ("PM", "BOTH"):
                q = db.query(PMCase).filter(PMCase.incident_id == incident_id)
                if filters.get("sex"):
                    q = q.filter(PMCase.sex.ilike(f"%{filters['sex']}%"))
                if filters.get("age_min") is not None:
                    q = q.filter(PMCase.estimated_age_max >= int(filters["age_min"]))
                if filters.get("age_max") is not None:
                    q = q.filter(PMCase.estimated_age_min <= int(filters["age_max"]))
                if filters.get("blood_group"):
                    q = q.filter(PMCase.blood_group.ilike(f"%{filters['blood_group']}%"))
                if filters.get("location"):
                    q = q.filter(PMCase.recovery_location.ilike(f"%{filters['location']}%"))

                candidates = q.limit(20).all()

                # Post-filter JSON fields (clothing, scars, tattoos, birthmarks) in Python
                for p in candidates:
                    ok = True
                    if filters.get("clothing_keywords"):
                        ok = ok and _json_contains_keyword(p.clothing, filters["clothing_keywords"])
                    if filters.get("body_marks"):
                        for bm in filters["body_marks"]:
                            field = bm["type"]
                            loc = bm.get("location")
                            field_val = getattr(p, field, None)
                            if field_val is not None:
                                match = _json_contains_keyword(field_val, [loc] if loc else [""])
                                ok = ok and (True if not loc else match)
                    if filters.get("jewellery_keywords"):
                        ok = ok and _json_contains_keyword(p.jewellery, filters["jewellery_keywords"])
                    if ok:
                        results["pm_records"].append({
                            "type": "PM",
                            "id": p.body_number,
                            "sex": p.sex,
                            "age_range": f"{p.estimated_age_min}–{p.estimated_age_max}" if p.estimated_age_min else "Unknown",
                            "height_cm": p.height_cm,
                            "blood_group": p.blood_group,
                            "clothing": p.clothing,
                            "location": p.recovery_location,
                            "physical_description": (p.physical_description or "")[:120],
                        })

            # --- AM search ---
            if record_type in ("AM", "BOTH"):
                q = db.query(AMCase).filter(AMCase.incident_id == incident_id)
                if filters.get("sex"):
                    q = q.filter(AMCase.sex.ilike(f"%{filters['sex']}%"))
                if filters.get("age_min") is not None:
                    q = q.filter(AMCase.age >= int(filters["age_min"]))
                if filters.get("age_max") is not None:
                    q = q.filter(AMCase.age <= int(filters["age_max"]))
                if filters.get("blood_group"):
                    q = q.filter(AMCase.blood_group.ilike(f"%{filters['blood_group']}%"))
                if filters.get("location"):
                    q = q.filter(AMCase.last_seen_location.ilike(f"%{filters['location']}%"))

                candidates = q.limit(20).all()

                for a in candidates:
                    ok = True
                    if filters.get("clothing_keywords"):
                        ok = ok and _json_contains_keyword(a.clothing, filters["clothing_keywords"])
                    if filters.get("body_marks"):
                        for bm in filters["body_marks"]:
                            field = bm["type"]
                            loc = bm.get("location")
                            field_val = getattr(a, field, None)
                            if field_val is not None:
                                match = _json_contains_keyword(field_val, [loc] if loc else [""])
                                ok = ok and (True if not loc else match)
                    if filters.get("jewellery_keywords"):
                        ok = ok and _json_contains_keyword(a.jewellery, filters["jewellery_keywords"])
                    if ok:
                        results["am_records"].append({
                            "type": "AM",
                            "id": a.case_number,
                            "name": a.name,
                            "sex": a.sex,
                            "age": a.age,
                            "height_cm": a.height_cm,
                            "blood_group": a.blood_group,
                            "clothing": a.clothing,
                            "last_seen_location": a.last_seen_location,
                            "physical_description": (a.physical_description or "")[:120],
                        })

            return results

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
                    "age_range": f"{p.estimated_age_min}–{p.estimated_age_max}",
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
    def _score_badge(score: float) -> str:
        if score >= 80:
            return "🟢 Strong"
        elif score >= 50:
            return "🟡 Moderate"
        return "🔴 Weak"

    @staticmethod
    def _contradiction_badge(status: str) -> str:
        if "STRONG" in status:
            return "🔴 Strong Contradiction"
        elif "CONTRADICTION" in status:
            return "⚠️ Under Review"
        return "✅ Clear"

    @staticmethod
    def _is_description_search(query: str) -> bool:
        """
        Returns True if the query looks like a natural-language description search
        rather than a structured command.
        """
        lower = query.lower()
        triggers = [
            "find", "search", "look for", "locate", "who is", "any", "wearing",
            "has a", "have a", "with a", "with tattoo", "with scar",
            "shirt", "jeans", "kurta", "jacket", "red", "blue", "green",
            "ring", "watch", "chain", "scar", "tattoo", "birthmark",
        ]
        return any(t in lower for t in triggers)

    @staticmethod
    def _format_description_results(
        tool_res: Dict[str, Any],
        filters: Dict[str, Any],
        query: str,
    ) -> str:
        pm_records = tool_res.get("pm_records", [])
        am_records = tool_res.get("am_records", [])
        total = len(pm_records) + len(am_records)

        # Build a human-readable summary of what was searched
        filter_parts = []
        if filters.get("sex"):
            filter_parts.append(f"**{filters['sex'].title()}**")
        if filters.get("age_min") is not None or filters.get("age_max") is not None:
            lo = filters.get("age_min", "?")
            hi = filters.get("age_max", "?")
            filter_parts.append(f"aged {lo}–{hi}")
        if filters.get("clothing_keywords"):
            filter_parts.append(f"wearing *{', '.join(filters['clothing_keywords'][:3])}*")
        if filters.get("body_marks"):
            for bm in filters["body_marks"]:
                loc = f" on {bm['location']}" if bm.get("location") else ""
                filter_parts.append(f"has {bm['type'].rstrip('s')}{loc}")
        if filters.get("jewellery_keywords"):
            filter_parts.append(f"wearing *{', '.join(filters['jewellery_keywords'])}*")
        if filters.get("blood_group"):
            filter_parts.append(f"blood group **{filters['blood_group']}**")
        if filters.get("location"):
            filter_parts.append(f"near *{filters['location']}*")

        filter_summary = ", ".join(filter_parts) if filter_parts else "the given description"

        if total == 0:
            return (
                f"I searched both ante-mortem and post-mortem records for {filter_summary}, "
                f"but found **no matching records** in this incident.\n\n"
                f"> 💡 Try broadening your search — for example, remove the colour or drop the age range."
            )

        lines = [
            f"I found **{total} record(s)** matching {filter_summary}:\n",
        ]

        if pm_records:
            lines.append(f"### 🔵 Post-Mortem Records ({len(pm_records)} found)\n")
            lines.append("| Body # | Sex | Age | Height | Clothing | Location |")
            lines.append("|--------|-----|-----|--------|----------|----------|")
            for r in pm_records:
                clothing_str = ", ".join(r["clothing"]) if isinstance(r["clothing"], list) else str(r["clothing"] or "—")
                lines.append(
                    f"| **{r['id']}** | {r.get('sex') or '—'} | {r.get('age_range', '—')} "
                    f"| {r.get('height_cm') or '—'} cm | {clothing_str[:40] or '—'} | {r.get('location') or '—'} |"
                )
            lines.append("")

        if am_records:
            lines.append(f"### 🟠 Ante-Mortem Records ({len(am_records)} found)\n")
            lines.append("| Case # | Name | Sex | Age | Height | Clothing | Last Seen |")
            lines.append("|--------|------|-----|-----|--------|----------|-----------|")
            for r in am_records:
                clothing_str = ", ".join(r["clothing"]) if isinstance(r["clothing"], list) else str(r["clothing"] or "—")
                lines.append(
                    f"| **{r['id']}** | {r.get('name', '—')} | {r.get('sex') or '—'} | {r.get('age') or '—'} "
                    f"| {r.get('height_cm') or '—'} cm | {clothing_str[:40] or '—'} | {r.get('last_seen_location') or '—'} |"
                )
            lines.append("")

        lines.append(
            "> Results are filtered by available structured data. "
            "Open any record to view full details and run candidate matching."
        )

        return "\n".join(lines)

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
        pm_match = re.search(r"\b(pm[-_\s]?\d{1,4})\b", lower)
        am_match = re.search(r"\b(am[-_\s]?\d{1,4})\b", lower)

        target_pm = context_pm_id
        target_am = context_am_id

        if pm_match:
            target_pm = pm_match.group(1).replace(" ", "-").upper()
        if am_match:
            target_am = am_match.group(1).replace(" ", "-").upper()

        # --- Intent: Explain why AM ranked for PM ---
        if "why" in lower and target_pm and target_am:
            tool_res = BobCopilotService._execute_controlled_tool(
                "explain_candidate_ranking",
                {"pm_id": target_pm, "am_id": target_am},
                db,
                incident_id,
            )
            tools_used.append({
                "tool": "explain_candidate_ranking",
                "parameters": {"pm_id": target_pm, "am_id": target_am},
                "result": tool_res,
            })
            rationale = tool_res.get("rationale", "Candidate evaluation completed.")
            return {
                "response": rationale,
                "tools_used": tools_used,
                "suggested_actions": [
                    "Open Candidate Reconciliation",
                    "Generate Reconciliation PDF",
                    "Inspect Evidence Graph",
                ],
                "intent": "EXPLAIN_RANKING",
            }

        # --- Intent: Show top candidates for a PM ---
        elif ("candidate" in lower or ("show" in lower and target_pm)) and not BobCopilotService._is_description_search(lower):
            active_pm = target_pm or "PM-017"
            tool_res = BobCopilotService._execute_controlled_tool(
                "get_candidates_for_pm",
                {"pm_id": active_pm},
                db,
                incident_id,
            )
            tools_used.append({
                "tool": "get_candidates_for_pm",
                "parameters": {"pm_id": active_pm},
                "result": tool_res,
            })
            cands = tool_res.get("candidates", [])

            if not cands:
                resp = (
                    f"I checked the records for **{active_pm}**, but no candidate matches have been "
                    f"calculated yet. You may need to run the matching engine first."
                )
            else:
                lines = [
                    f"Here are the top candidate matches for **{active_pm}**:\n",
                    "| # | Case | Name | Score | Status | Contradictions |",
                    "|---|------|------|-------|--------|----------------|",
                ]
                for c in cands:
                    badge = BobCopilotService._score_badge(c["score"])
                    contra = BobCopilotService._contradiction_badge(c["contradiction_status"])
                    lines.append(
                        f"| {c['rank']} | **{c['am_case_number']}** | {c['name']} "
                        f"| {badge} **{c['score']}/100** | `{c['status']}` | {contra} |"
                    )
                lines.append("")
                lines.append(
                    "> Scores are deterministic ranking indicators — not probabilities. "
                    "A coordinator must review and confirm any identification."
                )
                resp = "\n".join(lines)

            return {
                "response": resp,
                "tools_used": tools_used,
                "suggested_actions": [
                    f"Reconcile {active_pm}",
                    "View Evidence Graph",
                    "Filter PM Cases",
                ],
                "intent": "SHOW_CANDIDATES",
            }

        # --- Intent: Natural language description search ---
        elif BobCopilotService._is_description_search(lower):
            filters = _extract_nl_features(query)

            tool_res = BobCopilotService._execute_controlled_tool(
                "search_by_description",
                {"filters": filters, "record_type": "BOTH"},
                db,
                incident_id,
            )
            tools_used.append({
                "tool": "search_by_description",
                "parameters": {"filters": filters},
                "result": {"pm_count": len(tool_res.get("pm_records", [])), "am_count": len(tool_res.get("am_records", []))},
            })

            resp = BobCopilotService._format_description_results(tool_res, filters, query)
            total = len(tool_res.get("pm_records", [])) + len(tool_res.get("am_records", []))

            suggestions = []
            if tool_res.get("pm_records"):
                suggestions.append(f"Open {tool_res['pm_records'][0]['id']} PM Record")
            if tool_res.get("am_records"):
                suggestions.append(f"Open {tool_res['am_records'][0]['id']} AM Record")
            suggestions.append("Run Matching Recalculation")

            return {
                "response": resp,
                "tools_used": tools_used,
                "suggested_actions": suggestions,
                "intent": "DESCRIPTION_SEARCH",
            }

        # --- Intent: Contradictions / conflicts ---
        elif "contradict" in lower or "conflict" in lower:
            tool_res = BobCopilotService._execute_controlled_tool(
                "list_unresolved_contradictions",
                {},
                db,
                incident_id,
            )
            tools_used.append({
                "tool": "list_unresolved_contradictions",
                "parameters": {},
                "result": tool_res,
            })
            count = len(tool_res) if isinstance(tool_res, list) else 0

            if count == 0:
                resp = "✅ Great news — no active anatomical or biological contradictions are flagged for this incident right now."
            else:
                lines = [
                    f"I found **{count} case pair(s)** with unresolved contradictions that need attention before sign-off:\n",
                    "| Match | PM | AM | Score | Status |",
                    "|-------|----|----|-------|--------|",
                ]
                for m in (tool_res if isinstance(tool_res, list) else []):
                    badge = BobCopilotService._score_badge(m.get("score", 0))
                    contra = BobCopilotService._contradiction_badge(m.get("status", ""))
                    lines.append(
                        f"| `{m.get('match_id', '')}` | {m.get('pm_id', '')} | {m.get('am_id', '')} "
                        f"| {badge} {m.get('score', 0)}/100 | {contra} |"
                    )
                lines.append("")
                lines.append(
                    "> Recommend reviewing each of these with a senior forensic pathologist before proceeding to reconciliation."
                )
                resp = "\n".join(lines)

            return {
                "response": resp,
                "tools_used": tools_used,
                "suggested_actions": [
                    "Review Contradictions in Dashboard",
                    "Filter Strong Contradictions",
                ],
                "intent": "LIST_CONTRADICTIONS",
            }

        # --- Intent: Filter unidentified bodies (simple sex/age filter) ---
        elif "filter" in lower or (("male" in lower or "female" in lower) and not BobCopilotService._is_description_search(lower)):
            f_sex = "MALE" if "male" in lower and "female" not in lower else ("FEMALE" if "female" in lower else None)
            tool_res = BobCopilotService._execute_controlled_tool(
                "filter_unidentified_bodies",
                {"sex": f_sex},
                db,
                incident_id,
            )
            tools_used.append({
                "tool": "filter_unidentified_bodies",
                "parameters": {"sex": f_sex},
                "result": tool_res,
            })
            count = len(tool_res) if isinstance(tool_res, list) else 0
            sex_label = f_sex.title() if f_sex else "All"

            if count == 0:
                resp = f"No unidentified {sex_label.lower()} PM records matched your filter for this incident."
            else:
                lines = [
                    f"Found **{count} unidentified PM record(s)** — {sex_label}:\n",
                    "| Body # | Sex | Age Range | Height | Location |",
                    "|--------|-----|-----------|--------|----------|",
                ]
                for p in (tool_res if isinstance(tool_res, list) else []):
                    lines.append(
                        f"| **{p.get('body_number', '')}** | {p.get('sex', '—')} "
                        f"| {p.get('age_range', '—')} | {p.get('height_cm', '—')} cm "
                        f"| {p.get('location', '—')} |"
                    )
                resp = "\n".join(lines)

            return {
                "response": resp,
                "tools_used": tools_used,
                "suggested_actions": ["Open PM Records Table", "Run Matching Recalculation"],
                "intent": "FILTER_PM",
            }

        # --- General / greeting ---
        return {
            "response": (
                "Hi, I'm **Bob** — your DVI Coordinator Copilot. 👋\n\n"
                "I can search case records, explain match scores, track missing evidence, "
                "and surface anything that needs your attention before sign-off.\n\n"
                "**You can describe people in plain language, like:**\n"
                "- *Find a red shirt boy around 25 years*\n"
                "- *Look for a woman with a tattoo on her arm*\n"
                "- *Search for male, B+ blood group, wearing blue jeans*\n"
                "- *Man with scar near left arm, 160cm tall*\n\n"
                "**Or use structured commands:**\n"
                "- *Why is AM-042 ranked first for PM-017?*\n"
                "- *Show top candidates for PM-017*\n"
                "- *Show cases with conflicting information*\n\n"
                "> 💡 Open any PM record and I'll automatically have that case in context."
            ),
            "tools_used": tools_used,
            "suggested_actions": [
                "Show PM-017 Candidates",
                "Audit Chain Integrity Status",
                "Evaluation Metrics Benchmark",
            ],
            "intent": "GENERAL_QUERY",
        }
