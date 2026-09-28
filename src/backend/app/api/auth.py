from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user_payload,
    RequireRoles,
    UserRole,
)
from app.models.entities import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    token = create_access_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
    })

    AuditService.log_event(
        db=db,
        user_id=user.id,
        role=user.role,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/register", response_model=UserResponse)
def register_user(
    user_in: UserCreate,
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        full_name=user_in.full_name,
        is_active=user_in.is_active,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    AuditService.log_event(
        db=db,
        user_id=current_user.get("sub", "ADMIN"),
        role=current_user.get("role", "ADMIN"),
        action="USER_CREATED",
        entity_type="USER",
        entity_id=new_user.id,
        details={"username": new_user.username, "role": new_user.role},
    )

    return new_user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: dict = Depends(RequireRoles([UserRole.ADMIN, UserRole.COORDINATOR])),
    db: Session = Depends(get_db),
):
    return db.query(User).all()
