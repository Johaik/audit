# 4. Immutable Append-Only Log Structure

Date: 2025-12-26

## Status

Accepted

## Context

Audit logs are legally sensitive and must be tamper-evident. Once written, a log entry should not be modified. I also need to be able to verify that the log has not been altered.

## Decision

I will treat the `events` table as an **immutable, append-only log**.

*   **No Updates:** The API will not expose any endpoints to update existing events.
*   **Hashing:** Each event will include a SHA-256 hash of its content (payload + metadata) at the time of ingestion.
*   **Idempotency:** To handle retries safely without creating duplicates or modifying existing records, I will use a client-provided `idempotency_key`.

## Consequences

*   **Positive:**
    *   **Integrity:** Provides a high degree of confidence in the audit trail's validity.
    *   **Simplicity:** Read and Write patterns are simplified (no complex update logic).
*   **Negative:**
    *   **Correction Difficulty:** If a system logs incorrect data, it cannot be "fixed" in place; a compensating "correction" event must be logged instead, which is a standard audit trail practice but can be confusing for users expecting CRUD.
    *   **Storage:** Data grows indefinitely; requires an archival strategy (which is planned for future evolution).
