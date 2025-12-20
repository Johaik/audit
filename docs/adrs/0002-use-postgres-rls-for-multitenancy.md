# 2. Use PostgreSQL RLS for Multi-tenancy

Date: 2025-12-26

## Status

Accepted

## Context

The Audit Service must support multiple tenants with strict data isolation. I need to ensure that a bug in the application layer (e.g., a missing `WHERE tenant_id = ?` clause) does not result in data leakage between tenants.

## Decision

I will use **PostgreSQL Row Level Security (RLS)** to enforce multi-tenancy at the database level.

*   The application connects as a shared user (`audit_app`) which has restricted permissions.
*   For each request, the application sets a session variable (e.g., `app.tenant_id`) based on the authenticated user's tenant.
*   RLS policies on the `events` and `event_entities` tables strictly limit SELECT and INSERT operations to rows matching the current session's `tenant_id`.

## Consequences

*   **Positive:**
    *   **Defense in Depth:** Security is enforced by the database engine, providing a strong guarantee against application-layer bugs.
    *   **Simplicity:** Developers don't need to manually add tenant filters to every query; the DB handles it transparently.
*   **Negative:**
    *   **Connection Pooling Complexity:** Connection poolers like PgBouncer must be configured carefully (e.g., in session mode) to ensure session variables don't leak across requests, or the application must reset the session state explicitly (which I do).
    *   **Testing:** Requires integration tests with a real Postgres instance to verify policies work as expected.
