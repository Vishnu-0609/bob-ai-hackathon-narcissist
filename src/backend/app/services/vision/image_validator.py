import os
import re
import io
import hashlib
from typing import Tuple, Dict, Any
from PIL import Image
from app.core.config import settings


class ImageValidationError(Exception):
    """Custom exception raised when an uploaded image fails security or format validation."""
    pass


class ImageValidator:
    ALLOWED_MIME_TYPES = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/jpg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/webp": [".webp"],
    }

    MAGIC_SIGNATURES = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"RIFF": "image/webp",  # WebP has RIFF...WEBP
    }

    MAX_FILE_SIZE_BYTES = settings.MAX_IMAGE_SIZE_BYTES  # 10 MB
    MIN_DIMENSION = 10
    MAX_DIMENSION = 10000

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitizes client original filename against path traversal and dangerous characters.
        """
        if not filename:
            return "unnamed_image.jpg"
        # Strip directory components
        base = os.path.basename(filename)
        # Remove null bytes and non-printable characters
        cleaned = re.sub(r"[^\w\s\.\-]", "", base).strip()
        if not cleaned or cleaned.startswith("."):
            cleaned = "image_" + cleaned
        return cleaned[:200]

    @classmethod
    def calculate_sha256(cls, file_bytes: bytes) -> str:
        """
        Calculates cryptographic SHA-256 digest of image content.
        """
        return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    def validate_image_bytes(
        cls, file_bytes: bytes, filename: str, declared_content_type: str = ""
    ) -> Dict[str, Any]:
        """
        Comprehensive security and integrity validation of image byte payload.
        Returns validated metadata dictionary.
        """
        if not file_bytes:
            raise ImageValidationError("Uploaded image payload is empty (0 bytes).")

        file_size = len(file_bytes)
        if file_size > cls.MAX_FILE_SIZE_BYTES:
            raise ImageValidationError(
                f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {cls.MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
            )

        # Reject executable / script magic headers
        if file_bytes.startswith((b"MZ", b"\x7fELF", b"#!/", b"<?php", b"<script")):
            raise ImageValidationError("Executable or script file format detected and rejected.")

        # Validate MIME type declaration and magic bytes
        normalized_mime = (declared_content_type or "").lower().strip()
        if normalized_mime == "image/jpg":
            normalized_mime = "image/jpeg"

        # Check magic signature
        detected_mime = None
        if file_bytes.startswith(b"\xff\xd8\xff"):
            detected_mime = "image/jpeg"
        elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            detected_mime = "image/png"
        elif file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[:16]:
            detected_mime = "image/webp"

        if not detected_mime:
            # Fallback to declared if valid
            if normalized_mime in ("image/jpeg", "image/png", "image/webp"):
                detected_mime = normalized_mime
            else:
                raise ImageValidationError("Unsupported image format. Allowed formats: JPEG, PNG, WEBP.")

        # Decode image using PIL to ensure it is not corrupt or malformed
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
                img_format = img.format
        except Exception as e:
            raise ImageValidationError(f"Invalid or corrupted image content: {str(e)}")

        # Re-open for dimension inspection (verify closes image)
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                if width < cls.MIN_DIMENSION or height < cls.MIN_DIMENSION:
                    raise ImageValidationError(
                        f"Image dimensions ({width}x{height}) are too small. Minimum is {cls.MIN_DIMENSION}x{cls.MIN_DIMENSION}px."
                    )
                if width > cls.MAX_DIMENSION or height > cls.MAX_DIMENSION:
                    raise ImageValidationError(
                        f"Image dimensions ({width}x{height}) exceed allowable maximum of {cls.MAX_DIMENSION}x{cls.MAX_DIMENSION}px."
                    )
        except ImageValidationError:
            raise
        except Exception as e:
            raise ImageValidationError(f"Unable to read image dimensions: {str(e)}")

        sha256 = cls.calculate_sha256(file_bytes)
        sanitized_name = cls.sanitize_filename(filename)

        return {
            "valid": True,
            "mime_type": detected_mime,
            "file_size": file_size,
            "sha256": sha256,
            "width": width,
            "height": height,
            "format": img_format,
            "sanitized_filename": sanitized_name,
        }
