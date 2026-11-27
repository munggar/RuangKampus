from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import get_current_user
from ruangkampus.models import Reservation, Room, User
from ruangkampus.responses import success
from ruangkampus.routers.reservations import _reservation_query
from ruangkampus.schemas import serialize_reservation

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "TU_ADMIN":
        total_rooms = db.scalar(select(func.count(Room.id)).where(Room.deleted_at.is_(None))) or 0
        active_rooms = db.scalar(select(func.count(Room.id)).where(Room.deleted_at.is_(None), Room.room_status == "ACTIVE")) or 0
        total_users = db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0
        counts = {}
        for state in ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"]:
            counts[state.lower()] = db.scalar(select(func.count(Reservation.id)).where(Reservation.status == state)) or 0
        total_reservations = sum(counts.values())
        data = {"role": user.role, "total_rooms": total_rooms, "active_rooms": active_rooms, "total_users": total_users, "total_reservations": total_reservations, **counts}
    else:
        counts = {}
        for state in ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"]:
            counts[state.lower()] = db.scalar(select(func.count(Reservation.id)).where(Reservation.user_id == user.id, Reservation.status == state)) or 0
        data = {"role": user.role, "total_reservations": sum(counts.values()), **counts}
    return success(data, "Dashboard summary retrieved")


@router.get("/recent-reservations")
def recent_reservations(limit: int = Query(default=8, ge=1, le=50), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = _reservation_query()
    if user.role != "TU_ADMIN":
        stmt = stmt.where(Reservation.user_id == user.id)
    items = db.scalars(stmt.order_by(Reservation.submitted_at.desc()).limit(limit)).unique().all()
    result = []
    for item in items:
        row = serialize_reservation(item)
        row["room"] = {"id": str(item.room.id), "room_name": item.room.room_name, "building": item.room.building}
        if user.role == "TU_ADMIN":
            row["applicant"] = {"id": str(item.user.id), "name": item.user.name, "email": item.user.email}
        result.append(row)
    return success(result, "Recent reservations retrieved")


@router.get("/room-statistics")
def room_statistics(date_from: date | None = Query(default=None, alias="dateFrom"), date_to: date | None = Query(default=None, alias="dateTo"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "TU_ADMIN":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Administrator access required")
    filters = [Reservation.status.in_(["APPROVED", "COMPLETED"])]
    if date_from:
        filters.append(Reservation.reservation_date >= date_from)
    if date_to:
        filters.append(Reservation.reservation_date <= date_to)
    rows = db.execute(
        select(Room.id, Room.room_name, Room.building, func.count(Reservation.id).label("reservation_count"))
        .outerjoin(Reservation, and_(Reservation.room_id == Room.id, *filters))
        .where(Room.deleted_at.is_(None))
        .group_by(Room.id, Room.room_name, Room.building)
        .order_by(func.count(Reservation.id).desc(), Room.room_name.asc())
    ).all()
    return success([{"room_id": str(row.id), "room_name": row.room_name, "building": row.building, "reservation_count": row.reservation_count} for row in rows], "Room statistics retrieved")
