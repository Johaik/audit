from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class Actor(BaseModel):
    kind: str
    id: str

class Entity(BaseModel):
    kind: str
    id: str

class EntityRead(BaseModel):
    kind: str = Field(validation_alias="entity_kind")
    id: str = Field(validation_alias="entity_id")

    class Config:
        from_attributes = True

class Trace(BaseModel):
    trace_id: str
    request_id: str

class EventBase(BaseModel):
    type: str
    actor: Actor
    entities: List[Entity]
    trace: Optional[Trace] = None
    payload: Dict[str, Any]
    occurred_at: datetime

class EventCreate(EventBase):
    idempotency_key: str

class EventRead(EventBase):
    event_id: UUID
    tenant_id: str
    ingested_at: datetime
    idempotency_key: str
    entities: List[EntityRead] # Use EntityRead for output to handle DB mapping

    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    events: List[EventRead]
    next_cursor: Optional[str] = None
