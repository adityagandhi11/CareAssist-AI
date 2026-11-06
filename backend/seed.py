"""Seed the local administrator and repeat-safe synthetic demonstration data."""

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, initialize_database
from app.models import Appointment, Enquiry, KnowledgeDocument, User
from app.security import hash_password

ADMIN_EMAIL = "admin@careassist.local"
ADMIN_PASSWORD = "CareAssistAdmin123!"
DEMO_PATIENT_PASSWORD = "PatientDemo123!"

DEMO_PATIENTS = (
    ("demo.avery@careassist.local", "Avery Morgan"),
    ("demo.jordan@careassist.local", "Jordan Lee"),
    ("demo.sam@careassist.local", "Sam Rivera"),
)


def _ensure_admin(db: Session) -> User:
    admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    if admin is None:
        admin = User(
            email=ADMIN_EMAIL,
            full_name="CareAssist Administrator",
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.flush()
    else:
        admin.full_name = "CareAssist Administrator"
        admin.password_hash = hash_password(ADMIN_PASSWORD)
        admin.role = "admin"
        admin.is_active = True
    return admin


def _ensure_patients(db: Session) -> dict[str, User]:
    patients: dict[str, User] = {}
    for email, full_name in DEMO_PATIENTS:
        patient = db.scalar(select(User).where(User.email == email))
        if patient is None:
            patient = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(DEMO_PATIENT_PASSWORD),
                role="patient",
                is_active=True,
            )
            db.add(patient)
            db.flush()
        else:
            patient.full_name = full_name
            patient.password_hash = hash_password(DEMO_PATIENT_PASSWORD)
            patient.role = "patient"
            patient.is_active = True
        patients[email] = patient
    return patients


def _available_demo_slots(db: Session):
    duration_minutes = settings.appointment_duration_minutes
    if duration_minutes < 1 or duration_minutes > 480:
        raise ValueError("APPOINTMENT_DURATION_MINUTES must be between 1 and 480")
    opening = time.fromisoformat(settings.clinic_open_time)
    closing = time.fromisoformat(settings.clinic_close_time)
    if opening >= closing:
        raise ValueError("CLINIC_OPEN_TIME must be earlier than CLINIC_CLOSE_TIME")

    zone = settings.clinic_zone
    now = datetime.now(timezone.utc)
    step = timedelta(minutes=duration_minutes)
    first_day = datetime.now(zone).date()
    for offset in range(60):
        appointment_day = first_day + timedelta(days=offset)
        if appointment_day.weekday() not in settings.working_day_numbers:
            continue
        cursor = datetime.combine(appointment_day, opening, tzinfo=zone)
        close_at = datetime.combine(appointment_day, closing, tzinfo=zone)
        while cursor + step <= close_at:
            starts_at = cursor.astimezone(timezone.utc)
            ends_at = (cursor + step).astimezone(timezone.utc)
            starts_db = starts_at.replace(tzinfo=None)
            ends_db = ends_at.replace(tzinfo=None)
            if starts_at > now and not db.scalar(
                select(Appointment.id).where(
                    Appointment.status.in_(("pending", "approved")),
                    Appointment.starts_at < ends_db,
                    Appointment.ends_at > starts_db,
                )
            ):
                yield starts_db, ends_db
            cursor += step


def _seed_appointments(db: Session, patients: dict[str, User]) -> None:
    fixtures = (
        ("demo.avery@careassist.local", "Demo: general health checkup", "approved"),
        ("demo.jordan@careassist.local", "Demo: preventive wellness visit", "pending"),
        ("demo.sam@careassist.local", "Demo: routine vaccination", "pending"),
    )
    slots = _available_demo_slots(db)
    for email, reason, status in fixtures:
        patient = patients[email]
        exists = db.scalar(
            select(Appointment.id).where(
                Appointment.patient_id == patient.id,
                Appointment.reason == reason,
            )
        )
        if exists is not None:
            continue
        slot = next(slots, None)
        if slot is None:
            raise RuntimeError("Could not find a future clinic slot for synthetic demo appointments")
        starts_at, ends_at = slot
        db.add(
            Appointment(
                patient_id=patient.id,
                starts_at=starts_at,
                ends_at=ends_at,
                reason=reason,
                status=status,
            )
        )
        db.flush()

    patient = patients["demo.avery@careassist.local"]
    reason = "Demo: completed general checkup"
    if db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient.id,
            Appointment.reason == reason,
        )
    ) is None:
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)
        starts_at = past.replace(hour=10, minute=0, second=0, microsecond=0)
        db.add(
            Appointment(
                patient_id=patient.id,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=settings.appointment_duration_minutes),
                reason=reason,
                status="completed",
                created_at=starts_at - timedelta(days=2),
            )
        )
        db.flush()


def _seed_enquiries(db: Session, patients: dict[str, User]) -> None:
    fixtures = (
        (
            "demo.avery@careassist.local",
            "Clinic opening hours",
            "Could you confirm the clinic's opening hours for weekdays?",
            "general",
            "Asks for the clinic's weekday operating hours.",
            "clinic_hours",
            "The sample clinic information lists weekday hours as Monday through Friday, 8:00 AM to 5:00 PM. Please confirm with clinic staff if you need current availability.",
            "open",
            "pending",
        ),
        (
            "demo.jordan@careassist.local",
            "Changing an appointment",
            "I need help changing the time of my upcoming appointment.",
            "appointment",
            "Requests help changing an appointment time.",
            "reschedule_appointment",
            "Please share your preferred time with clinic staff. They can help review available appointment options.",
            "in_progress",
            "pending",
        ),
        (
            "demo.sam@careassist.local",
            "Preventive wellness visits",
            "Does the clinic offer general health checkups or wellness visits?",
            "services",
            "Asks whether general checkups and wellness visits are offered.",
            "service_information",
            "The sample clinic information lists general health checkups and preventive wellness visits. Clinic staff can confirm current availability.",
            "open",
            "approved",
        ),
        (
            "demo.avery@careassist.local",
            "Insurance and billing",
            "What should I bring if I have health insurance?",
            "billing",
            "Asks what insurance information to bring to an appointment.",
            "insurance_information",
            "The sample clinic information asks patients with insurance to bring their insurance card. Please contact clinic staff for billing-specific questions.",
            "resolved",
            "approved",
        ),
    )
    for email, subject, message, category, summary, intent, response, status, review_status in fixtures:
        patient = patients[email]
        exists = db.scalar(
            select(Enquiry.id).where(
                Enquiry.patient_id == patient.id,
                Enquiry.subject == subject,
            )
        )
        if exists is None:
            db.add(
                Enquiry(
                    patient_id=patient.id,
                    subject=subject,
                    message=message,
                    category=category,
                    summary=summary,
                    intent=intent,
                    suggested_response=response,
                    status=status,
                    review_status=review_status,
                )
            )
    db.flush()


def _seed_documents(db: Session, admin: User) -> None:
    sample_data = Path(__file__).resolve().parents[1] / "sample_data"
    upload_directory = Path(settings.upload_directory)
    upload_directory.mkdir(parents=True, exist_ok=True)
    for filename in (
        "clinic_information.txt",
        "appointment_policies.txt",
        "services_faq.txt",
    ):
        source = sample_data / filename
        data = source.read_bytes()
        content_hash = hashlib.sha256(data).hexdigest()
        exists = db.scalar(
            select(KnowledgeDocument.id).where(KnowledgeDocument.content_hash == content_hash)
        )
        if exists is not None:
            continue

        stored_filename = f"demo-{content_hash[:16]}.txt"
        stored_path = upload_directory / stored_filename
        if not stored_path.exists() or stored_path.read_bytes() != data:
            stored_path.write_bytes(data)
        content = data.decode("utf-8-sig").strip()
        db.add(
            KnowledgeDocument(
                filename=filename,
                storage_path=str(stored_path),
                content=content,
                content_hash=content_hash,
                page_contents=json.dumps([content]),
                page_count=1,
                status="pending",
                uploaded_by=admin.id,
            )
        )
    db.flush()


def seed_demo_data(db: Session, admin: User) -> None:
    """Insert synthetic clinic content once, preserving existing application data."""
    patients = _ensure_patients(db)
    _seed_appointments(db, patients)
    _seed_enquiries(db, patients)
    _seed_documents(db, admin)


def seed_admin() -> None:
    initialize_database()
    with SessionLocal() as db:
        admin = _ensure_admin(db)
        seed_demo_data(db, admin)
        db.commit()

    print("Seeded local synthetic demonstration data:")
    print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Patient accounts: {len(DEMO_PATIENTS)} (each uses {DEMO_PATIENT_PASSWORD})")
    print("  Sample appointments, enquiries, and pending clinic documents are ready.")


if __name__ == "__main__":
    seed_admin()
