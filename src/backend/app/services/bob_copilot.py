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

# ---------------------------------------------------------------------------
# Natural-language feature extraction helpers
# ---------------------------------------------------------------------------

_COLORS = [
    "red", "blue", "green", "yellow", "black", "white", "grey", "gray",
    "brown", "orange", "pink", "purple", "violet", "navy", "maroon",
    "beige", "cream", "khaki", "olive", "cyan", "turquoise", "gold", "silver", "metallic", "dark blue", "light blue"
]

_CLOTHING_ITEMS = [
    "shirt", "t-shirt", "tshirt", "tee", "polo", "polo shirt", "top", "blouse", "kurta", "kurti",
    "jeans", "pants", "trousers", "shorts", "skirt", "saree", "sari",
    "jacket", "coat", "hoodie", "sweater", "dress", "salwar", "dhoti",
    "shoe", "shoes", "sneaker", "sneakers", "trainer", "trainers", "boot", "boots", "footwear",
    "sandal", "sandals", "chappal", "socks", "cap", "hat", "dupatta", "suit", "blazer", "vest", "moncler", "chinos", "denim"
]

_BODY_FEATURES = {
    "scar": "scars",
    "scars": "scars",
    "burn": "scars",
    "burns": "scars",
    "birthmark": "birthmarks",
    "birthmarks": "birthmarks",
    "mole": "birthmarks",
    "moles": "birthmarks",
    "tattoo": "tattoos",
    "tattoos": "tattoos",
    "ink": "tattoos",
}

_JEWELLERY_ITEMS = [
    "ring", "rings", "watch", "watches", "wristwatch", "wristwatches", "analog", "digital", "timepiece", "chronograph",
    "chain", "chains", "bracelet", "bracelets", "necklace", "necklaces", "bangle", "bangles",
    "earring", "earrings", "stud", "studs", "pendant", "pendants", "anklet", "cuff", "strap", "case", "circular", "bezel"
]

_SEX_KEYWORDS = {
    "FEMALE": ["girl", "woman", "female", r"\bshe\b", r"\bher\b", "sister", "daughter", "mother", "aunt", "wife"],
    "MALE": [r"\bboy\b", r"\bman\b", r"\bmale\b", r"\bhe\b", r"\bhis\b", "brother", r"\bson\b", "father", "uncle", "husband"],
}

_STOP_WORDS = {
    "a", "an", "the", "person", "someone", "individual", "with", "having", "wearing",
    "of", "and", "or", "in", "on", "at", "about", "around", "near", "find", "search",
    "show", "me", "look", "for", "please", "case", "cases", "who", "is", "body", "record", "records"
}


def _extract_nl_features(query: str) -> Dict[str, Any]:
    """
    Parses a free-text natural language query into structured search filters and token representations.
    Handles complex forensic queries like:
      - "a person with Analog wristwatch with a gold-colored circular casewith grey shoe"
      - "find a red shirt boy around 25 years"
      - "look for woman with tattoo on left forearm wearing Moncler polo"
    """
    # Normalize concatenated prepositions like 'casewith' -> 'case with'
    normalized = re.sub(r"([a-zA-Z]+)(with|and|in|on|at|near)([a-zA-Z]+)", r"\1 \2 \3", query, flags=re.IGNORECASE)
    lower = normalized.lower()
    filters: Dict[str, Any] = {}

    # Extract all meaningful tokens for fuzzy and semantic intersection
    all_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", lower) if t not in _STOP_WORDS and len(t) > 1]
    filters["tokens"] = all_tokens

    # --- Sex ---
    for sex in ("FEMALE", "MALE"):
        keywords = _SEX_KEYWORDS[sex]
        if any(re.search(k, lower) for k in keywords):
            filters["sex"] = sex
            break

    # --- Age ---
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

    # --- Clothing & Footwear terms ---
    clothing_terms: List[str] = []
    for color in _COLORS:
        for item in _CLOTHING_ITEMS:
            pattern = rf"\b{color}\s+{item}\b"
            if re.search(pattern, lower):
                clothing_terms.append(f"{color} {item}")
        if re.search(rf"\b{color}\b", lower):
            for item in _CLOTHING_ITEMS:
                if re.search(rf"\b{item}\b", lower) and not any(t.startswith(color) for t in clothing_terms):
                    clothing_terms.append(f"{color} {item}")
                    break

    for item in _CLOTHING_ITEMS:
        if re.search(rf"\b{item}\b", lower) and not any(item in t for t in clothing_terms):
            clothing_terms.append(item)

    if clothing_terms:
        filters["clothing_keywords"] = list(dict.fromkeys(clothing_terms))

    # --- Scars / Tattoos / Marks ---
    for keyword, field in _BODY_FEATURES.items():
        if keyword in lower:
            loc_m = re.search(rf"{keyword}\s*(?:on|at|near|across)?\s*([a-z\s]{{3,25}})", lower)
            loc = loc_m.group(1).strip() if loc_m else None
            if loc:
                loc = re.split(r"\s+(?:around|about|age|year|wearing|with|and)", loc)[0].strip()
            filters.setdefault("body_marks", []).append({"type": field, "location": loc or None})

    # --- Jewellery & Watch Accessories ---
    jewellery_terms: List[str] = []
    for j in _JEWELLERY_ITEMS:
        if re.search(rf"\b{j}\b", lower):
            jewellery_terms.append(j)
    if jewellery_terms:
        filters["jewellery_keywords"] = list(dict.fromkeys(jewellery_terms))

    # --- Blood group ---
    bg_m = re.search(r"\b(a|b|ab|o)\s*([+-]|positive|negative)\b", lower)
    if bg_m:
        g = bg_m.group(1).upper()
        sign = "+" if "+" in bg_m.group(2) or "pos" in bg_m.group(2) else "-"
        filters["blood_group"] = f"{g}{sign}"

    # --- Location keyword ---
    loc_keywords = ["near", "at", "from", "around", "location", "found at", "recovered at", "last seen near", "last seen at"]
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


def _score_record_against_query(
    record: Any,
    filters: Dict[str, Any],
    query_tokens: List[str],
) -> Tuple[float, List[str]]:
    """
    Computes a forensic relevance score (0.0 to 100.0) and human-readable match explanations.
    Evaluates demographics, clothing extractions, jewellery, tattoos, scars, and photo notes.
    """
    score = 0.0
    reasons = []

    clothing_str = " ".join([c.get("description", str(c)) if isinstance(c, dict) else str(c) for c in (record.clothing or [])]).lower()
    jewellery_str = " ".join([j.get("description", str(j)) if isinstance(j, dict) else str(j) for j in (record.jewellery or [])]).lower()
    tattoos_str = " ".join([t.get("description", str(t)) if isinstance(t, dict) else str(t) for t in (record.tattoos or [])]).lower()
    scars_str = " ".join([s.get("description", str(s)) if isinstance(s, dict) else str(s) for s in (record.scars or [])] + [b.get("description", str(b)) if isinstance(b, dict) else str(b) for b in (record.birthmarks or [])]).lower()
    phys_str = (record.physical_description or "").lower()

    # 1. Jewellery match
    j_matches = []
    if filters.get("jewellery_keywords"):
        for jk in filters["jewellery_keywords"]:
            if jk in jewellery_str:
                j_matches.append(jk)
    # Also check full token matches in jewellery
    for t in query_tokens:
        if t in ["watch", "wristwatch", "analog", "circular", "gold", "strap", "case"] and t in jewellery_str and t not in j_matches:
            j_matches.append(t)

    if j_matches:
        j_weight = min(40.0, 15.0 + (len(set(j_matches)) * 7.0))
        score += j_weight
        reasons.append(f"Jewellery/Watch matching ({', '.join(set(j_matches))})")

    # 2. Clothing & Footwear match
    c_matches = []
    if filters.get("clothing_keywords"):
        for ck in filters["clothing_keywords"]:
            if any(part in clothing_str for part in ck.split()):
                c_matches.append(ck)
    for t in query_tokens:
        if t in ["shoe", "shoes", "sneaker", "sneakers", "grey", "gray", "white", "black", "blue", "moncler", "polo", "shirt", "trousers", "jeans"] and t in clothing_str and t not in c_matches:
            c_matches.append(t)

    if c_matches:
        c_weight = min(40.0, 15.0 + (len(set(c_matches)) * 6.0))
        score += c_weight
        reasons.append(f"Clothing/Footwear matching ({', '.join(set(c_matches))})")

    # 3. Tattoos & Marks match
    t_matches = []
    for t in query_tokens:
        if t in tattoos_str or t in scars_str:
            t_matches.append(t)
    if t_matches:
        score += 20.0
        reasons.append(f"Marks/Tattoos matching ({', '.join(set(t_matches))})")

    # 4. Demographic matches
    if filters.get("sex") and record.sex and filters["sex"].upper() == record.sex.upper():
        score += 10.0
        reasons.append(f"Sex ({record.sex})")

    # 5. Token coverage across entire record text
    full_text = f"{clothing_str} {jewellery_str} {tattoos_str} {scars_str} {phys_str}"
    if query_tokens:
        matched_tok_count = sum(1 for t in query_tokens if t in full_text)
        tok_ratio = matched_tok_count / len(query_tokens)
        score += (tok_ratio * 30.0)

    score = min(100.0, round(score, 1))
    return score, reasons


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
            filters = params.get("filters", {})
            record_type = params.get("record_type", "BOTH")
            query_tokens = filters.get("tokens", [])
            results: Dict[str, List[Dict]] = {"pm_records": [], "am_records": []}

            # --- PM Search ---
            if record_type in ("PM", "BOTH"):
                pms = db.query(PMCase).filter(PMCase.incident_id == incident_id).all()
                scored_pms = []
                for p in pms:
                    s, r = _score_record_against_query(p, filters, query_tokens)
                    if s >= 15.0 or (not query_tokens and not filters):
                        clothing_display = ", ".join([c.get("description", str(c)) if isinstance(c, dict) else str(c) for c in (p.clothing or [])]) or "None"
                        jewellery_display = ", ".join([j.get("description", str(j)) if isinstance(j, dict) else str(j) for j in (p.jewellery or [])]) or "None"
                        scored_pms.append({
                            "type": "PM",
                            "id": p.body_number,
                            "uuid": str(p.id),
                            "score": s,
                            "reasons": r,
                            "sex": p.sex,
                            "age_range": f"{p.estimated_age_min}–{p.estimated_age_max}" if p.estimated_age_min else "Unknown",
                            "height_cm": p.height_cm,
                            "blood_group": p.blood_group,
                            "clothing": clothing_display,
                            "jewellery": jewellery_display,
                            "location": p.recovery_location,
                            "physical_description": (p.physical_description or "")[:120],
                        })
                scored_pms.sort(reverse=True, key=lambda x: x["score"])
                results["pm_records"] = scored_pms[:10]

            # --- AM Search ---
            if record_type in ("AM", "BOTH"):
                ams = db.query(AMCase).filter(AMCase.incident_id == incident_id).all()
                scored_ams = []
                for a in ams:
                    s, r = _score_record_against_query(a, filters, query_tokens)
                    if s >= 15.0 or (not query_tokens and not filters):
                        clothing_display = ", ".join([c.get("description", str(c)) if isinstance(c, dict) else str(c) for c in (a.clothing or [])]) or "None"
                        jewellery_display = ", ".join([j.get("description", str(j)) if isinstance(j, dict) else str(j) for j in (a.jewellery or [])]) or "None"
                        scored_ams.append({
                            "type": "AM",
                            "id": a.case_number,
                            "uuid": str(a.id),
                            "score": s,
                            "reasons": r,
                            "name": a.name,
                            "sex": a.sex,
                            "age": a.age,
                            "height_cm": a.height_cm,
                            "blood_group": a.blood_group,
                            "clothing": clothing_display,
                            "jewellery": jewellery_display,
                            "last_seen_location": a.last_seen_location,
                            "physical_description": (a.physical_description or "")[:120],
                        })
                scored_ams.sort(reverse=True, key=lambda x: x["score"])
                results["am_records"] = scored_ams[:10]

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
            "has a", "have a", "with a", "with tattoo", "with scar", "person", "man", "woman", "boy", "girl",
            "shirt", "jeans", "kurta", "jacket", "red", "blue", "green", "grey", "gray", "white", "black", "gold", "silver",
            "ring", "watch", "wristwatch", "analog", "chain", "scar", "tattoo", "birthmark", "shoe", "shoes", "sneaker", "sneakers"
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
            filter_parts.append(f"clothing: *{', '.join(filters['clothing_keywords'][:3])}*")
        if filters.get("jewellery_keywords"):
            filter_parts.append(f"jewellery/watch: *{', '.join(filters['jewellery_keywords'][:3])}*")
        if filters.get("body_marks"):
            for bm in filters["body_marks"]:
                loc = f" on {bm['location']}" if bm.get("location") else ""
                filter_parts.append(f"has {bm['type'].rstrip('s')}{loc}")
        if filters.get("blood_group"):
            filter_parts.append(f"blood group **{filters['blood_group']}**")
        if filters.get("location"):
            filter_parts.append(f"near *{filters['location']}*")

        filter_summary = ", ".join(filter_parts) if filter_parts else f"“{query}”"

        if total == 0:
            return (
                f"I searched both Ante-Mortem (AM) and Post-Mortem (PM) forensic records for {filter_summary}, "
                f"but found **no matching records** in this incident.\n\n"
                f"> 💡 Try broadening your search or checking spelling."
            )

        lines = [
            f"I found **{total} record(s)** matching {filter_summary} (ranked by visual & demographic relevance):\n",
        ]

        if am_records:
            lines.append(f"### 🟠 Ante-Mortem Records ({len(am_records)} found)\n")
            lines.append("| Case # | Name | Relevance | Matched Observables | Jewellery & Accessories | Visible Clothing |")
            lines.append("|--------|------|-----------|---------------------|--------------------------|------------------|")
            for r in am_records:
                match_badge = BobCopilotService._score_badge(r.get("score", 0))
                reasons_str = "; ".join(r.get("reasons", [])[:2]) or "Visual concordance"
                lines.append(
                    f"| **{r['id']}** | {r.get('name', '—')} | {match_badge} **{r.get('score', 0):.0f}%** "
                    f"| {reasons_str} | {r.get('jewellery', '—')[:45]} | {r.get('clothing', '—')[:45]} |"
                )
            lines.append("")

        if pm_records:
            lines.append(f"### 🔵 Post-Mortem Records ({len(pm_records)} found)\n")
            lines.append("| Body # | Relevance | Matched Observables | Jewellery & Accessories | Visible Clothing | Recovery |")
            lines.append("|--------|-----------|---------------------|--------------------------|------------------|----------|")
            for r in pm_records:
                match_badge = BobCopilotService._score_badge(r.get("score", 0))
                reasons_str = "; ".join(r.get("reasons", [])[:2]) or "Visual concordance"
                lines.append(
                    f"| **{r['id']}** | {match_badge} **{r.get('score', 0):.0f}%** "
                    f"| {reasons_str} | {r.get('jewellery', '—')[:45]} | {r.get('clothing', '—')[:45]} | {r.get('location', '—')} |"
                )
            lines.append("")

        lines.append(
            "> 🔍 **Click on any Case # or Body #** above to inspect full forensic evidence, photos, and run candidate matching."
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
