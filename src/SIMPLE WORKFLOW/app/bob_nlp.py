import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.model import get_clip_model
from app.database import get_db

# Common conversational stop words / query prefixes in NLP search
STOP_PREFIXES = [
    r"^(?:find|search|show|get|display|list|locate|look for|any|who has|who is|is there|bodies with|body with|victim with|person with)\b",
    r"^(?:please\s+)",
    r"\b(?:bodies|body|victims|victim|persons|person|corpse|remains)\b"
]

GENDER_PATTERNS = {
    "Male": [r"\bmale\b", r"\bman\b", r"\bmen\b", r"\bboy\b", r"\bgentleman\b"],
    "Female": [r"\bfemale\b", r"\bwoman\b", r"\bwomen\b", r"\bgirl\b", r"\blady\b"]
}

COMMON_STOP_WORDS = {
    "find", "search", "show", "me", "a", "an", "the", "in", "at", "with", "wearing", 
    "who", "was", "has", "is", "there", "body", "bodies", "person", "persons", 
    "victim", "victims", "details", "for", "and", "or", "of", "to", "on", "from",
    "some", "any", "all", "about", "what", "which", "where", "have", "had", "can",
    "please", "look", "locate", "corpse", "remains", "record", "records"
}

CONCEPT_DICTIONARY = {
    "clothing": [
        "shirt", "t-shirt", "top", "kurta", "jeans", "denim", "trousers", "pants", 
        "jacket", "coat", "hoodie", "sweater", "saree", "dress", "shorts", "fabric", "cloth",
        "polo", "moncler", "plaid", "checkered", "cotton", "formal", "suit"
    ],
    "colors": [
        "white", "black", "blue", "navy", "red", "maroon", "green", "yellow", 
        "gray", "grey", "brown", "beige", "khaki", "orange", "purple", "dark", "light",
        "gold", "silver"
    ],
    "accessories": [
        "watch", "wristwatch", "ring", "kalawa", "thread", "kada", "bangle", 
        "chain", "necklace", "earring", "belt", "shoes", "footwear", "jewelry", "jewellery",
        "bracelet", "glasses", "spectacles", "sunglasses", "eyeglasses", "strap", "octagonal"
    ],
    "marks": [
        "scar", "incision", "surgery", "surgical", "tattoo", "mole", "birthmark", 
        "stubble", "beard", "hair", "bald", "trauma", "mark", "curly", "wavy", "straight"
    ]
}


class BobNLPEngine:
    _instance = None

    def __init__(self):
        self.clip = get_clip_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def parse_nlp_query(self, query: str, known_locations: List[str]) -> Dict[str, Any]:
        """
        Parses conversational natural language queries into structured intent,
        extracted entities (gender, location, concepts), and cleaned semantic text.
        """
        raw_q = query.strip()
        lower_q = raw_q.lower()

        # 1. Inferred Gender
        inferred_gender = None
        for g_name, patterns in GENDER_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower_q):
                    inferred_gender = g_name
                    break
            if inferred_gender:
                break

        # 2. Inferred Locations from registered bodies
        matched_locations = []
        for loc in known_locations:
            if not loc or loc.lower() == "unspecified location":
                continue
            loc_lower = loc.lower()
            if loc_lower in lower_q:
                matched_locations.append(loc)
            else:
                tokens = [t for t in re.split(r"[\s,\-/]+", loc_lower) if len(t) >= 3]
                if any(re.search(rf"\b{re.escape(t)}\b", lower_q) for t in tokens):
                    matched_locations.append(loc)

        matched_locations = list(dict.fromkeys(matched_locations))

        # 3. Extracted Concepts from dictionary + arbitrary query terms
        extracted_concepts = {
            "clothing": [],
            "colors": [],
            "accessories": [],
            "marks": [],
            "other_traits": []
        }
        for cat, words in CONCEPT_DICTIONARY.items():
            for w in words:
                if re.search(rf"\b{re.escape(w)}\b", lower_q):
                    extracted_concepts[cat].append(w)

        # Extract other content words (e.g. brand names, unique identifiers)
        loc_words = set()
        for loc in matched_locations:
            loc_words.update(re.findall(r"\b[a-zA-Z]{3,}\b", loc.lower()))
        gender_words = {"male", "female", "man", "woman", "boy", "girl", "men", "women"}
        all_dict_words = set()
        for words in CONCEPT_DICTIONARY.values():
            all_dict_words.update(words)

        all_query_words = re.findall(r"\b[a-zA-Z]{3,}\b", lower_q)
        for w in all_query_words:
            if w not in COMMON_STOP_WORDS and w not in loc_words and w not in gender_words:
                if w not in all_dict_words and w not in extracted_concepts["other_traits"]:
                    extracted_concepts["other_traits"].append(w)

        # 4. Clean semantic query (strip conversational filler words)
        clean_text = lower_q
        for sp in STOP_PREFIXES:
            clean_text = re.sub(sp, " ", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            clean_text = lower_q

        # 5. Formulate natural intent explanation
        intent_parts = []
        if inferred_gender:
            intent_parts.append(f"Gender: {inferred_gender}")
        if matched_locations:
            intent_parts.append(f"Location: {', '.join(matched_locations)}")
        all_concepts = []
        for c_list in extracted_concepts.values():
            all_concepts.extend(c_list)
        all_concepts = list(dict.fromkeys(all_concepts))
        if all_concepts:
            intent_parts.append(f"Traits: {', '.join(all_concepts)}")

        intent_summary = " • ".join(intent_parts) if intent_parts else f"Semantic Search for: '{raw_q}'"

        return {
            "raw_query": raw_q,
            "cleaned_query": clean_text,
            "inferred_gender": inferred_gender,
            "matched_locations": matched_locations,
            "extracted_concepts": extracted_concepts,
            "all_concepts": all_concepts,
            "intent_summary": intent_summary
        }

    def search(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        """
        Executes Bob NLP search across all registered bodies with strict
        relevance filtering (shows ONLY relevant bodies) and calibrated accuracy scores.
        """
        db = get_db()
        all_bodies = db.get_all_bodies()
        if not all_bodies:
            return {
                "query": query,
                "parsed_intent": {"intent_summary": "No bodies in registry"},
                "total_results": 0,
                "results": []
            }

        known_locations = [b.get("location", "") for b in all_bodies if b.get("location")]
        parsed = self.parse_nlp_query(query, known_locations)

        # Encode query semantically using CLIP
        search_prompt = parsed["cleaned_query"] if len(parsed["cleaned_query"]) >= 3 else query
        query_vector = np.array(self.clip.encode_text(f"a forensic recovery of {search_prompt}"))

        scored_results = []
        has_location_filter = bool(parsed["matched_locations"])
        has_gender_filter = bool(parsed["inferred_gender"])
        all_traits = parsed["all_concepts"]
        has_trait_filter = bool(all_traits)

        for body in all_bodies:
            body_id = body.get("id")
            body_loc = str(body.get("location", ""))
            body_gender = str(body.get("gender", ""))
            body_details = str(body.get("details", ""))
            ef = body.get("extracted_features") or {}

            # Construct comprehensive forensic text representation
            body_context_parts = [
                f"location {body_loc}",
                f"gender {body_gender}",
                body_details
            ]
            if isinstance(ef, dict):
                if ef.get("summary"):
                    body_context_parts.append(ef["summary"])
                for c in ef.get("detected_clothing", []):
                    if isinstance(c, dict):
                        body_context_parts.append(f"{c.get('name', '')} {c.get('details', '')}")
                    else:
                        body_context_parts.append(str(c))
                for a in ef.get("detected_accessories", []):
                    if isinstance(a, dict):
                        body_context_parts.append(f"{a.get('name', '')} {a.get('details', '')}")
                    else:
                        body_context_parts.append(str(a))
                for m in ef.get("detected_marks", []):
                    if isinstance(m, dict):
                        body_context_parts.append(f"{m.get('name', '')} {m.get('details', '')}")
                    else:
                        body_context_parts.append(str(m))
                for col in ef.get("detected_colors", []):
                    if isinstance(col, dict):
                        body_context_parts.append(col.get("name", ""))
                    else:
                        body_context_parts.append(str(col))

            body_full_text = " | ".join(body_context_parts)
            searchable_lower = body_full_text.lower()

            # -------------------------------------------------------------
            # 1. HARD RELEVANCE PRUNING (Show only relevant bodies)
            # -------------------------------------------------------------
            # Location Constraint: If location explicitly specified, must match
            if has_location_filter:
                loc_match = any(loc.lower() in body_loc.lower() or body_loc.lower() in loc.lower() for loc in parsed["matched_locations"])
                if not loc_match:
                    continue

            # Gender Constraint: If gender explicitly specified, filter conflicting genders
            if has_gender_filter:
                g_req = parsed["inferred_gender"].lower()
                b_gen = body_gender.lower()
                if g_req == "male" and "female" in b_gen:
                    continue
                if g_req == "female" and ("male" in b_gen and "female" not in b_gen):
                    continue

            # Check keyword / trait matches
            matched_traits = []
            for trait in all_traits:
                if re.search(rf"\b{re.escape(trait)}\b", searchable_lower):
                    matched_traits.append(trait)

            # If user specified specific traits, but this body has ZERO matched traits,
            # this body is not relevant to the query!
            if has_trait_filter:
                if len(matched_traits) == 0:
                    continue
                # If query specified 3 or more traits, require at least 40% match ratio
                # to eliminate false positive matches from incidental single words
                if len(all_traits) >= 3 and (len(matched_traits) / len(all_traits)) < 0.40:
                    continue

            # -------------------------------------------------------------
            # 2. ACCURACY SCORE CALCULATION (0 - 100%)
            # -------------------------------------------------------------
            # Base semantic similarity
            body_vector = np.array(self.clip.encode_text(body_full_text[:400]))
            sim = float(query_vector @ body_vector)
            sem_pts = max(0.0, min(1.0, (sim - 0.18) / 0.35)) * 35.0

            accuracy_score = sem_pts
            rationale_points = []

            if has_location_filter:
                accuracy_score += 25.0
                rationale_points.append(f"Location matched '{body_loc}'")

            if has_gender_filter and parsed["inferred_gender"].lower() in body_gender.lower():
                accuracy_score += 15.0
                rationale_points.append(f"Gender matched ({parsed['inferred_gender']})")

            if matched_traits:
                trait_ratio = len(matched_traits) / max(1, len(all_traits))
                trait_pts = 15.0 + (trait_ratio * 35.0)
                accuracy_score += trait_pts
                rationale_points.append(f"Matched traits: {', '.join(matched_traits[:5])}")

            final_accuracy = round(min(100.0, max(50.0, accuracy_score)), 1)

            if not rationale_points:
                rationale_points.append(f"Semantic similarity: {round(sem_pts * 3.3, 1)}%")

            nlp_rationale = "; ".join(rationale_points) + "."

            # Minimum relevance threshold: 55% accuracy
            if final_accuracy >= 55.0:
                scored_results.append({
                    "body": body,
                    "nlp_score": final_accuracy,
                    "accuracy_score": final_accuracy,
                    "semantic_similarity": round(sem_pts * 3.3, 1),
                    "matched_entities": matched_traits,
                    "nlp_rationale": nlp_rationale
                })

        # Sort highest accuracy score first
        scored_results.sort(key=lambda x: x["nlp_score"], reverse=True)

        # Dynamic Relevance Pruning:
        # If strong matches exist (>= 75%), filter out weak marginal matches to only return truly relevant bodies
        if scored_results:
            top_score = scored_results[0]["nlp_score"]
            if top_score >= 75.0:
                scored_results = [r for r in scored_results if r["nlp_score"] >= max(68.0, top_score - 15.0)]

        top_results = scored_results[:top_k]

        return {
            "query": query,
            "parsed_intent": parsed,
            "total_matches": len(top_results),
            "results": top_results
        }


def get_bob_nlp_engine() -> BobNLPEngine:
    return BobNLPEngine.get_instance()
