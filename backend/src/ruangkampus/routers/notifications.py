from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user
from ruangkampus.models import Notification, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(unread_only: bool = Query(default=False, alias="unreadOnly"), page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Notification).where(Notification.recipient_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    meta = {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit) if total else 0}
    return success([NotificationOut.model_validate(item).model_dump(mode="json") for item in items], "Notifications retrieved", meta)


@router.patch("/{notification_id}/read")
def mark_read(notification_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user.id).with_for_update())
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = notification.read_at or utcnow()
    db.commit()
    db.refresh(notification)
    return success(NotificationOut.model_validate(notification).model_dump(mode="json"), "Notification marked as read")
