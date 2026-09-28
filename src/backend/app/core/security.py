import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Union
import jwt
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Optional bcrypt import with robust fallback
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

security_scheme = HTTPBearer(auto_error=False)


class UserRole:
    ADMIN = "ADMIN"
    COORDINATOR = "COORDINATOR"
    DVI_COORDINATOR = "DVI_COORDINATOR"
    FORENSIC_REVIEWER = "FORENSIC_REVIEWER"
    FIELD_OPERATOR = "FIELD_OPERATOR"
    AM_TEAM = "AM_TEAM"
    PM_TEAM = "PM_TEAM"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"

    @classmethod
    def all_roles(cls) -> List[str]:
        return [
            cls.ADMIN,
            cls.COORDINATOR,
            cls.DVI_COORDINATOR,
            cls.FORENSIC_REVIEWER,
            cls.FIELD_OPERATOR,
            cls.AM_TEAM,
            cls.PM_TEAM,
            cls.AUDITOR,
            cls.VIEWER,
        ]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if HAS_BCRYPT and hashed_password.startswith("$2b$"):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            pass
    # SHA-256 fallback / salt support
    if ":" in hashed_password:
        salt, h = hashed_password.split(":", 1)
        expected = hashlib.sha256((salt + plain_password).encode('utf-8')).hexdigest()
        return expected == h
    # plain sha256 or direct match for demo seeds
    return (
        hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password
        or plain_password == hashed_password
    )


def get_password_hash(password: str) -> str:
    if HAS_BCRYPT:
        try:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        except Exception:
            pass
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}:{h}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def get_current_user_payload(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


class RequireRoles:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, payload: dict = Depends(get_current_user_payload)) -> dict:
        user_role = payload.get("role", UserRole.VIEWER)
        # ADMIN has superuser permission across all roles
        if user_role == UserRole.ADMIN:
            return payload
        # Match role (e.g. COORDINATOR matches DVI_COORDINATOR)
        if user_role in self.allowed_roles:
            return payload
        if user_role == UserRole.DVI_COORDINATOR and UserRole.COORDINATOR in self.allowed_roles:
            return payload
        if user_role == UserRole.COORDINATOR and UserRole.DVI_COORDINATOR in self.allowed_roles:
            return payload
        if user_role == UserRole.AM_TEAM and UserRole.FIELD_OPERATOR in self.allowed_roles:
            return payload
        if user_role == UserRole.PM_TEAM and UserRole.FIELD_OPERATOR in self.allowed_roles:
            return payload

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted for role '{user_role}'. Required: {self.allowed_roles}",
        )
