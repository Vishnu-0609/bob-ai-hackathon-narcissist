import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.models.entities import ImageEvidence, AMCase, PMCase
from app.services.audit_service import AuditService
from app.services.vision.image_validator import ImageValidator, ImageValidationError
from app.services.vision.image_storage import ImageStorageService
from app.services.vision.gemini_client import GeminiClient, GeminiVisionError, GeminiRateLimitError
from app.services.vision.extraction_schema import ImageExtraction

logger = logging.getLogger("dvi.vision.service")


class GeminiVisionService:
    """
    Central orchestration service for multimodal cloud-based image evidence extraction,
    validation, storage, human review, and case provenance tracking.
    """

    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()

    @classmethod
    def upload_and_register_image(
        cls,
        db: Session,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        incident_id: str,
        am_id: Optional[str] = None,
        pm_id: Optional[str] = None,
        image_type: str = "OTHER",
        uploaded_by: str = "SYSTEM",
        role: str = "FIELD_OPERATOR",
    ) -> ImageEvidence:
        """
        Validates uploaded image, saves with UUID in secure private storage,
        and creates an authoritative ImageEvidence database record.
        """
        # Validate security, dimensions, format, SHA-256
        validation_info = ImageValidator.validate_image_bytes(
            file_bytes=file_bytes,
            filename=filename,
            declared_content_type=content_type,
        )

        image_id = str(uuid.uuid4())
        entity_type = "AM" if am_id else ("PM" if pm_id else "OTHER")

        # Determine extension from detected MIME
        ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        ext = ext_map.get(validation_info["mime_type"], ".jpg")

        # Save to private storage
        storage_rel_path = ImageStorageService.save_image(
            file_bytes=file_bytes,
            image_id=image_id,
            entity_type=entity_type,
            extension=ext,
        )

        image_record = ImageEvidence(
            id=image_id,
            incident_id=incident_id,
            am_id=am_id,
            pm_id=pm_id,
            storage_path=storage_rel_path,
            original_filename=validation_info["sanitized_filename"],
            mime_type=validation_info["mime_type"],
            file_size=validation_info["file_size"],
            sha256=validation_info["sha256"],
            image_type=image_type.upper(),
            gemini_model=settings.GEMINI_MODEL,
            analysis_status="PENDING",
            extraction_json={},
            human_review_status="PENDING_REVIEW",
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
        )

        db.add(image_record)
        db.commit()
        db.refresh(image_record)

        AuditService.log_event(
            db=db,
            user_id=uploaded_by,
            role=role,
            action="IMAGE_UPLOADED",
            entity_type="IMAGE_EVIDENCE",
            entity_id=image_record.id,
            details={
                "sha256": image_record.sha256,
                "file_size": image_record.file_size,
                "mime_type": image_record.mime_type,
                "image_type": image_record.image_type,
                "am_id": am_id,
                "pm_id": pm_id,
            },
        )

        return image_record

    def analyze_image(
        self,
        db: Session,
        image_id: str,
        user_id: str = "SYSTEM",
        role: str = "FIELD_OPERATOR",
    ) -> Dict[str, Any]:
        """
        Performs cloud Gemini 2.5 Flash multimodal analysis on a registered image.
        Updates analysis status and structured extraction JSON in the database.
        """
        image_record = db.query(ImageEvidence).filter(ImageEvidence.id == image_id).first()
        if not image_record:
            raise ValueError(f"Image evidence record {image_id} not found.")

        # Read binary payload from secure storage
        try:
            image_bytes = ImageStorageService.read_image_bytes(image_record.storage_path)
        except Exception as e:
            logger.error("Failed to read image from storage: %s", e)
            image_record.analysis_status = "FAILED"
            db.commit()
            raise GeminiVisionError(f"Image file could not be read from storage: {str(e)}")

        record_type = "AM" if image_record.am_id else ("PM" if image_record.pm_id else "OTHER")

        image_record.analysis_status = "ANALYZING"
        db.commit()

        try:
            extraction_result = self.client.extract_image_evidence(
                image_bytes=image_bytes,
                mime_type=image_record.mime_type,
                record_type=record_type,
                image_type=image_record.image_type,
            )

            # Record model provenance on extraction payload
            extraction_result["provenance"] = {
                "source_type": "IMAGE",
                "source_image_id": image_record.id,
                "sha256": image_record.sha256,
                "model": "Gemini",
                "model_version": self.client.model,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "human_review_status": image_record.human_review_status,
            }

            image_record.extraction_json = extraction_result
            image_record.gemini_model = self.client.model
            image_record.analysis_status = "COMPLETED"
            image_record.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(image_record)

            AuditService.log_event(
                db=db,
                user_id=user_id,
                role=role,
                action="IMAGE_ANALYZED",
                entity_type="IMAGE_EVIDENCE",
                entity_id=image_record.id,
                details={
                    "model": self.client.model,
                    "record_type": record_type,
                    "observations_summary": extraction_result.get("summary"),
                },
            )

            return {
                "image_id": image_record.id,
                "analysis_status": "COMPLETED",
                "model": self.client.model,
                "extracted_data": extraction_result,
                "human_review_status": image_record.human_review_status,
            }

        except Exception as err:
            logger.error("Gemini image analysis failed for image %s: %s", image_id, err)
            image_record.analysis_status = "FAILED"
            image_record.updated_at = datetime.now(timezone.utc)
            db.commit()

            AuditService.log_event(
                db=db,
                user_id=user_id,
                role=role,
                action="IMAGE_ANALYSIS_FAILED",
                entity_type="IMAGE_EVIDENCE",
                entity_id=image_record.id,
                details={"error": str(err)},
            )
            raise

    @classmethod
    def review_evidence(
        cls,
        db: Session,
        image_id: str,
        decision: str,  # APPROVED, MODIFIED_AND_APPROVED, REJECTED
        approved_observations: Dict[str, Any],
        reviewed_by: str,
        role: str = "FORENSIC_REVIEWER",
        review_notes: Optional[str] = None,
        am_id: Optional[str] = None,
        pm_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        auto_create_case: bool = False,
        record_type: Optional[str] = None,
    ) -> ImageEvidence:
        """
        Human reviewer reviews, edits, and verifies Gemini-extracted evidence.
        Synchronizes verified evidence into the linked AM/PM case for matching engine evaluation and DB persistence.
        """
        image_record = db.query(ImageEvidence).filter(ImageEvidence.id == image_id).first()
        if not image_record:
            raise ValueError(f"Image evidence record {image_id} not found.")

        valid_decisions = ("APPROVED", "MODIFIED_AND_APPROVED", "REJECTED")
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision: {decision}. Must be one of {valid_decisions}")

        # Update case link if provided
        if am_id:
            image_record.am_id = am_id
        if pm_id:
            image_record.pm_id = pm_id
        if incident_id and not image_record.incident_id:
            image_record.incident_id = incident_id

        current_extraction = image_record.extraction_json or {}
        current_extraction["observations"] = approved_observations.get("observations", approved_observations)
        if "summary" in approved_observations:
            current_extraction["summary"] = approved_observations["summary"]

        current_extraction["review"] = {
            "decision": decision,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "notes": review_notes,
        }

        image_record.extraction_json = current_extraction
        image_record.human_review_status = decision
        image_record.reviewed_by = reviewed_by
        image_record.reviewed_at = datetime.now(timezone.utc)
        image_record.updated_at = datetime.now(timezone.utc)

        # If approved or modified-and-approved, merge verified evidence into case record
        if decision in ("APPROVED", "MODIFIED_AND_APPROVED"):
            # Auto-create case if requested and not linked to any case yet
            if not image_record.am_id and not image_record.pm_id and (auto_create_case or record_type):
                rec_type = (record_type or "AM").upper()
                inc_id = image_record.incident_id or incident_id
                if not inc_id:
                    from app.models.entities import Incident
                    inc = db.query(Incident).first()
                    inc_id = inc.id if inc else "INC-001"
                    image_record.incident_id = inc_id

                if rec_type == "AM":
                    new_case_num = f"AM-{db.query(AMCase).count() + 1:03d}"
                    new_am = AMCase(
                        incident_id=inc_id,
                        case_number=new_case_num,
                        name=f"Subject ({image_record.image_type or 'Photo'})",
                        clothing=[],
                        jewellery=[],
                        tattoos=[],
                        scars=[],
                        birthmarks=[],
                        provenance_details={},
                        version=1,
                        created_by=reviewed_by,
                    )
                    db.add(new_am)
                    db.flush()
                    image_record.am_id = new_am.id
                elif rec_type == "PM":
                    new_body_num = f"PM-{db.query(PMCase).count() + 1:03d}"
                    new_pm = PMCase(
                        incident_id=inc_id,
                        body_number=new_body_num,
                        clothing=[],
                        jewellery=[],
                        tattoos=[],
                        scars=[],
                        birthmarks=[],
                        provenance_details={},
                        version=1,
                        created_by=reviewed_by,
                    )
                    db.add(new_pm)
                    db.flush()
                    image_record.pm_id = new_pm.id

            cls._sync_evidence_to_case(db, image_record, current_extraction, reviewed_by)

        db.commit()
        db.refresh(image_record)

        AuditService.log_event(
            db=db,
            user_id=reviewed_by,
            role=role,
            action="IMAGE_EVIDENCE_REVIEWED",
            entity_type="IMAGE_EVIDENCE",
            entity_id=image_record.id,
            details={
                "decision": decision,
                "reviewed_by": reviewed_by,
                "am_id": image_record.am_id,
                "pm_id": image_record.pm_id,
            },
        )

        return image_record

    @classmethod
    def _sync_evidence_to_case(
        cls,
        db: Session,
        image_record: ImageEvidence,
        extraction_data: Dict[str, Any],
        reviewer: str,
    ):
        """
        Propagates human-verified visual observations (clothing, jewellery, tattoos, scars)
        into the parent AMCase or PMCase structured record with full provenance tracking.
        """
        obs = extraction_data.get("observations", {})
        clothing_list = obs.get("clothing", [])
        jewellery_list = obs.get("jewellery", [])
        tattoo_list = obs.get("tattoos", [])
        scar_list = obs.get("scars_or_marks", [])
        phys_list = obs.get("physical_characteristics", [])
        visible_text = obs.get("visible_text", [])

        provenance_tag = {
            "source_type": "IMAGE",
            "source_image_id": image_record.id,
            "model": "Gemini",
            "model_version": image_record.gemini_model,
            "extracted_at": image_record.created_at.isoformat() if image_record.created_at else datetime.now(timezone.utc).isoformat(),
            "review_status": "HUMAN_VERIFIED",
            "reviewed_by": reviewer,
        }

        # Helper to extract clothing strings
        parsed_clothing = []
        for c in clothing_list:
            if isinstance(c, str):
                desc = c.strip()
            elif isinstance(c, dict):
                desc = (c.get("description") or f"{c.get('color', '')} {c.get('item_type', '')}").strip()
            else:
                desc = str(c).strip()
            if desc and desc not in parsed_clothing:
                parsed_clothing.append(desc)

        # Helper to extract jewellery strings
        parsed_jewellery = []
        for j in jewellery_list:
            if isinstance(j, str):
                desc = j.strip()
            elif isinstance(j, dict):
                desc = (j.get("description") or f"{j.get('material_or_color', '')} {j.get('item_type', '')}").strip()
                loc = j.get("location")
                if loc and loc not in desc:
                    desc = f"{desc} ({loc})"
            else:
                desc = str(j).strip()
            if desc and desc not in parsed_jewellery:
                parsed_jewellery.append(desc)

        # Helper to extract tattoo entries
        parsed_tattoos = []
        for t in tattoo_list:
            if isinstance(t, str):
                t_entry = {
                    "location": "unspecified",
                    "description": t.strip(),
                    "design_motifs": [],
                    "colors": [],
                    "provenance": provenance_tag,
                }
            elif isinstance(t, dict):
                t_entry = {
                    "location": t.get("location") or "unspecified",
                    "description": t.get("description") or "tattoo",
                    "design_motifs": t.get("design_motifs") or [],
                    "colors": t.get("colors") or [],
                    "provenance": provenance_tag,
                }
            else:
                continue
            parsed_tattoos.append(t_entry)

        # Helper to extract scar / mark entries
        parsed_scars = []
        parsed_birthmarks = []
        for s in scar_list:
            if isinstance(s, str):
                entry = {
                    "location": "unspecified",
                    "description": s.strip(),
                    "provenance": provenance_tag,
                }
                parsed_scars.append(entry)
            elif isinstance(s, dict):
                mtype = (s.get("mark_type") or "scar").lower()
                entry = {
                    "location": s.get("location") or "unspecified",
                    "description": s.get("description") or mtype,
                    "provenance": provenance_tag,
                }
                if mtype in ("birthmark", "mole"):
                    parsed_birthmarks.append(entry)
                else:
                    parsed_scars.append(entry)

        # Parse physical characteristics
        added_phys = []
        for p in phys_list:
            if isinstance(p, dict):
                val = p.get("value")
                if val and val != "UNKNOWN":
                    attr_label = (p.get("attribute") or "").replace("_", " ")
                    added_phys.append(f"{attr_label}: {val}")
            elif isinstance(p, str) and p.strip():
                added_phys.append(p.strip())

        if image_record.am_id:
            am = db.query(AMCase).filter((AMCase.id == image_record.am_id) | (AMCase.case_number == image_record.am_id)).first()
            if am:
                existing_clothing = list(am.clothing or [])
                for item in parsed_clothing:
                    if item not in existing_clothing:
                        existing_clothing.append(item)

                existing_jewellery = list(am.jewellery or [])
                for item in parsed_jewellery:
                    if item not in existing_jewellery:
                        existing_jewellery.append(item)

                existing_tattoos = list(am.tattoos or [])
                for t_new in parsed_tattoos:
                    if not any(
                        (t.get("description") == t_new["description"] and t.get("location") == t_new["location"])
                        if isinstance(t, dict) else str(t) == t_new["description"]
                        for t in existing_tattoos
                    ):
                        existing_tattoos.append(t_new)

                existing_scars = list(am.scars or [])
                for s_new in parsed_scars:
                    if not any(
                        (s.get("description") == s_new["description"] and s.get("location") == s_new["location"])
                        if isinstance(s, dict) else str(s) == s_new["description"]
                        for s in existing_scars
                    ):
                        existing_scars.append(s_new)

                existing_birthmarks = list(am.birthmarks or [])
                for b_new in parsed_birthmarks:
                    if not any(
                        (b.get("description") == b_new["description"] and b.get("location") == b_new["location"])
                        if isinstance(b, dict) else str(b) == b_new["description"]
                        for b in existing_birthmarks
                    ):
                        existing_birthmarks.append(b_new)

                if added_phys:
                    phys_note = f"[Photo Evidence]: {', '.join(added_phys)}"
                    if not am.physical_description:
                        am.physical_description = phys_note
                    elif phys_note not in am.physical_description:
                        am.physical_description = f"{am.physical_description} | {phys_note}"

                prov_dict = dict(am.provenance_details or {})
                if visible_text:
                    prov_dict["extracted_visual_text"] = visible_text
                prov_dict["last_image_sync"] = {
                    "image_id": image_record.id,
                    "model": image_record.gemini_model,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                am.provenance_details = prov_dict

                am.clothing = existing_clothing
                am.jewellery = existing_jewellery
                am.tattoos = existing_tattoos
                am.scars = existing_scars
                am.birthmarks = existing_birthmarks
                am.version = (am.version or 0) + 1
                am.updated_at = datetime.now(timezone.utc)

                flag_modified(am, "clothing")
                flag_modified(am, "jewellery")
                flag_modified(am, "tattoos")
                flag_modified(am, "scars")
                flag_modified(am, "birthmarks")
                flag_modified(am, "provenance_details")
                db.add(am)

        elif image_record.pm_id:
            pm = db.query(PMCase).filter((PMCase.id == image_record.pm_id) | (PMCase.body_number == image_record.pm_id)).first()
            if pm:
                existing_clothing = list(pm.clothing or [])
                for item in parsed_clothing:
                    if item not in existing_clothing:
                        existing_clothing.append(item)

                existing_jewellery = list(pm.jewellery or [])
                for item in parsed_jewellery:
                    if item not in existing_jewellery:
                        existing_jewellery.append(item)

                existing_tattoos = list(pm.tattoos or [])
                for t_new in parsed_tattoos:
                    if not any(
                        (t.get("description") == t_new["description"] and t.get("location") == t_new["location"])
                        if isinstance(t, dict) else str(t) == t_new["description"]
                        for t in existing_tattoos
                    ):
                        existing_tattoos.append(t_new)

                existing_scars = list(pm.scars or [])
                for s_new in parsed_scars:
                    if not any(
                        (s.get("description") == s_new["description"] and s.get("location") == s_new["location"])
                        if isinstance(s, dict) else str(s) == s_new["description"]
                        for s in existing_scars
                    ):
                        existing_scars.append(s_new)

                existing_birthmarks = list(pm.birthmarks or [])
                for b_new in parsed_birthmarks:
                    if not any(
                        (b.get("description") == b_new["description"] and b.get("location") == b_new["location"])
                        if isinstance(b, dict) else str(b) == b_new["description"]
                        for b in existing_birthmarks
                    ):
                        existing_birthmarks.append(b_new)

                if added_phys:
                    phys_note = f"[Photo Evidence]: {', '.join(added_phys)}"
                    if not pm.physical_description:
                        pm.physical_description = phys_note
                    elif phys_note not in pm.physical_description:
                        pm.physical_description = f"{pm.physical_description} | {phys_note}"

                prov_dict = dict(pm.provenance_details or {})
                if visible_text:
                    prov_dict["extracted_visual_text"] = visible_text
                prov_dict["last_image_sync"] = {
                    "image_id": image_record.id,
                    "model": image_record.gemini_model,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                pm.provenance_details = prov_dict

                pm.clothing = existing_clothing
                pm.jewellery = existing_jewellery
                pm.tattoos = existing_tattoos
                pm.scars = existing_scars
                pm.birthmarks = existing_birthmarks
                pm.version = (pm.version or 0) + 1
                pm.updated_at = datetime.now(timezone.utc)

                flag_modified(pm, "clothing")
                flag_modified(pm, "jewellery")
                flag_modified(pm, "tattoos")
                flag_modified(pm, "scars")
                flag_modified(pm, "birthmarks")
                flag_modified(pm, "provenance_details")
                db.add(pm)
