# Specification: Production Readiness - Immediate Quick Wins

## 1. Overview
This track implements the "Immediate Quick Wins" from the Production Readiness & Evolution Strategy. It focuses on improving the performance, observability, and reliability of the Audit Service through targeted refactors and initial infrastructure scaffolding.

## 2. Goals
*   **Optimize Ingestion Performance:** Refactor idempotency logic for all models to use more efficient database operations.
*   **Enhance System Reliability:** Tune database connection pooling and implement robust health checks.
*   **Foundational Observability:** Set up structured logging and basic distributed tracing for improved system visibility.

## 3. Scope
*   **Idempotency Refactor:** Replace nested savepoint logic in `app/api/utils.py` and relevant model logic with `INSERT ... ON CONFLICT` for all models using `idempotency_key`.
*   **Database Tuning:** Configure `asyncpg` connection pooling in `app/database.py` with high-performance defaults.
*   **Health Monitoring:** Enhance the `/health` endpoint in `app/main.py` or a dedicated router to return detailed status (latency, heartbeat) for PostgreSQL and Keycloak.
*   **Observability Scaffolding:** 
    *   Integrate `structlog` for structured JSON logging.
    *   Implement initial OpenTelemetry scaffolding for FastAPI and SQLAlchemy.

## 4. Technical Approach
*   **SQLAlchemy Async:** Utilize `insert().on_conflict_do_nothing()` or similar for idempotency.
*   **Async Health Checks:** Implement concurrent health checks for all external dependencies to minimize latency.
*   **OpenTelemetry:** Use `opentelemetry-instrumentation-fastapi` and `opentelemetry-instrumentation-sqlalchemy` for automatic instrumentation.
*   **Structured Logging:** Configure `structlog` to output JSON in production and pretty-printed logs in development.

## 5. Acceptance Criteria
*   [ ] All models utilizing `idempotency_key` have been refactored to use `ON CONFLICT` logic.
*   [ ] Database connection pooling is configured with explicit, optimized settings.
*   [ ] `/health` endpoint returns a detailed JSON response including component-specific health metrics and overall system status.
*   [ ] All application logs are output in structured JSON format via `structlog`.
*   [ ] Basic distributed traces are generated and accessible (exported to OTLP).

## 6. Out of Scope
*   Implementation of message brokers (Kafka/RabbitMQ).
*   Database partitioning or cold storage offloading.
*   Advanced traffic management (rate limiting, circuit breakers).
