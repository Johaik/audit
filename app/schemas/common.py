from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

ID_REGEX = r"^[a-zA-Z0-9_\-]+$"

class Actor(BaseModel):
    kind: str = Field(..., min_length=1, pattern=ID_REGEX)
    id: str = Field(..., min_length=1, pattern=ID_REGEX)

class Entity(BaseModel):
    kind: str = Field(..., min_length=1, pattern=ID_REGEX)
    id: str = Field(..., min_length=1, pattern=ID_REGEX)

class EntityRead(BaseModel):
    kind: str = Field(validation_alias="entity_kind", pattern=ID_REGEX)
    id: str = Field(validation_alias="entity_id", pattern=ID_REGEX)

    class Config:
        from_attributes = True

class Trace(BaseModel):
    trace_id: str = Field(..., pattern=ID_REGEX)
    request_id: str = Field(..., pattern=ID_REGEX)

class EventBase(BaseModel):
    type: str = Field(..., min_length=1, pattern=r"^[a-zA-Z0-9_\-\.]+$")
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
