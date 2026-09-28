import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import BobInteraction

logger = logging.getLogger("dvi.bob_client")


class BobClient:
    """
    Client interface for IBM Bob / watsonx Orchestrate AI capabilities.
    All IBM credentials stay strictly on the backend.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.BOB_API_KEY
        self.base_url = (base_url or settings.BOB_API_URL).rstrip("/")
        self.timeout = settings.BOB_TIMEOUT_SECONDS

    def _hash_schema(self, data: Any) -> str:
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        except Exception:
            return ""

    def log_interaction(
        self,
        db: Optional[Session],
        agent_name: str,
        request_id: str,
        input_data: Any,
        output_data: Any,
        latency_ms: float,
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        if not db:
            return
        try:
            interaction = BobInteraction(
                agent_name=agent_name,
                request_id=request_id,
                input_schema_hash=self._hash_schema(input_data),
                output_schema_hash=self._hash_schema(output_data) if success else None,
                timestamp=datetime.now(timezone.utc),
                success=success,
                latency_ms=round(latency_ms, 2),
                error_type=error_type,
            )
            db.add(interaction)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log Bob interaction: {e}")

    async def call_bob_api(
        self,
        agent_name: str,
        payload: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        request_id = f"BOB-REQ-{uuid.uuid4().hex[:10].upper()}"
        start_time = time.perf_counter()

        if not self.api_key:
            # Fallback when API key is not configured
            latency = (time.perf_counter() - start_time) * 1000
            self.log_interaction(
                db=db,
                agent_name=agent_name,
                request_id=request_id,
                input_data=payload,
                output_data={"status": "fallback_local_engine"},
                latency_ms=latency,
                success=True,
                error_type="API_KEY_NOT_CONFIGURED",
            )
            return {
                "success": False,
                "reason": "BOB_API_KEY_MISSING",
                "message": "IBM Bob API key not configured. Using deterministic fallback engine.",
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }

        url = f"{self.base_url}/agents/{agent_name.lower()}/execute"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                latency = (time.perf_counter() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    self.log_interaction(
                        db=db,
                        agent_name=agent_name,
                        request_id=request_id,
                        input_data=payload,
                        output_data=data,
                        latency_ms=latency,
                        success=True,
                    )
                    return {"success": True, "data": data}
                else:
                    error_type = f"HTTP_{response.status_code}"
                    self.log_interaction(
                        db=db,
                        agent_name=agent_name,
                        request_id=request_id,
                        input_data=payload,
                        output_data=None,
                        latency_ms=latency,
                        success=False,
                        error_type=error_type,
                    )
                    return {
                        "success": False,
                        "reason": error_type,
                        "message": f"IBM Bob returned status code {response.status_code}",
                    }
        except httpx.TimeoutException:
            latency = (time.perf_counter() - start_time) * 1000
            self.log_interaction(
                db=db,
                agent_name=agent_name,
                request_id=request_id,
                input_data=payload,
                output_data=None,
                latency_ms=latency,
                success=False,
                error_type="TIMEOUT",
            )
            return {"success": False, "reason": "TIMEOUT", "message": "IBM Bob API request timed out."}
        except Exception as ex:
            latency = (time.perf_counter() - start_time) * 1000
            self.log_interaction(
                db=db,
                agent_name=agent_name,
                request_id=request_id,
                input_data=payload,
                output_data=None,
                latency_ms=latency,
                success=False,
                error_type=type(ex).__name__,
            )
            return {"success": False, "reason": "CONNECTION_ERROR", "message": str(ex)}


bob_client = BobClient()
