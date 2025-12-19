from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Event, EventEntity
from app.schemas import EventCreate, EventRead, TimelineResponse
from app.api.deps import get_current_tenant

router = APIRouter()

@router.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    # Idempotency check
    query = select(Event).options(selectinload(Event.entities)).where(
        Event.tenant_id == tenant_id,
        Event.idempotency_key == event_in.idempotency_key
    )
    result = await db.execute(query)
    existing_event = result.scalar_one_or_none()

    if existing_event:
        # Check if payloads match (simplified check)
        if existing_event.type != event_in.type or \
           existing_event.actor != event_in.actor.model_dump() or \
           existing_event.payload != event_in.payload:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key exists but body does not match"
            )
        
        response.status_code = status.HTTP_200_OK
        return existing_event

    # Create new event
    new_event = Event(
        tenant_id=tenant_id,
        occurred_at=event_in.occurred_at,
        type=event_in.type,
        actor=event_in.actor.model_dump(),
        trace=event_in.trace.model_dump() if event_in.trace else None,
        payload=event_in.payload,
        idempotency_key=event_in.idempotency_key
    )
    
    db.add(new_event)
    
    # We flush to get the event_id before creating entities
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Race condition handling for idempotency
        query = select(Event).options(selectinload(Event.entities)).where(
            Event.tenant_id == tenant_id,
            Event.idempotency_key == event_in.idempotency_key
        )
        result = await db.execute(query)
        existing_event = result.scalar_one_or_none()
        if existing_event:
             response.status_code = status.HTTP_200_OK
             return existing_event
        raise HTTPException(status_code=400, detail="Could not create event")

    # Create event entities
    for entity in event_in.entities:
        db.add(EventEntity(
            event_id=new_event.event_id,
            entity_kind=entity.kind,
            entity_id=entity.id
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

    query = (
        select(Event)
        .options(selectinload(Event.entities))
        .join(EventEntity, Event.event_id == EventEntity.event_id)
        .where(
            Event.tenant_id == tenant_id,
            EventEntity.entity_kind == kind,
            EventEntity.entity_id == entity_id
        )
        .order_by(desc(Event.occurred_at))
        .limit(limit)
    )
    
    if cursor:
        try:
            # Simple cursor implementation using occurred_at timestamp
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
        # Assuming actor is stored as JSONB, we can query by id inside actor object
        query = query.where(Event.actor['id'].astext == actor_id)

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
