from datetime import date
import logging
from math import ceil
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user, require_admin, require_student
from ruangkampus.models import Notification, Reservation, Room, RoomUpdateLog, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import ReservationCancelIn, ReservationCreateIn, ReservationRejectIn, serialize_reservation
from ruangkampus.services.availability import check_room_availability, ensure_future_campus_time
from ruangkampus.services.mail import render_html_email, send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reservations", tags=["Reservations"])


def _locked_room(db: Session, room_id: UUID) -> Room:
    room = db.scalar(select(Room).where(Room.id == room_id, Room.deleted_at.is_(None)).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def _reservation_query():
    return select(Reservation).options(joinedload(Reservation.room), joinedload(Reservation.user))


def _get_reservation(db: Session, reservation_id: UUID, lock: bool = False) -> Reservation:
    stmt = select(Reservation).where(Reservation.id == reservation_id)
    if lock:
        stmt = stmt.with_for_update()
    reservation = db.scalar(stmt)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


def _notify_once(
    db: Session,
    recipient: User,
    notification_type: str,
    title: str,
    message: str,
    event_key: str,
    action_url: str | None = None,
) -> tuple[Notification, bool]:
    existing = db.scalar(select(Notification).where(Notification.event_key == event_key))
    if existing is not None:
        return existing, False
    notification = Notification(
        recipient_id=recipient.id,
        notification_type=notification_type,
        title=title,
        message=message,
        delivery_status="IN_APP_CREATED",
        email_delivery_status="NOT_CONFIGURED",
        event_key=event_key,
        action_url=action_url,
    )
    try:
        with db.begin_nested():
            db.add(notification)
            db.flush()
        return notification, True
    except IntegrityError:
        existing = db.scalar(select(Notification).where(Notification.event_key == event_key))
        if existing is None:
            raise
        return existing, False


def _deliver_notification_email(
    db: Session,
    notification: Notification,
    recipient: User,
    *,
    reservation: Reservation,
    email_subject: str,
    email_intro: str,
    eyebrow: str,
    accent_color: str,
    extra_details: list[tuple[str, str]] | None = None,
) -> None:
    # Claim the one permitted attempt under a row lock. Email providers cannot guarantee
    # exactly-once delivery across network timeouts, so retries are not automatic.
    record = db.scalar(select(Notification).where(Notification.id == notification.id).with_for_update())
    if record is None or record.email_attempted_at is not None:
        return
    record.email_attempted_at = utcnow()
    record.email_attempt_count += 1
    record.email_delivery_status = "ATTEMPTED"
    db.commit()

    settings = get_settings()
    role_path = "admin" if recipient.role == "TU_ADMIN" else "student"
    action_url = (
        settings.public_app_url.rstrip("/")
        + f"/{role_path}/reservations/{reservation.id}"
    )
    reservation_date = reservation.reservation_date.strftime("%d/%m/%Y")
    reservation_time = (
        reservation.start_time.strftime("%H:%M")
        + "–"
        + reservation.end_time.strftime("%H:%M")
        + " WIB"
    )
    details: list[tuple[str, str]] = []
    if recipient.role == "TU_ADMIN":
        details.append(("Nama pemohon", reservation.user.name))
    details.extend([
        ("Ruangan", reservation.room.room_name),
        ("Gedung", reservation.room.building),
        ("Tanggal", reservation_date),
        ("Waktu", reservation_time),
        ("Jumlah peserta", str(reservation.participant_count)),
        ("Keperluan", reservation.purpose),
    ])
    if extra_details:
        details.extend(extra_details)

    plain_body = email_intro + "\n\n"
    plain_body += "\n".join(f"{label}: {value}" for label, value in details)
    plain_body += f"\n\nBuka detail reservasi: {action_url}"

    try:
        delivered = send_email(
            recipient.email,
            email_subject,
            plain_body,
            render_html_email(
                email_subject,
                email_intro,
                action_url,
                "Lihat detail reservasi",
                preheader=email_intro,
                eyebrow=eyebrow,
                details=details,
                accent_color=accent_color,
            ),
        )
        if delivered:
            record.email_delivery_status = (
                "LOCAL_MAILBOX_WRITTEN" if settings.email_backend == "console" else "SENT"
            )
            record.email_sent_at = utcnow() if settings.email_backend in {"smtp", "brevo"} else None
        else:
            record.email_delivery_status = "NOT_CONFIGURED"
    except Exception as exc:
        record.email_delivery_status = "FAILED"
        logger.error("Reservation notification email delivery failed (exception_type=%s)", type(exc).__name__)
    db.commit()


def _audit_reservation_action(db: Session, admin: User, reservation: Reservation, action: str, previous_status: str):
    db.add(RoomUpdateLog(
        admin_id=admin.id,
        entity_type="RESERVATION",
        entity_id=reservation.id,
        action=action,
        previous_value={"status": previous_status},
        new_value={"status": reservation.status, "rejection_reason": reservation.rejection_reason},
    ))


def _assert_reservation_owner(reservation: Reservation, user: User):
    if user.role != "TU_ADMIN" and reservation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Reservation not found")


@router.post("", status_code=201)
def create_reservation(payload: ReservationCreateIn, user: User = Depends(require_student), db: Session = Depends(get_db)):
    if not ensure_future_campus_time(payload.date, payload.start_time):
        raise HTTPException(status_code=422, detail="Reservation start must be in the future (Asia/Jakarta)")
    room = _locked_room(db, payload.room_id)
    result = check_room_availability(db, room, payload.date, payload.start_time, payload.end_time, payload.participant_count)
    if not result.available:
        raise HTTPException(status_code=409, detail="Room is not available for the requested period")
    reservation = Reservation(
        user_id=user.id, room_id=room.id, purpose=payload.purpose.strip(),
        reservation_date=payload.date, start_time=payload.start_time, end_time=payload.end_time,
        participant_count=payload.participant_count, notes=payload.notes, status="PENDING",
    )
    db.add(reservation)
    db.flush()
    admins = db.scalars(select(User).where(User.role == "TU_ADMIN", User.account_status == "ACTIVE", User.deleted_at.is_(None))).all()
    pending_deliveries = []
    for admin in admins:
        notification, is_new = _notify_once(
            db, admin, "RESERVATION_NEW", "Pengajuan reservasi baru",
            f"{user.name} mengajukan reservasi {room.room_name} untuk {payload.date.strftime('%d/%m/%Y')}.",
            f"reservation:{reservation.id}:new:{admin.id}",
            f"/admin/reservations/{reservation.id}",
        )
        if is_new:
            pending_deliveries.append((notification, admin))
    db.commit()
    for notification, recipient in pending_deliveries:
        _deliver_notification_email(
            db, notification, recipient, reservation=reservation,
            email_subject=f"📥 Pengajuan reservasi baru · {room.room_name}",
            email_intro=f"Halo, ada pengajuan reservasi baru dari {user.name} yang menunggu pemeriksaan.",
            eyebrow="PENGAJUAN BARU",
            accent_color="#3268dc",
        )
    db.refresh(reservation)
    return success(serialize_reservation(reservation), "Reservation request submitted")


@router.get("")
def list_reservations(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(PENDING|APPROVED|REJECTED|CANCELLED|COMPLETED)$"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = _reservation_query()
    if user.role != "TU_ADMIN":
        stmt = stmt.where(Reservation.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Reservation.status == status_filter)
    if date_from:
        stmt = stmt.where(Reservation.reservation_date >= date_from)
    if date_to:
        stmt = stmt.where(Reservation.reservation_date <= date_to)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.order_by(Reservation.submitted_at.desc()).offset((page - 1) * limit).limit(limit)).unique().all()
    meta = {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit) if total else 0}
    data = []
    for item in items:
        out = serialize_reservation(item)
        out["room"] = {"id": str(item.room.id), "room_name": item.room.room_name, "building": item.room.building, "capacity": item.room.capacity}
        out["applicant"] = {"id": str(item.user.id), "name": item.user.name, "email": item.user.email} if user.role == "TU_ADMIN" else None
        data.append(out)
    return success(data, "Reservations retrieved", meta)


@router.get("/{reservation_id}")
def get_reservation(reservation_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reservation = db.scalar(_reservation_query().where(Reservation.id == reservation_id))
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    _assert_reservation_owner(reservation, user)
    data = serialize_reservation(reservation)
    data["room"] = {"id": str(reservation.room.id), "room_name": reservation.room.room_name, "building": reservation.room.building, "capacity": reservation.room.capacity}
    if user.role == "TU_ADMIN":
        data["applicant"] = {"id": str(reservation.user.id), "name": reservation.user.name, "email": reservation.user.email}
    return success(data, "Reservation retrieved")


@router.patch("/{reservation_id}/cancel")
def cancel_reservation(reservation_id: UUID, payload: ReservationCancelIn | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reservation = _get_reservation(db, reservation_id, lock=True)
    _assert_reservation_owner(reservation, user)
    if reservation.status not in {"PENDING", "APPROVED"}:
        raise HTTPException(status_code=409, detail="Only pending or approved reservations can be cancelled")
    campus_now = utcnow().astimezone(ZoneInfo(get_settings().campus_timezone))
    start_at = campus_now.combine(reservation.reservation_date, reservation.start_time, tzinfo=ZoneInfo(get_settings().campus_timezone))
    if start_at <= campus_now:
        raise HTTPException(status_code=409, detail="A reservation cannot be cancelled after its start time")
    previous_status = reservation.status
    reservation.status = "CANCELLED"
    reservation.cancelled_at = utcnow()
    reservation.updated_at = utcnow()
    reservation.cancellation_reason = payload.reason.strip() if payload and payload.reason else None
    reservation.cancelled_by_id = user.id
    if user.role == "TU_ADMIN":
        reservation.admin_id = user.id
        _audit_reservation_action(db, user, reservation, "CANCEL_RESERVATION", previous_status)
    pending_deliveries = []
    if user.role == "TU_ADMIN":
        notification, is_new = _notify_once(
            db, reservation.user, "RESERVATION_CANCELLED", "Reservasi dibatalkan",
            f"Reservasi {reservation.room.room_name} pada {reservation.reservation_date.strftime('%d/%m/%Y')} dibatalkan oleh Admin. Alasan: {reservation.cancellation_reason or 'Tidak dicantumkan'}.",
            f"reservation:{reservation.id}:cancelled:{reservation.user_id}",
            f"/student/reservations/{reservation.id}",
        )
        if is_new:
            pending_deliveries.append((notification, reservation.user))
    else:
        admins = db.scalars(select(User).where(
            User.role == "TU_ADMIN", User.account_status == "ACTIVE", User.deleted_at.is_(None)
        )).all()
        for admin in admins:
            notification, is_new = _notify_once(
                db, admin, "RESERVATION_CANCELLED_BY_STUDENT", "Reservasi dibatalkan mahasiswa",
                f"{user.name} membatalkan reservasi {reservation.room.room_name} pada {reservation.reservation_date.strftime('%d/%m/%Y')}. Alasan: {reservation.cancellation_reason or 'Tidak dicantumkan'}.",
                f"reservation:{reservation.id}:cancelled-by-student:{admin.id}",
                f"/admin/reservations/{reservation.id}",
            )
            if is_new:
                pending_deliveries.append((notification, admin))
    db.commit()
    for notification, recipient in pending_deliveries:
        if user.role == "TU_ADMIN":
            _deliver_notification_email(
                db, notification, recipient, reservation=reservation,
                email_subject=f"⚠️ Reservasi dibatalkan · {reservation.room.room_name}",
                email_intro="Administrator membatalkan reservasi kamu. Buka detail untuk melihat status dan informasi terbaru.",
                eyebrow="RESERVASI DIBATALKAN",
                accent_color="#ea8a32",
                extra_details=[("Alasan pembatalan", reservation.cancellation_reason or "Tidak ada alasan yang dicantumkan")],
            )
        else:
            _deliver_notification_email(
                db, notification, recipient, reservation=reservation,
                email_subject=f"↩️ Pembatalan dari mahasiswa · {reservation.room.room_name}",
                email_intro=f"{user.name} membatalkan reservasi ruang. Mohon periksa perubahan jadwal dan ketersediaan ruang.",
                eyebrow="PEMBATALAN OLEH MAHASISWA",
                accent_color="#ea8a32",
                extra_details=[("Alasan pembatalan", reservation.cancellation_reason or "Tidak ada alasan yang dicantumkan")],
            )
    db.refresh(reservation)
    return success(serialize_reservation(reservation), "Reservation cancelled")


@router.patch("/{reservation_id}/approve")
def approve_reservation(reservation_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    reservation = _get_reservation(db, reservation_id, lock=True)
    if reservation.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending reservations can be approved")
    if not ensure_future_campus_time(reservation.reservation_date, reservation.start_time):
        raise HTTPException(status_code=409, detail="Expired reservation requests cannot be approved")
    room = _locked_room(db, reservation.room_id)
    result = check_room_availability(db, room, reservation.reservation_date, reservation.start_time, reservation.end_time, reservation.participant_count, exclude_reservation_id=reservation.id)
    if not result.available:
        raise HTTPException(status_code=409, detail="Reservation can no longer be approved")
    previous_status = reservation.status
    reservation.status = "APPROVED"
    reservation.admin_id = admin.id
    reservation.approved_at = utcnow()
    reservation.updated_at = utcnow()
    _audit_reservation_action(db, admin, reservation, "APPROVE_RESERVATION", previous_status)
    notification, is_new = _notify_once(
        db, reservation.user, "RESERVATION_APPROVED", "Reservasi disetujui",
        f"Reservasi {room.room_name} pada {reservation.reservation_date.strftime('%d/%m/%Y')} telah disetujui oleh Admin.",
        f"reservation:{reservation.id}:approved:{reservation.user_id}",
        f"/student/reservations/{reservation.id}",
    )
    db.commit()
    if is_new:
        _deliver_notification_email(
            db, notification, reservation.user, reservation=reservation,
            email_subject=f"🎉 Reservasi disetujui · {room.room_name}",
            email_intro="Kabar baik! Pengajuan reservasi kamu telah disetujui. Ruangan sudah tercatat untuk jadwal berikut.",
            eyebrow="RESERVASI DISETUJUI",
            accent_color="#159b70",
        )
    db.refresh(reservation)
    return success(serialize_reservation(reservation), "Reservation approved")


@router.patch("/{reservation_id}/reject")
def reject_reservation(reservation_id: UUID, payload: ReservationRejectIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    reservation = _get_reservation(db, reservation_id, lock=True)
    if reservation.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending reservations can be rejected")
    previous_status = reservation.status
    reservation.status = "REJECTED"
    reservation.admin_id = admin.id
    reservation.rejection_reason = payload.rejection_reason.strip()
    reservation.updated_at = utcnow()
    _audit_reservation_action(db, admin, reservation, "REJECT_RESERVATION", previous_status)
    notification, is_new = _notify_once(
        db, reservation.user, "RESERVATION_REJECTED", "Reservasi ditolak",
        f"Reservasi {reservation.room.room_name} pada {reservation.reservation_date.strftime('%d/%m/%Y')} ditolak. Alasan: {reservation.rejection_reason}",
        f"reservation:{reservation.id}:rejected:{reservation.user_id}",
        f"/student/reservations/{reservation.id}",
    )
    db.commit()
    if is_new:
        _deliver_notification_email(
            db, notification, reservation.user, reservation=reservation,
            email_subject=f"Pembaruan pengajuan · {reservation.room.room_name}",
            email_intro="Pengajuan reservasi kamu belum dapat disetujui. Silakan baca alasan berikut dan hubungi pengelola jika perlu klarifikasi.",
            eyebrow="RESERVASI BELUM DISETUJUI",
            accent_color="#dc5b62",
            extra_details=[("Alasan penolakan", reservation.rejection_reason or "Tidak ada alasan yang dicantumkan")],
        )
    db.refresh(reservation)
    return success(serialize_reservation(reservation), "Reservation rejected")


@router.patch("/{reservation_id}/complete")
def complete_reservation(reservation_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    reservation = _get_reservation(db, reservation_id, lock=True)
    if reservation.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only approved reservations can be completed")
    campus_now = utcnow().astimezone(ZoneInfo(get_settings().campus_timezone))
    end_at = campus_now.combine(reservation.reservation_date, reservation.end_time, tzinfo=ZoneInfo(get_settings().campus_timezone))
    if end_at > campus_now:
        raise HTTPException(status_code=409, detail="Reservation cannot be completed before its end time")
    previous_status = reservation.status
    reservation.status = "COMPLETED"
    reservation.admin_id = admin.id
    reservation.updated_at = utcnow()
    _audit_reservation_action(db, admin, reservation, "COMPLETE_RESERVATION", previous_status)
    notification, is_new = _notify_once(
        db, reservation.user, "RESERVATION_COMPLETED", "Reservasi selesai",
        f"Reservasi {reservation.room.room_name} pada {reservation.reservation_date.strftime('%d/%m/%Y')} telah ditandai selesai oleh Admin.",
        f"reservation:{reservation.id}:completed:{reservation.user_id}",
        f"/student/reservations/{reservation.id}",
    )
    db.commit()
    if is_new:
        _deliver_notification_email(
            db, notification, reservation.user, reservation=reservation,
            email_subject=f"✅ Reservasi selesai · {reservation.room.room_name}",
            email_intro="Sesi peminjaman ruangan kamu telah ditandai selesai oleh Admin. Terima kasih telah menggunakan RuangKampus.",
            eyebrow="RESERVASI SELESAI",
            accent_color="#3268dc",
        )
    db.refresh(reservation)
    return success(serialize_reservation(reservation), "Reservation marked completed")
