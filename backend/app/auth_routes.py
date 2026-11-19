import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    CurrentUser, DUMMY_PASSWORD_HASH, consume_account_token, consume_refresh_token, create_access_token, hash_password,
    issue_account_token, issue_refresh_token, normalize_email, normalize_username,
    revoke_refresh_token, verify_password,
)
from .main_dependencies import get_db
from .models import Profile, RefreshToken, User
from .schemas_auth import (
    AuthTokens, EmailRequest, LoginRequest, PasswordResetRequest, ProfileRead, ProfileUpdate,
    RefreshRequest, RegisterRequest, TokenRequest,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
DB = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthTokens, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DB) -> AuthTokens:
    email = normalize_email(payload.email)
    username = normalize_username(payload.username)
    exists = db.scalar(select(User.id).where(or_(User.email == email, User.username == username)))
    if exists is not None:
        raise HTTPException(status_code=409, detail="Email or username is already registered")
    user = User(
        email=email, username=username, password_hash=hash_password(payload.password),
        profile=Profile(display_name=payload.display_name.strip()),
    )
    db.add(user)
    try:
        db.flush()
        issue_account_token(db, user, "verify_email", timedelta(hours=24))
        logger.info("Email verification token issued for user %s", user.id)
        tokens = AuthTokens(access_token=create_access_token(user), refresh_token=issue_refresh_token(db, user))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or username is already registered") from error
    return tokens


@router.post("/login", response_model=AuthTokens)
def login(payload: LoginRequest, db: DB) -> AuthTokens:
    identity = payload.identity.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == identity, User.username == identity)))
    password_valid = verify_password(payload.password, user.password_hash if user is not None else DUMMY_PASSWORD_HASH)
    if user is None or not password_valid or not user.is_active:
        raise HTTPException(status_code=401, detail="Email, username, or password is incorrect")
    user.last_login_at = datetime.now(timezone.utc)
    tokens = AuthTokens(access_token=create_access_token(user), refresh_token=issue_refresh_token(db, user))
    db.commit()
    return tokens


@router.post("/refresh", response_model=AuthTokens)
def refresh(payload: RefreshRequest, db: DB) -> AuthTokens:
    user = consume_refresh_token(db, payload.refresh_token)
    tokens = AuthTokens(access_token=create_access_token(user), refresh_token=issue_refresh_token(db, user))
    db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DB) -> None:
    revoke_refresh_token(db, payload.refresh_token)
    db.commit()


@router.get("/me", response_model=ProfileRead)
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=ProfileRead)
def update_me(payload: ProfileUpdate, user: CurrentUser, db: DB) -> User:
    stored = db.get(User, user.id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Account not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(stored.profile, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(stored)
    return stored


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(payload: TokenRequest, db: DB) -> None:
    user = consume_account_token(db, payload.token, "verify_email")
    user.email_verified = True
    db.commit()


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: EmailRequest, db: DB) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if user is not None and user.is_active:
        issue_account_token(db, user, "reset_password", timedelta(hours=1))
        logger.info("Password reset token issued for user %s", user.id)
        db.commit()
    return {"detail": "If the account exists, reset instructions have been issued"}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(payload: PasswordResetRequest, db: DB) -> None:
    user = consume_account_token(db, payload.token, "reset_password")
    user.password_hash = hash_password(payload.password)
    db.execute(update(RefreshToken).where(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None),
    ).values(revoked_at=datetime.now(timezone.utc)))
    db.commit()
