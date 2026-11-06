from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Enquiry, User
from app.schemas import EnquiryCreate, EnquiryRead, EnquiryUpdate
from app.services.classification import analyze_enquiry

router = APIRouter(prefix="/enquiries", tags=["enquiries"])


@router.post("", response_model=EnquiryRead, status_code=status.HTTP_201_CREATED)
def create_enquiry(payload: EnquiryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = analyze_enquiry(payload.subject, payload.message)
    enquiry = Enquiry(
        patient_id=user.id,
        subject=payload.subject.strip(),
        message=payload.message.strip(),
        category=analysis.category,
        summary=analysis.summary,
        intent=analysis.intent,
        suggested_response=analysis.suggested_response,
        review_status="pending",
    )
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.get("", response_model=list[EnquiryRead])
def list_enquiries(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Enquiry).order_by(Enquiry.created_at.desc())
    if user.role != "admin":
        query = query.where(Enquiry.patient_id == user.id)
    return db.scalars(query).all()


@router.get("/{enquiry_id}", response_model=EnquiryRead)
def get_enquiry(enquiry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enquiry = db.get(Enquiry, enquiry_id)
    if enquiry is None or (user.role != "admin" and enquiry.patient_id != user.id):
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


@router.patch("/{enquiry_id}", response_model=EnquiryRead)
def update_enquiry(
    enquiry_id: int,
    payload: EnquiryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enquiry = db.get(Enquiry, enquiry_id)
    if enquiry is None or user.role != "admin":
        raise HTTPException(status_code=404, detail="Enquiry not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(enquiry, key, value.strip() if isinstance(value, str) and key in {"subject", "message"} else value)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.delete("/{enquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enquiry(enquiry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enquiry = db.get(Enquiry, enquiry_id)
    if enquiry is None or (user.role != "admin" and enquiry.patient_id != user.id):
        raise HTTPException(status_code=404, detail="Enquiry not found")
    db.delete(enquiry)
    db.commit()
