import json
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from agent import graph
from database import SessionLocal, get_db
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


@router.post("/{thread_id}/chat")
def chat(thread_id: UUID, body: MessageCreate, db: Session = Depends(get_db)):
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Build LangChain message list from DB history + new user message
    existing = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )
    lc_messages = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in existing
    ]
    lc_messages.append(HumanMessage(content=body.content))

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

        full_response = ""

        try:
            async for event in graph.astream_events(
                {"messages": lc_messages, "max_retries": 5, "retry_count": 0, "call_log": []},
                version="v2",
            ):
                kind = event["event"]
                node = event.get("metadata", {}).get("langgraph_node", "")

                # Agent LLM streaming tokens (tool-call chunks have empty
                # content and are filtered out by the `if chunk.content` guard)
                if kind == "on_chat_model_stream" and node == "agent":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        full_response += chunk.content
                        yield f"data: {json.dumps({'token': chunk.content})}\n\n"

                # Tool about to execute — just send the tool name
                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'step': 'tool_call', 'tool': event.get('name', '')})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Persist the assembled assistant message
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
