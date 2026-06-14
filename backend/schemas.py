from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel


class ThreadCreate(BaseModel):
    title: str = "New Chat"


class ThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    role: str
    content: str
    media_refs: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
