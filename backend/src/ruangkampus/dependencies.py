from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.models import AuthSession, User, utcnow
from ruangkampus.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError("Wrong token type")
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from None

    auth_session = db.scalar(select(AuthSession).where(AuthSession.id == session_id))
    now = utcnow()
    if auth_session is None or auth_session.user_id != user_id or auth_session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Session is no longer active", headers={"WWW-Authenticate": "Bearer"})
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Session is expired", headers={"WWW-Authenticate": "Bearer"})

    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None or user.account_status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account is not active", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    # Reuse the same full validation path for supplied credentials.
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
        if payload.get("type") != "access":
            raise ValueError("Wrong token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from None
    auth_session = db.scalar(select(AuthSession).where(AuthSession.id == session_id))
    now = utcnow()
    if auth_session is None or auth_session.user_id != user_id or auth_session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Session is no longer active")
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Session is expired")
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None or user.account_status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account is not active")
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return current_user
    return dependency


require_admin = require_roles("TU_ADMIN")
require_student = require_roles("STUDENT")
