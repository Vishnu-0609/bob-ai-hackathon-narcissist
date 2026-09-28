import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import AuditLog

GENESIS_HASH = "0" * 64


def compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AuditService:
    @staticmethod
    def get_last_event(db: Session) -> Optional[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.event_id.desc()).first()

    @staticmethod
    def log_event(
        db: Session,
        user_id: str,
        role: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
        old_value_hash: Optional[str] = None,
        new_value_hash: Optional[str] = None,
    ) -> AuditLog:
        if details is None:
            details = {}

        # Fetch last event to chain
        last_event = AuditService.get_last_event(db)
        previous_event_hash = last_event.event_hash if last_event else GENESIS_HASH

        # Generate unique event ID based on max existing or count
        event_count = db.query(AuditLog).count() + 1
        event_id = f"AUD-{event_count:06d}"

        now = datetime.now(timezone.utc)
        iso_timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build canonical payload for deterministic hashing
        canonical_dict = {
            "event_id": event_id,
            "user_id": user_id,
            "role": role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "timestamp": iso_timestamp,
        }
        canonical_str = json.dumps(canonical_dict, sort_keys=True, default=str)
        event_hash = compute_sha256(canonical_str + previous_event_hash)

        # Store the record
        log_entry = AuditLog(
            event_id=event_id,
            user_id=user_id,
            role=role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            old_value_hash=old_value_hash,
            new_value_hash=new_value_hash,
            previous_event_hash=previous_event_hash,
            event_hash=event_hash,
            timestamp=now,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def verify_integrity(db: Session) -> Dict[str, Any]:
        start_time = time.perf_counter()
        events = db.query(AuditLog).order_by(AuditLog.event_id.asc()).all()

        if not events:
            return {
                "valid": True,
                "events_checked": 0,
                "broken_at": None,
                "last_event_hash": None,
                "verification_time_ms": 0.0,
            }

        expected_previous_hash = GENESIS_HASH
        for idx, event in enumerate(events):
            # Verify chain linkage
            if event.previous_event_hash != expected_previous_hash:
                return {
                    "valid": False,
                    "events_checked": idx,
                    "broken_at": event.event_id,
                    "error": f"Previous hash mismatch at {event.event_id}",
                    "last_event_hash": event.previous_event_hash,
                    "verification_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                }

            # Recompute canonical hash
            ts_str = event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if event.timestamp else ""
            canonical_dict = {
                "event_id": event.event_id,
                "user_id": event.user_id,
                "role": event.role,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "details": event.details,
                "timestamp": ts_str,
            }
            canonical_str = json.dumps(canonical_dict, sort_keys=True, default=str)
            calculated_hash = compute_sha256(canonical_str + expected_previous_hash)

            if calculated_hash != event.event_hash:
                return {
                    "valid": False,
                    "events_checked": idx,
                    "broken_at": event.event_id,
                    "error": f"Tampered event data at {event.event_id}",
                    "last_event_hash": event.event_hash,
                    "verification_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                }

            expected_previous_hash = event.event_hash

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "valid": True,
            "events_checked": len(events),
            "broken_at": None,
            "last_event_hash": expected_previous_hash,
            "verification_time_ms": elapsed_ms,
        }
