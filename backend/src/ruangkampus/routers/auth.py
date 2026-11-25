from datetime import timedelta
from uuid import UUID

import jwt
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user
from ruangkampus.models import AuthSession, PasswordResetToken, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, TokenOut, UserOut
from ruangkampus.security import create_access_token, generate_opaque_token, hash_opaque_token, hash_password, verify_password
from ruangkampus.services.mail import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="ruangkampus_refresh",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key="ruangkampus_refresh",
        path=f"{settings.api_v1_prefix}/auth",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def _issue_session(user: User, db: Session, response: Response, user_agent: str | None = None) -> dict:
    settings = get_settings()
    refresh_token = generate_opaque_token()
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_opaque_token(refresh_token),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=(user_agent or "")[:512] or None,
    )
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    _set_refresh_cookie(response, refresh_token)
    return TokenOut(
        access_token=create_access_token(user.id, auth_session.id, user.role),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    ).model_dump(mode="json")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    existing = db.scalar(select(User.id).where(User.email == email, User.deleted_at.is_(None)))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        name=payload.name.strip(),
        email=email,
        student_identifier=payload.student_identifier.strip() if payload.student_identifier else None,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="STUDENT",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(user)
    tokens = _issue_session(user, db, response, request.headers.get("user-agent"))
    return tokens


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    # A single generic message avoids revealing whether an email is registered.
    if user is None or user.account_status != "ACTIVE" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    tokens = _issue_session(user, db, response, request.headers.get("user-agent"))
    return tokens


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("ruangkampus_refresh")
    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh session is required")
    token_hash = hash_opaque_token(raw_token)
    auth_session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash).with_for_update())
    if auth_session is None or auth_session.revoked_at is not None:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh session is invalid")
    expires_at = auth_session.expires_at
    now = utcnow()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    user = db.scalar(select(User).where(User.id == auth_session.user_id, User.deleted_at.is_(None)))
    if expires_at <= now or user is None or user.account_status != "ACTIVE":
        auth_session.revoked_at = now
        db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh session has expired")

    # Rotate refresh token on every successful use; only the hash is stored.
    new_refresh = generate_opaque_token()
    auth_session.refresh_token_hash = hash_opaque_token(new_refresh)
    auth_session.expires_at = now + timedelta(days=get_settings().refresh_token_expire_days)
    db.commit()
    _set_refresh_cookie(response, new_refresh)
    data = TokenOut(
        access_token=create_access_token(user.id, auth_session.id, user.role),
        expires_in=get_settings().access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    ).model_dump(mode="json")
    return data


@router.post("/logout")
def logout(request: Request, response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip()
    revoked = False
    try:
        claims = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[get_settings().jwt_algorithm])
        session_id = UUID(claims["sid"])
        auth_session = db.get(AuthSession, session_id)
        if auth_session and auth_session.user_id == current_user.id and auth_session.revoked_at is None:
            auth_session.revoked_at = utcnow()
            revoked = True
    except Exception:
        pass
    if not revoked:
        raw_token = request.cookies.get("ruangkampus_refresh")
        if raw_token:
            auth_session = db.scalar(select(AuthSession).where(
                AuthSession.refresh_token_hash == hash_opaque_token(raw_token),
                AuthSession.user_id == current_user.id,
            ))
            if auth_session and auth_session.revoked_at is None:
                auth_session.revoked_at = utcnow()
    db.commit()
    _clear_refresh_cookie(response)
    return {"success": True}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user).model_dump(mode="json")


@router.post("/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None), User.account_status == "ACTIVE"))
    if user:
        raw_token = generate_opaque_token()
        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=utcnow() + timedelta(minutes=get_settings().password_reset_expire_minutes),
        )
        db.add(reset_record)
        db.commit()
        reset_url = f"{get_settings().password_reset_base_url}?token={raw_token}"
        try:
            send_email(user.email, "RuangKampus password reset", f"Use this one-time link to reset your password: {reset_url}\n\nThe link expires in {get_settings().password_reset_expire_minutes} minutes.")
        except Exception:
            # Do not expose mail-provider errors or account existence to callers.
            logger.exception("Password reset delivery failed")
    return success(None, "If an active account matches that email and email delivery is configured, reset instructions will be sent")


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    now = utcnow()
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_opaque_token(payload.token)).with_for_update())
    if record is None or record.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token is invalid or has already been used")
    expiry = record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=now.tzinfo)
    if expiry <= now:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None or user.account_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Reset token is invalid")
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = now
    record.used_at = now
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: now}, synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None), PasswordResetToken.id != record.id).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return success(None, "Password has been reset. Please sign in again")
