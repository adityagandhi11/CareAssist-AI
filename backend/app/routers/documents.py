from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import KnowledgeDocument, User
from app.schemas import DocumentRead, DocumentSummary
from app.services.documents import (
    delete_document_vectors,
    process_document,
    summarize_document,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["knowledge documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return await upload_document(file, admin, db)


@router.get("", response_model=list[DocumentRead])
def list_documents(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()


@router.get("/{document_id}/summary", response_model=DocumentSummary)
def summarize(
    document_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    summary, source_pages = summarize_document(document)
    return DocumentSummary(
        document_id=document.id,
        filename=document.filename,
        summary=summary,
        source_pages=source_pages,
    )


@router.post("/{document_id}/process", response_model=DocumentRead)
def process(
    document_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        process_document(document)
        document.status = "processed"
        document.processing_error = None
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:
        document.status = "failed"
        document.processing_error = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status == "processed":
        try:
            delete_document_vectors(document.id)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(document)
    db.commit()
