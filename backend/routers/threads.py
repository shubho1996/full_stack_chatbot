from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Message, Thread
from schemas import (
    MessageCreate,
    MessageResponse,
    SendMessageResponse,
    ThreadCreate,
    ThreadResponse,
)

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", response_model=ThreadResponse, status_code=201)
def create_thread(body: ThreadCreate, db: Session = Depends(get_db)):
    thread = Thread(title=body.title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.get("", response_model=List[ThreadResponse])
def list_threads(db: Session = Depends(get_db)):
    return db.query(Thread).order_by(Thread.updated_at.desc()).all()


@router.get("/{thread_id}/messages", response_model=List[MessageResponse])
def get_messages(thread_id: UUID, db: Session = Depends(get_db)):
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.messages


@router.post("/{thread_id}/messages", response_model=SendMessageResponse)
def send_message(thread_id: UUID, body: MessageCreate, db: Session = Depends(get_db)):
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    is_first = db.query(Message).filter(Message.thread_id == thread_id).count() == 0
    if is_first and thread.title == "New Chat":
        thread.title = body.content[:50]

    user_msg = Message(thread_id=thread_id, role="user", content=body.content)
    db.add(user_msg)

    assistant_msg = Message(
        thread_id=thread_id,
        role="assistant",
        content=f"Echo: {body.content}",
    )
    db.add(assistant_msg)

    thread.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return {"user_message": user_msg, "assistant_message": assistant_msg}
