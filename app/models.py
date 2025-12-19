import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, JSON, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    type = Column(String, nullable=False)
    actor = Column(JSONB, nullable=False)
    trace = Column(JSONB, nullable=True)
    payload = Column(JSONB, nullable=False)
    idempotency_key = Column(String, nullable=False)

    # Relationship to entities
    entities = relationship("EventEntity", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_tenant_idempotency'),
    )

class EventEntity(Base):
    __tablename__ = "event_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False)
    entity_kind = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)

    event = relationship("Event", back_populates="entities")

    __table_args__ = (
        Index('ix_event_entities_kind_id', 'entity_kind', 'entity_id'),
    )
