import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .main_dependencies import get_db
from .models import AccountToken, RefreshToken, User

passwords = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = passwords.hash("not-a-real-eklavya-account-password")
bearer = HTTPBearer(auto_error=False)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    return passwords.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return passwords.verify(password, encoded)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id), "role": user.role, "type": "access",
        "iat": now, "exp": now + timedelta(minutes=settings().access_token_minutes),
    }
    return jwt.encode(payload, settings().secret_key, algorithm="HS256")


def issue_refresh_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings().refresh_token_days),
    ))
    return token


def consume_refresh_token(db: Session, raw_token: str) -> User:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update())
    now = datetime.now(timezone.utc)
    if token is None or token.revoked_at is not None or _aware(token.expires_at) <= now:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    token.revoked_at = now
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)


def issue_account_token(db: Session, user: User, purpose: str, lifetime: timedelta) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AccountToken(
        user_id=user.id, purpose=purpose,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + lifetime,
    ))
    return token


def consume_account_token(db: Session, raw_token: str, purpose: str) -> User:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(AccountToken).where(
        AccountToken.token_hash == token_hash, AccountToken.purpose == purpose,
    ).with_for_update())
    now = datetime.now(timezone.utc)
    if token is None or token.used_at is not None or _aware(token.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Token is invalid or expired")
    token.used_at = now
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Token is invalid or expired")
    return user


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings().secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise InvalidTokenError
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Access token is invalid or expired") from error
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Anonymous viewers receive ALL content only; invalid tokens never grant access."""
    if credentials is None:
        return None
    return current_user(credentials, db)


OptionalUser = Annotated[User | None, Depends(optional_current_user)]
