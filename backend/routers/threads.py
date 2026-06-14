import json
import os
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import Message, Thread
from schemas import (
    MessageCreate,
    MessageResponse,
    SendMessageResponse,
    ThreadCreate,
    ThreadResponse,
)

MODEL = "gpt-5.4-nano"

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


@router.post("/{thread_id}/chat")
def chat(thread_id: UUID, body: MessageCreate, db: Session = Depends(get_db)):
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Build context from existing history before saving the new message
    existing = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )
    oai_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *[{"role": m.role, "content": m.content} for m in existing],
        {"role": "user", "content": body.content},
    ]

    # Persist user message
    is_first = len(existing) == 0
    if is_first and thread.title == "New Chat":
        thread.title = body.content[:50]
    user_msg = Message(thread_id=thread_id, role="user", content=body.content)
    db.add(user_msg)
    thread.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    user_msg_id = str(user_msg.id)

    async def event_stream():
        yield f"data: {json.dumps({'user_message_id': user_msg_id})}\n\n"

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        full_response = ""

        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=oai_messages,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    yield f"data: {json.dumps({'token': delta.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Persist assistant message using a fresh session (we're inside async context)
        save_db = SessionLocal()
        try:
            assistant_msg = Message(
                thread_id=thread_id, role="assistant", content=full_response
            )
            save_db.add(assistant_msg)
            t = save_db.get(Thread, thread_id)
            if t:
                t.updated_at = datetime.utcnow()
            save_db.commit()
            save_db.refresh(assistant_msg)
            yield f"data: {json.dumps({'done': True, 'message_id': str(assistant_msg.id)})}\n\n"
        finally:
            save_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
