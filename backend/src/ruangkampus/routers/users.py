from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user, require_admin
from ruangkampus.models import AuthSession, RoomUpdateLog, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import AdminStudentCreateIn, PasswordChangeIn, ProfileUpdateIn, UserOut, UserRoleUpdateIn, UserStatusUpdateIn
from ruangkampus.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    return success(UserOut.model_validate(current_user).model_dump(mode="json"), "Profile retrieved")


@router.patch("/me")
def update_profile(payload: ProfileUpdateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(current_user, key, str(value) if key == "profile_image_url" and value is not None else value)
    current_user.updated_at = utcnow()
    db.commit()
    db.refresh(current_user)
    return success(UserOut.model_validate(current_user).model_dump(mode="json"), "Profile updated")


@router.patch("/me/password")
def change_password(payload: PasswordChangeIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="New password must differ from current password")
    current_user.password_hash = hash_password(payload.new_password)
    current_user.updated_at = utcnow()
    db.query(AuthSession).filter(AuthSession.user_id == current_user.id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: utcnow()}, synchronize_session=False)
    db.commit()
    return success(None, "Password changed. Please sign in again")


@router.get("")
def list_users(
    search: str | None = None,
    role: str | None = Query(default=None, pattern="^(STUDENT|TU_ADMIN)$"),
    account_status: str | None = Query(default=None, pattern="^(ACTIVE|DISABLED)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(term), User.email.ilike(term), User.student_identifier.ilike(term)))
    if role:
        stmt = stmt.where(User.role == role)
    if account_status:
        stmt = stmt.where(User.account_status == account_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    meta = {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit) if total else 0}
    return success([UserOut.model_validate(item).model_dump(mode="json") for item in users], "Users retrieved", meta)


def _ensure_not_last_active_admin(db: Session, target: User, next_role: str | None = None, next_status: str | None = None, deleting: bool = False):
    will_remove_admin = target.role == "TU_ADMIN" and target.account_status == "ACTIVE" and (next_role == "STUDENT" or next_status == "DISABLED" or deleting)
    if will_remove_admin:
        active_admins = db.scalar(select(func.count(User.id)).where(User.role == "TU_ADMIN", User.account_status == "ACTIVE", User.deleted_at.is_(None))) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="The last active TU/Admin account cannot be disabled, demoted, or deleted")


def _user_audit_snapshot(user: User) -> dict:
    return {
        "name": user.name,
        "email": user.email,
        "student_identifier": user.student_identifier,
        "role": user.role,
        "account_status": user.account_status,
    }


def _record_user_change(db: Session, admin: User, target: User, action: str, previous: dict | None) -> None:
    db.add(RoomUpdateLog(
        admin_id=admin.id,
        entity_type="USER",
        entity_id=target.id,
        action=action,
        previous_value=previous,
        new_value=_user_audit_snapshot(target),
    ))


@router.post("", status_code=201)
def create_student_account(
    payload: AdminStudentCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email = str(payload.email).lower().strip()
    identifier = payload.student_identifier.strip()
    if identifier.lower() == "admin.uhamka":
        raise HTTPException(status_code=409, detail="This identifier is reserved for the administrator")
    duplicate = db.scalar(select(User.id).where(
        (func.lower(User.email) == email) | (func.lower(User.student_identifier) == identifier.lower())
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="An account with this email or NIM already exists")
    student = User(
        name=payload.name.strip(),
        email=email,
        student_identifier=identifier,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="STUDENT",
        account_status="ACTIVE",
    )
    db.add(student)
    db.flush()
    _record_user_change(db, admin, student, "CREATE_STUDENT", None)
    db.commit()
    db.refresh(student)
    return success(UserOut.model_validate(student).model_dump(mode="json"), "Student account created")


@router.patch("/{user_id}/status")
def update_user_status(user_id: UUID, payload: UserStatusUpdateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id and payload.account_status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Administrators cannot disable their own account")
    target = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_not_last_active_admin(db, target, next_status=payload.account_status)
    previous = _user_audit_snapshot(target)
    target.account_status = payload.account_status
    target.updated_at = utcnow()
    if target.account_status == "DISABLED":
        db.query(AuthSession).filter(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: utcnow()}, synchronize_session=False)
    _record_user_change(db, admin, target, "UPDATE_STATUS", previous)
    db.commit()
    db.refresh(target)
    return success(UserOut.model_validate(target).model_dump(mode="json"), "User status updated")


@router.patch("/{user_id}/role")
def update_user_role(user_id: UUID, payload: UserRoleUpdateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="Administrators cannot change their own role")
    target = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_not_last_active_admin(db, target, next_role=payload.role.value)
    previous = _user_audit_snapshot(target)
    target.role = payload.role.value
    target.updated_at = utcnow()
    db.query(AuthSession).filter(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: utcnow()}, synchronize_session=False)
    _record_user_change(db, admin, target, "UPDATE_ROLE", previous)
    db.commit()
    db.refresh(target)
    return success(UserOut.model_validate(target).model_dump(mode="json"), "User role updated; previous sessions have been revoked")


@router.delete("/{user_id}")
def soft_delete_user(user_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="Administrators cannot delete their own account")
    target = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_not_last_active_admin(db, target, deleting=True)
    now = utcnow()
    previous = _user_audit_snapshot(target)
    target.deleted_at = now
    target.account_status = "DISABLED"
    target.updated_at = now
    db.query(AuthSession).filter(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: now}, synchronize_session=False)
    _record_user_change(db, admin, target, "DELETE_USER", previous)
    db.commit()
    return success({"id": str(target.id), "deleted": True}, "User deactivated; reservation history is retained")
