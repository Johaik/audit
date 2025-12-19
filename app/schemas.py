from pydantic import BaseModel, Field, model_validator
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
    # hash is optional in input, but we might calculate it
    hash: Optional[str] = None

class EventCreate(EventBase):
    idempotency_key: str

class EventRead(BaseModel):
    event_id: UUID
    tenant_id: str
    occurred_at: datetime
    ingested_at: datetime
    type: str
    actor_kind: str
    actor_id: str
    actor: Actor 
    
    payload: Dict[str, Any]
    trace: Optional[Dict[str, Any]] = None # Trace stored as JSONB
    idempotency_key: str
    hash: str
    entities: List[EntityRead]

    @model_validator(mode='before')
    @classmethod
    def assemble_actor(cls, data: Any) -> Any:
        return data

    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    events: List[EventRead]
    next_cursor: Optional[str] = None
