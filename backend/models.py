import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base


class Thread(Base):
    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    media_refs = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("Thread", back_populates="messages")
