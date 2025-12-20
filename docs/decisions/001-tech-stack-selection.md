# Tech Stack Selection

**Date:** 2025-12-26

## Context
I needed to pick a backend tech stack for the Audit Service that offered high ingestion performance, strong Postgres support, and rapid development. My Python expertise meant I could deliver faster and more effectively than with other languages.

## Alternatives Considered

1.  **Go (Golang):**
    *   *Pros:* Excellent performance, static binary, strong concurrency.
    *   *Cons:* Verbose error handling, ORM ecosystem (e.g., GORM, Ent) is different from my existing expertise, dynamic JSON handling (crucial for arbitrary audit payloads) can be more boilerplate-heavy.

2.  **Node.js (TypeScript):**
    *   *Pros:* Great JSON handling, huge ecosystem.
    *   *Cons:* Single-threaded event loop can be blocked by CPU-intensive tasks (like hashing large payloads), though worker threads mitigate this.

3.  **Python (FastAPI):**
    *   *Pros:* `FastAPI` offers high performance (Starlette/Pydantic) comparable to Node/Go for I/O bound tasks. Excellent SQLAlchemy ecosystem for complex SQL generation (vital for RLS and polymorphic queries). Native JSON support is first-class.
    *   *Cons:* Global Interpreter Lock (GIL), though less of an issue for I/O bound services.

## Decision
I chose **Python with FastAPI**.

## Rationale
*   **SQLAlchemy 2.0:** The ability to drop down to raw SQL constructs while maintaining composability is unmatched. Support for Postgres-specific features (JSONB, Arrays, UUIDs) is mature.
*   **Pydantic:** Automatic data validation and schema generation (OpenAPI) dramatically speeds up API development.
*   **Async/Await:** Modern Python async support handles the high-concurrency ingestion requirements well.
*   **Team Velocity:** Python allows for very concise code, enabling rapid iteration on features like the complex entity filtering logic.
