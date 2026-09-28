from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user_payload
from app.schemas import (
    CopilotChatRequest,
    CopilotChatResponse,
)
from app.services.bob_rationale import BobRationaleService
from app.services.bob_evidence_gap import BobEvidenceGapService
from app.services.bob_copilot import BobCopilotService
from app.services.bob_client import bob_client

router = APIRouter(prefix="/bob", tags=["IBM Bob AI Services"])


@router.get("/status")
def get_bob_status(payload: dict = Depends(get_current_user_payload)):
    """
    Returns the operational status of IBM Bob integration.
    """
    has_key = bool(settings.BOB_API_KEY and len(settings.BOB_API_KEY.strip()) > 5)
    return {
        "configured": has_key,
        "endpoint": settings.BOB_API_URL,
        "fallback_active": not has_key,
        "mode": "CONNECTED_IBM_BOB" if has_key else "LOCAL_HEURISTIC_BACKUP",
        "message": (
            "IBM Bob AI service is active and handling requests."
            if has_key
            else "IBM Bob API key not configured. Local deterministic fallback engine is active and fully functional."
        ),
    }


@router.post("/rationale")
async def generate_rationale(
    candidate_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Generates plain-language forensic rationale for a candidate match package.
    """
    rationale = await BobRationaleService.generate_rationale(candidate_data, db=db)
    return {"rationale": rationale}


@router.post("/evidence-gaps")
async def analyze_evidence_gaps(
    candidate_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Identifies missing forensic evidence and suggests verification steps.
    """
    gaps = await BobEvidenceGapService.analyze_evidence_gaps(candidate_data, db=db)
    return gaps


@router.post("/chat", response_model=CopilotChatResponse)
async def chat_copilot(
    req: CopilotChatRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    DVI Coordinator Copilot chat with strictly controlled tool execution.
    """
    res = await BobCopilotService.process_copilot_query(
        query=req.query,
        incident_id=req.incident_id,
        context_pm_id=req.context_pm_id,
        context_am_id=req.context_am_id,
        db=db,
    )
    return CopilotChatResponse(
        response=res["response"],
        tools_used=res.get("tools_used", []),
        suggested_actions=res.get("suggested_actions", []),
        intent=res.get("intent"),
    )
