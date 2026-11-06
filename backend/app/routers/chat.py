import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, Message, User, utcnow
from app.schemas import AskRequest, ConversationCreate, ConversationRead, MessageRead
from app.services.documents import answer_question

router = APIRouter(prefix="/chat", tags=["AI assistant"])


def _owned_conversation(conversation_id: int, user: User, db: Session) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.patient_id == user.id)
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _message_read(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        sources=json.loads(message.sources) if message.sources else [],
        created_at=message.created_at,
    )


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = Conversation(patient_id=user.id, title=payload.title.strip())
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Conversation).where(Conversation.patient_id == user.id).order_by(Conversation.updated_at.desc())
    ).all()


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def get_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _owned_conversation(conversation_id, user, db)
    return [_message_read(message) for message in sorted(conversation.messages, key=lambda message: message.id)]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
    status_code=status.HTTP_201_CREATED,
)
def ask(
    conversation_id: int,
    payload: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _owned_conversation(conversation_id, user, db)
    history = [
        (message.role, message.content)
        for message in sorted(conversation.messages, key=lambda message: message.id)
        if message.role in {"user", "assistant"}
    ]
    user_message = Message(conversation_id=conversation.id, role="user", content=payload.question.strip())
    db.add(user_message)
    conversation.updated_at = utcnow()
    db.commit()
    db.refresh(user_message)
    try:
        answer, sources = answer_question(payload.question.strip(), history=history)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources),
    )
    db.add(assistant_message)
    conversation.updated_at = utcnow()
    db.commit()
    db.refresh(assistant_message)
    return [_message_read(user_message), _message_read(assistant_message)]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _owned_conversation(conversation_id, user, db)
    db.delete(conversation)
    db.commit()
