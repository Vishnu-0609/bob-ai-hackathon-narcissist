from typing import List, Optional
from datetime import datetime, timezone
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
    Query,
    Response,
    Security,
)
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user_payload,
    RequireRoles,
    UserRole,
    decode_access_token,
    security_scheme,
    HTTPAuthorizationCredentials,
)
from app.models.entities import ImageEvidence, AMCase, PMCase
from app.schemas import (
    ImageUploadResponse,
    ImageAnalyzeResponse,
    ImageReviewRequest,
    ImageEvidenceResponse,
)
from app.services.vision import (
    GeminiVisionService,
    ImageStorageService,
    ImageValidationError,
    GeminiVisionError,
    GeminiRateLimitError,
)

router = APIRouter(prefix="/images", tags=["Multimodal Image Evidence (Gemini)"])


@router.post("/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    incident_id: str = Form(...),
    am_id: Optional[str] = Form(None),
    pm_id: Optional[str] = Form(None),
    image_type: str = Form("OTHER"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        RequireRoles([
            UserRole.ADMIN,
            UserRole.COORDINATOR,
            UserRole.AM_TEAM,
            UserRole.PM_TEAM,
            UserRole.FORENSIC_REVIEWER,
            UserRole.FIELD_OPERATOR,
        ])
    ),
):
    """
    Validates uploaded image MIME, size, SHA-256 and dimensions, saves to private UUID storage,
    and creates an ImageEvidence record.
    """
    try:
        file_bytes = await file.read()
        image_record = GeminiVisionService.upload_and_register_image(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg",
            incident_id=incident_id,
            am_id=am_id,
            pm_id=pm_id,
            image_type=image_type,
            uploaded_by=current_user.get("username", "USER"),
            role=current_user.get("role", "FIELD_OPERATOR"),
        )
        return image_record

    except ImageValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")


@router.post("/batch-upload", response_model=List[ImageUploadResponse], status_code=status.HTTP_201_CREATED)
async def batch_upload_images(
    files: List[UploadFile] = File(...),
    incident_id: str = Form(...),
    am_id: Optional[str] = Form(None),
    pm_id: Optional[str] = Form(None),
    image_type: str = Form("OTHER"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        RequireRoles([
            UserRole.ADMIN,
            UserRole.COORDINATOR,
            UserRole.AM_TEAM,
            UserRole.PM_TEAM,
            UserRole.FORENSIC_REVIEWER,
            UserRole.FIELD_OPERATOR,
        ])
    ),
):
    """
    Validates and registers multiple uploaded image files in parallel.
    """
    records = []
    errors = []
    for file in files:
        try:
            file_bytes = await file.read()
            record = GeminiVisionService.upload_and_register_image(
                db=db,
                file_bytes=file_bytes,
                filename=file.filename or "image.jpg",
                content_type=file.content_type or "image/jpeg",
                incident_id=incident_id,
                am_id=am_id,
                pm_id=pm_id,
                image_type=image_type,
                uploaded_by=current_user.get("username", "USER"),
                role=current_user.get("role", "FIELD_OPERATOR"),
            )
            records.append(record)
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    if not records and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return records


@router.post("/{image_id}/analyze", response_model=ImageAnalyzeResponse)
def analyze_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        RequireRoles([
            UserRole.ADMIN,
            UserRole.COORDINATOR,
            UserRole.AM_TEAM,
            UserRole.PM_TEAM,
            UserRole.FORENSIC_REVIEWER,
            UserRole.FIELD_OPERATOR,
        ])
    ),
):
    """
    Triggers cloud multimodal extraction via Google Gemini 2.5 Flash API.
    Returns structured visual observations and image quality metrics.
    """
    service = GeminiVisionService()
    try:
        result = service.analyze_image(
            db=db,
            image_id=image_id,
            user_id=current_user.get("username", "USER"),
            role=current_user.get("role", "FIELD_OPERATOR"),
        )
        return result
    except GeminiRateLimitError as rle:
        raise HTTPException(status_code=429, detail=f"Gemini Rate Limit: {str(rle)}")
    except GeminiVisionError as gve:
        raise HTTPException(status_code=502, detail=f"Gemini Vision Service Error: {str(gve)}")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis error: {str(e)}")


@router.get("/{image_id}/analysis", response_model=ImageEvidenceResponse)
def get_image_analysis(
    image_id: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Retrieves the complete extraction result, provenance metadata, and review status for an image.
    """
    record = db.query(ImageEvidence).filter(ImageEvidence.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image evidence record not found")
    return record


@router.post("/{image_id}/review", response_model=ImageEvidenceResponse)
def review_image_evidence(
    image_id: str,
    review_req: ImageReviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        RequireRoles([
            UserRole.ADMIN,
            UserRole.COORDINATOR,
            UserRole.AM_TEAM,
            UserRole.PM_TEAM,
            UserRole.FORENSIC_REVIEWER,
            UserRole.FIELD_OPERATOR,
        ])
    ),
):
    """
    Authoritative human review of AI-extracted evidence.
    Approves, modifies, or rejects observations and updates linked AM/PM case records.
    """
    try:
        updated_record = GeminiVisionService.review_evidence(
            db=db,
            image_id=image_id,
            decision=review_req.decision,
            approved_observations=review_req.approved_observations,
            reviewed_by=current_user.get("username", "USER"),
            role=current_user.get("role", "FORENSIC_REVIEWER"),
            review_notes=review_req.notes,
            am_id=review_req.am_id,
            pm_id=review_req.pm_id,
            incident_id=review_req.incident_id,
            auto_create_case=review_req.auto_create_case or False,
            record_type=review_req.record_type,
        )
        return updated_record
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review submission failed: {str(e)}")


@router.get("/{image_id}/file")
def get_image_file(
    image_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
):
    """
    Securely serves the image binary to authenticated clients.
    Supports either standard Bearer Authorization header or ?token= query parameter for browser <img> tags.
    """
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access forensic image evidence",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    record = db.query(ImageEvidence).filter(ImageEvidence.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        image_bytes = ImageStorageService.read_image_bytes(record.storage_path)
        return Response(content=image_bytes, media_type=record.mime_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Image file content unavailable on server")


@router.get("", response_model=List[ImageEvidenceResponse])
def list_images(
    incident_id: Optional[str] = Query(None),
    am_id: Optional[str] = Query(None),
    pm_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
):
    """
    Lists image evidence records filtered by incident, AM case, or PM case.
    """
    query = db.query(ImageEvidence)
    if incident_id:
        query = query.filter(ImageEvidence.incident_id == incident_id)
    if am_id:
        query = query.filter((ImageEvidence.am_id == am_id))
    if pm_id:
        query = query.filter((ImageEvidence.pm_id == pm_id))
    return query.order_by(ImageEvidence.created_at.desc()).all()
