from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime
import uuid
import hashlib
import json

from app.database import get_db
from app.models import Event, EventEntity
from app.schemas import EventCreate, EventRead, TimelineResponse
from app.api.deps import get_current_tenant

router = APIRouter()

def calculate_hash(event_in: EventCreate) -> str:
    # Canonicalize payload for hashing
    payload_str = json.dumps(event_in.payload, sort_keys=True)
    # Include critical fields
    data = f"{event_in.occurred_at.isoformat()}|{event_in.type}|{event_in.actor.kind}|{event_in.actor.id}|{payload_str}"
    return hashlib.sha256(data.encode()).hexdigest()

@router.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    # Calculate hash if not provided
    event_hash = event_in.hash or calculate_hash(event_in)

    # Optimistic insertion (Create new event first, handle conflict later)
    new_event = Event(
        tenant_id=tenant_id,
        occurred_at=event_in.occurred_at,
        type=event_in.type,
        actor_kind=event_in.actor.kind,
        actor_id=event_in.actor.id,
        trace=event_in.trace.model_dump() if event_in.trace else None,
        payload=event_in.payload,
        idempotency_key=event_in.idempotency_key,
        hash=event_hash
    )
    
    db.add(new_event)
    
    # We flush to get the event_id before creating entities
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Race condition / Idempotency handling
        # Idempotency key exists
        query = select(Event).options(selectinload(Event.entities)).where(
            Event.tenant_id == tenant_id,
            Event.idempotency_key == event_in.idempotency_key
        )
        result = await db.execute(query)
        existing_event = result.scalar_one_or_none()
        
        if existing_event:
             # Check hash for duplicate detection
             if existing_event.hash != event_hash:
                 raise HTTPException(
                     status_code=status.HTTP_409_CONFLICT,
                     detail="Idempotency key exists but parameters do not match (hash mismatch)"
                 )
             
             response.status_code = status.HTTP_200_OK
             return existing_event
        
        # If we got IntegrityError but can't find the event, something else failed or race condition was weird
        raise HTTPException(status_code=400, detail="Could not create event")

    # Create event entities
    for entity in event_in.entities:
        db.add(EventEntity(
            tenant_id=tenant_id,
            event_id=new_event.event_id,
            entity_kind=entity.kind,
            entity_id=entity.id,
            occurred_at=event_in.occurred_at # Denormalized
        ))

    await db.commit()
    
    # Re-fetch with eager load
    query = select(Event).options(selectinload(Event.entities)).where(Event.event_id == new_event.event_id)
    result = await db.execute(query)
    final_event = result.scalar_one()
    
    return final_event

@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    entity: str = Query(..., description="Format: kind:id"),
    limit: int = Query(50, le=100),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    try:
        kind, entity_id = entity.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Entity must be in format kind:id")

    # Use EventEntity to drive the sort order efficiently using the index
    # (tenant_id, entity_kind, entity_id, occurred_at desc, event_id desc)
    
    # We select Event but join EventEntity. 
    # To strictly use the index for sorting, we should order by EventEntity.occurred_at
    query = (
        select(Event)
        .options(selectinload(Event.entities))
        .join(EventEntity, Event.event_id == EventEntity.event_id)
        .where(
            EventEntity.tenant_id == tenant_id, # Redundant but helps index usage if partition key
            EventEntity.entity_kind == kind,
            EventEntity.entity_id == entity_id
        )
        .order_by(desc(EventEntity.occurred_at), desc(EventEntity.event_id))
        .limit(limit)
    )
    
    if cursor:
        try:
            # Simple cursor implementation using occurred_at timestamp
            # Handle space replacing + (common URL decoding issue) or missing timezone logic
            # The cursor comes from isoformat(), which might be like '2025-01-01T12:00:00+00:00'
            # If passed in query param, + might become space if not encoded properly by client,
            # but usually httpx handles this. Let's be robust.
            cursor_cleaned = cursor.replace(" ", "+")
            if cursor_cleaned.endswith("Z"):
                 cursor_cleaned = cursor_cleaned.replace("Z", "+00:00")
            
            cursor_dt = datetime.fromisoformat(cursor_cleaned)
            query = query.where(EventEntity.occurred_at < cursor_dt)
        except ValueError as e:
            # Log error for debugging if needed
            print(f"Cursor parse error: {e}, cursor: {cursor}")
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    result = await db.execute(query)
    events = result.scalars().all()

    next_cursor = None
    if events and len(events) == limit:
        next_cursor = events[-1].occurred_at.isoformat()

    return TimelineResponse(events=events, next_cursor=next_cursor)

@router.get("/events/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    query = select(Event).options(selectinload(Event.entities)).where(Event.event_id == event_id, Event.tenant_id == tenant_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return event

@router.get("/events", response_model=TimelineResponse)
async def list_events(
    limit: int = Query(50, le=100),
    cursor: Optional[str] = None,
    type: Optional[str] = None,
    actor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    query = select(Event).options(selectinload(Event.entities)).where(Event.tenant_id == tenant_id).order_by(desc(Event.occurred_at)).limit(limit)
    
    if type:
        query = query.where(Event.type == type)
    
    if actor_id:
        # Now using flat column
        query = query.where(Event.actor_id == actor_id)

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(Event.occurred_at < cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    result = await db.execute(query)
    events = result.scalars().all()
    
    next_cursor = None
    if events and len(events) == limit:
        next_cursor = events[-1].occurred_at.isoformat()

    return TimelineResponse(events=events, next_cursor=next_cursor)
