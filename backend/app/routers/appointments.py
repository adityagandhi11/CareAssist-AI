from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Appointment, User
from app.schemas import AppointmentCreate, AppointmentRead, AppointmentUpdate, AvailableSlot
from app.config import settings

router = APIRouter(prefix="/appointments", tags=["appointments"])
BUSY_STATUSES = ("pending", "approved")


@router.get("/available-slots", response_model=list[AvailableSlot])
def available_slots(
    slot_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if slot_date < datetime.now(settings.clinic_zone).date():
        return []
    if slot_date.weekday() not in settings.working_day_numbers:
        return []
    try:
        open_at = time.fromisoformat(settings.clinic_open_time)
        close_at = time.fromisoformat(settings.clinic_close_time)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Clinic hours are misconfigured") from exc
    duration = settings.appointment_duration_minutes
    if duration < 1 or duration > 480 or open_at >= close_at:
        raise HTTPException(status_code=500, detail="Clinic hours or appointment duration are misconfigured")

    zone = settings.clinic_zone
    opening = datetime.combine(slot_date, open_at, tzinfo=zone)
    closing = datetime.combine(slot_date, close_at, tzinfo=zone)
    step = timedelta(minutes=duration)
    slots: list[AvailableSlot] = []
    now_utc = datetime.now(timezone.utc)
    cursor = opening
    while cursor + step <= closing:
        starts_at = cursor.astimezone(timezone.utc)
        ends_at = (cursor + step).astimezone(timezone.utc)
        if starts_at > now_utc:
            starts_db = starts_at.replace(tzinfo=None)
            ends_db = ends_at.replace(tzinfo=None)
            if not db.scalar(
                select(Appointment.id).where(
                    Appointment.status.in_(BUSY_STATUSES),
                    Appointment.starts_at < ends_db,
                    Appointment.ends_at > starts_db,
                )
            ):
                slots.append(AvailableSlot(starts_at=starts_at, ends_at=ends_at))
        cursor += step
    return slots


def _assert_no_conflict(db: Session, starts_at: datetime, ends_at: datetime, exclude_id: int | None = None):
    query = select(Appointment).where(
        Appointment.status.in_(BUSY_STATUSES),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    )
    if exclude_id is not None:
        query = query.where(Appointment.id != exclude_id)
    if db.scalar(query):
        raise HTTPException(status_code=409, detail="Requested appointment time conflicts with an existing booking")


def _validate_clinic_slot(starts_at: datetime, ends_at: datetime) -> None:
    try:
        opening_time = time.fromisoformat(settings.clinic_open_time)
        closing_time = time.fromisoformat(settings.clinic_close_time)
        working_days = settings.working_day_numbers
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=500, detail="Clinic schedule is misconfigured") from exc
    duration = settings.appointment_duration_minutes
    if duration < 1 or duration > 480 or opening_time >= closing_time:
        raise HTTPException(status_code=500, detail="Clinic schedule is misconfigured")
    local_start = starts_at.replace(tzinfo=timezone.utc).astimezone(settings.clinic_zone)
    local_end = ends_at.replace(tzinfo=timezone.utc).astimezone(settings.clinic_zone)
    opening = datetime.combine(local_start.date(), opening_time, tzinfo=settings.clinic_zone)
    closing = datetime.combine(local_start.date(), closing_time, tzinfo=settings.clinic_zone)
    if (
        local_start.weekday() not in working_days
        or local_end.date() != local_start.date()
        or local_start < opening
        or local_end > closing
        or ends_at - starts_at != timedelta(minutes=duration)
        or (local_start - opening).total_seconds() % (duration * 60) != 0
    ):
        raise HTTPException(status_code=422, detail="Appointment must match an available clinic slot")


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_clinic_slot(payload.starts_at, payload.ends_at)
    _assert_no_conflict(db, payload.starts_at, payload.ends_at)
    appointment = Appointment(patient_id=user.id, **payload.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentRead])
def list_appointments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Appointment).order_by(Appointment.starts_at)
    if user.role != "admin":
        query = query.where(Appointment.patient_id == user.id)
    return db.scalars(query).all()


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or (user.role != "admin" and appointment.patient_id != user.id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or (user.role != "admin" and appointment.patient_id != user.id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    updates = payload.model_dump(exclude_unset=True)
    if user.role != "admin":
        if set(updates) - {"starts_at", "ends_at", "reason", "status"}:
            raise HTTPException(status_code=403, detail="Not permitted")
        if "status" in updates and updates["status"] != "cancelled":
            raise HTTPException(status_code=403, detail="Patients may only cancel appointments")
        if updates.get("status") == "cancelled":
            if appointment.status in ("completed", "cancelled"):
                raise HTTPException(status_code=409, detail="This appointment cannot be cancelled")
            appointment.status = "cancelled"
            db.commit()
            db.refresh(appointment)
            return appointment
    starts_at = updates.get("starts_at", appointment.starts_at)
    ends_at = updates.get("ends_at", appointment.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="ends_at must be after starts_at")
    if starts_at <= datetime.now(timezone.utc).replace(tzinfo=None) and ("starts_at" in updates or "ends_at" in updates):
        raise HTTPException(status_code=422, detail="Appointment must be in the future")
    if "starts_at" in updates or "ends_at" in updates:
        _validate_clinic_slot(starts_at, ends_at)
        _assert_no_conflict(db, starts_at, ends_at, appointment.id)
    for key, value in updates.items():
        setattr(appointment, key, value)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(appointment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or (user.role != "admin" and appointment.patient_id != user.id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail="This appointment cannot be cancelled")
    appointment.status = "cancelled"
    db.commit()
