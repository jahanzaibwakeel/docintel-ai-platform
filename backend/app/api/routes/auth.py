from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    hash_password_reset_token,
    hash_refresh_token,
    password_reset_expires_at,
    refresh_token_expires_at,
    verify_password,
)
from app.models.session import PasswordResetToken, RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.audit import log_action
from app.services.email import send_password_reset_email
from app.services.workspaces import create_personal_workspace

router = APIRouter(prefix="/auth", tags=["auth"])


def issue_token_pair(db: Session, user: User) -> TokenResponse:
    refresh_token = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expires_at(),
        )
    )
    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    workspace = create_personal_workspace(db, user)
    log_action(db, action="auth.register", actor_id=user.id, workspace_id=workspace.id)
    response = issue_token_pair(db, user)
    db.commit()
    db.refresh(user)
    return response


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    response = issue_token_pair(db, user)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if not stored or stored.revoked_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, stored.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    stored.revoked_at = func.now()
    response = issue_token_pair(db, user)
    log_action(db, action="auth.refresh", actor_id=user.id)
    db.commit()
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if payload.refresh_token:
        token_hash = hash_refresh_token(payload.refresh_token)
        stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.user_id == current_user.id))
        if stored and stored.revoked_at is None:
            stored.revoked_at = func.now()
    log_action(db, action="auth.logout", actor_id=current_user.id)
    db.commit()


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> PasswordResetRequestResponse:
    message = "If an account exists for this email, password reset instructions have been sent."
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        return PasswordResetRequestResponse(message=message)

    raw_token = create_password_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=password_reset_expires_at(),
        )
    )
    log_action(db, action="auth.password_reset_requested", actor_id=user.id)
    db.commit()
    send_password_reset_email(user.email, raw_token)

    settings = get_settings()
    return PasswordResetRequestResponse(message=message, reset_token=raw_token if settings.password_reset_return_token else None)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_password_reset_token(payload.token)
    stored = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if not stored or stored.used_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid or expired password reset token")

    user = db.get(User, stored.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired password reset token")

    user.password_hash = hash_password(payload.new_password)
    stored.used_at = func.now()
    active_refresh_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    for refresh_token in active_refresh_tokens:
        refresh_token.revoked_at = func.now()
    log_action(db, action="auth.password_reset_completed", actor_id=user.id)
    db.commit()


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    current_user.full_name = payload.full_name
    log_action(db, action="auth.profile_update", actor_id=current_user.id)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    active_refresh_tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
    ).all()
    for refresh_token in active_refresh_tokens:
        refresh_token.revoked_at = func.now()
    log_action(db, action="auth.password_change", actor_id=current_user.id)
    db.commit()
