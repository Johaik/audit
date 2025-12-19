import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, JSON, Integer, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    type = Column(String, nullable=False)
    actor_kind = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    trace = Column(JSONB, nullable=True)
    idempotency_key = Column(String, nullable=False)
    hash = Column(String, nullable=False)

    # Relationship to entities
    entities = relationship("EventEntity", back_populates="event", cascade="all, delete-orphan")

    @property
    def actor(self):
        return {"kind": self.actor_kind, "id": self.actor_id}

    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_tenant_idempotency'),
        Index('ix_events_tenant_occurred_event', 'tenant_id', text('occurred_at DESC'), text('event_id DESC')),
        Index('ix_events_tenant_type_occurred', 'tenant_id', 'type', text('occurred_at DESC')),
    )

class EventEntity(Base):
    __tablename__ = "event_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.event_id"), nullable=False)
    entity_kind = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)

    event = relationship("Event", back_populates="entities")

    __table_args__ = (
        Index('ix_event_entities_query_accel', 'tenant_id', 'entity_kind', 'entity_id', text('occurred_at DESC'), text('event_id DESC')),
    )
