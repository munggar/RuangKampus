from math import ceil
from uuid import UUID

import logging
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user
from ruangkampus.models import Notification, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import NotificationOut
from ruangkampus.services.mail import render_html_email, send_email

logger = logging.getLogger(__name__)

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


@router.patch("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = utcnow()
    result = db.execute(
        update(Notification)
        .where(Notification.recipient_id == user.id, Notification.read_at.is_(None))
        .values(read_at=now)
    )
    db.commit()
    return success({"updated_count": result.rowcount or 0, "read_at": now.isoformat()}, "All notifications marked as read")


@router.patch("/{notification_id}/read")
def mark_read(notification_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user.id).with_for_update())
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = notification.read_at or utcnow()
    db.commit()
    db.refresh(notification)
    return success(NotificationOut.model_validate(notification).model_dump(mode="json"), "Notification marked as read")


@router.post("/{notification_id}/retry-email")
def retry_notification_email(notification_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.scalar(
        select(Notification)
        .options(joinedload(Notification.recipient))
        .where(Notification.id == notification_id)
        .with_for_update()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if user.role != "TU_ADMIN" and notification.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.email_delivery_status != "FAILED":
        raise HTTPException(status_code=409, detail="Only failed email notifications can be retried")
    if notification.email_attempt_count >= 3:
        raise HTTPException(status_code=409, detail="Email retry limit reached")

    # Claim this manual retry before contacting the provider to avoid concurrent sends.
    notification.email_attempted_at = utcnow()
    notification.email_attempt_count += 1
    notification.email_delivery_status = "ATTEMPTED"
    db.commit()

    settings = get_settings()
    recipient = notification.recipient
    action_url = (
        settings.public_app_url.rstrip("/") + notification.action_url
        if notification.action_url else settings.public_app_url.rstrip("/")
    )
    plain_body = notification.message + (f"\\n\\nBuka RuangKampus: {action_url}" if notification.action_url else "")
    try:
        delivered = send_email(
            recipient.email,
            notification.title,
            plain_body,
            render_html_email(
                notification.title,
                notification.message,
                action_url,
                "Lihat detail di RuangKampus" if notification.action_url else "Buka RuangKampus",
                preheader=notification.message,
                eyebrow="PEMBARUAN RUANGKAMPUS",
                accent_color="#3268dc",
            ),
        )
        if delivered:
            notification.email_delivery_status = (
                "LOCAL_MAILBOX_WRITTEN" if settings.email_backend == "console" else "SENT"
            )
            notification.email_sent_at = utcnow() if settings.email_backend in {"smtp", "brevo"} else None
        else:
            notification.email_delivery_status = "NOT_CONFIGURED"
    except Exception as exc:
        notification.email_delivery_status = "FAILED"
        logger.error("Manual notification email retry failed (exception_type=%s)", type(exc).__name__)
    db.commit()
    db.refresh(notification)
    return success(
        NotificationOut.model_validate(notification).model_dump(mode="json"),
        "Email notification retry processed",
    )
