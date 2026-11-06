from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Appointment, Enquiry, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        today = datetime.now(timezone.utc).date()
        return {
            "role": "admin",
            "patients_total": db.scalar(select(func.count(User.id)).where(User.role == "patient")) or 0,
            "appointments_total": db.scalar(select(func.count(Appointment.id))) or 0,
            "appointments_pending": db.scalar(
                select(func.count(Appointment.id)).where(Appointment.status == "pending")
            )
            or 0,
            "appointments_today": db.scalar(
                select(func.count(Appointment.id)).where(func.date(Appointment.starts_at) == today.isoformat())
            )
            or 0,
            "enquiries_open": db.scalar(
                select(func.count(Enquiry.id)).where(Enquiry.status.in_(("open", "in_progress")))
            )
            or 0,
            "enquiries_total": db.scalar(select(func.count(Enquiry.id))) or 0,
        }

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return {
        "role": "patient",
        "appointments_upcoming": db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.patient_id == user.id,
                Appointment.starts_at >= now,
                Appointment.status.in_(("pending", "approved")),
            )
        )
        or 0,
        "appointments_pending": db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.patient_id == user.id, Appointment.status == "pending"
            )
        )
        or 0,
        "enquiries_open": db.scalar(
            select(func.count(Enquiry.id)).where(
                Enquiry.patient_id == user.id, Enquiry.status.in_(("open", "in_progress"))
            )
        )
        or 0,
    }
