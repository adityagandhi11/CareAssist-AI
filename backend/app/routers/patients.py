from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[UserRead])
def list_patients(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.role == "patient").order_by(User.id)).all()


@router.get("/{patient_id}", response_model=UserRead)
def get_patient(patient_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    patient = db.get(User, patient_id)
    if patient is None or patient.role != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.patch("/{patient_id}/deactivate", response_model=UserRead)
def deactivate_patient(patient_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    patient = db.get(User, patient_id)
    if patient is None or patient.role != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_active = False
    db.commit()
    db.refresh(patient)
    return patient
