# Polymorphic Indexing Strategy

**Date:** 2025-12-26

## Context
A core requirement of the Audit Service is to answer questions like:
*   "Show me all actions performed by User 123"
*   "Show me all actions performed *on* Document 456"
*   "Show me all changes to Organization 789"

The `payload` of an event is arbitrary JSON. Indexing deep into a JSONB column for every possible field is inefficient and requires knowing the schema in advance.

## Decision
I implemented a **Normalized `event_entities` Table**.

Instead of searching the JSON payload, I extract "entities" (Actor, Target, Resource, etc.) at ingestion time and store them in a separate table:

```sql
CREATE TABLE event_entities (
    event_id UUID,
    entity_kind VARCHAR,  -- e.g., "user", "file", "org"
    entity_id VARCHAR,    -- e.g., "123", "path/to/file"
    ...
);
```

## Rationale
1.  **Generic Lookup:** I can index `(entity_kind, entity_id)` to find *any* event related to that object in milliseconds, regardless of where it appeared in the payload.
2.  **Write Efficiency:** Writing a few extra rows to this table is cheap compared to the cost of scanning a large JSONB table.
3.  **Flexibility:** Clients can tag events with any number of related entities.
