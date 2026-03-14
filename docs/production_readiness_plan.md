# Production Readiness & Evolution Strategy: Audit Service

This document outlines the strategic roadmap to transform the Audit API into a world-class, production-grade service. It covers architecture, observability, security, testing, and lifecycle management.

---

## 1. System Architecture & Scalability

### 1.1 Asynchronous Ingestion (Decoupling)
Currently, ingestion is synchronous (HTTP -> DB). To handle high throughput and traffic spikes:
- **Broker-Based Ingestion:** Introduce **Apache Kafka** or **RabbitMQ**. The API validates the request and pushes to the broker, returning `202 Accepted`.
- **Worker Pool:** Use background workers (e.g., Celery or Go/Rust consumers) to batch-insert events into PostgreSQL. This significantly reduces p99 latency for producers.

### 1.2 Database Optimization
Audit logs grow infinitely; a single table will eventually degrade.
- **Table Partitioning:** Implement **PostgreSQL Declarative Partitioning** on `events` and `event_entities` by `occurred_at` (e.g., monthly partitions).
- **Partition Management:** Use `pg_partman` to automate the creation and maintenance of partitions.
- **Cold Storage Offloading:** Develop a lifecycle worker to move partitions older than 90 days to **S3 (Parquet format)**. Provide an async Export API for historical data retrieval.

---

## 2. Observability & Monitoring

### 2.1 Distributed Tracing
- **OpenTelemetry Integration:** Instrument the FastAPI application and SQLAlchemy queries.
- **Context Propagation:** Ensure the `trace_id` provided in the event payload is linked to the internal execution trace.
- **Backend:** Export traces to **Grafana Tempo** or **Jaeger**.

### 2.2 Metrics & Alerting
- **RED Metrics:** Monitor **R**ate, **E**rrors, and **D**uration for all endpoints using `prometheus-client`.
- **Business SLIs:** Track event ingestion lag (time between `occurred_at` and `ingested_at`) and tenant-specific throughput.
- **Alerting:** Set up Grafana alerts for elevated 4xx/5xx rates and high database CPU/IOPS.

### 2.3 Structured Logging
- Implement JSON logging via `structlog`. Ensure every log entry includes `tenant_id`, `request_id`, and `trace_id` for easy correlation in **Loki** or **ELK**.

---

## 3. Security & Resilience

### 3.1 Multi-Tenant Isolation
- **RLS Audit:** Perform regular security audits on PostgreSQL Row-Level Security (RLS) policies.
- **Leakage Testing:** Implement specialized integration tests that attempt cross-tenant data access to verify RLS enforcement.

### 3.2 Traffic Management
- **Per-Tenant Rate Limiting:** Implement rate limiting (Token Bucket) at the API Gateway or application level (using Redis) to prevent one tenant from impacting service availability.
- **Circuit Breakers:** Implement circuit breakers for downstream dependencies like Keycloak.

### 3.3 Auth Hardening
- **M2M Support:** Add support for hashed API Keys (stored in DB) alongside JWTs for machine-to-machine ingestion.
- **Token Caching:** Cache OIDC metadata and public keys to minimize latency on JWT validation.

---

## 4. Testing Strategy

### 4.1 The Testing Pyramid
- **Unit Tests:** High coverage of utility functions (e.g., hashing, cursor parsing).
- **Integration Tests:** Use `Testcontainers` for real PostgreSQL and Keycloak testing in CI.
- **Contract Testing:** Use Pact to ensure consumers of the Audit API (other services) don't break when the schema evolves.

### 4.2 Performance & Scale
- **Continuous Benchmarking:** Run Locust load tests in the CI/CD pipeline. Fail builds on performance regressions.
- **Volume Testing:** Maintain a "Scale Environment" with 100M+ events to validate index performance and query plans (`EXPLAIN ANALYZE`).

---

## 5. Deployment & Infrastructure

### 5.1 Infrastructure as Code (IaC)
- Manage all resources (RDS, Redis, EKS/ECS, S3) using **Terraform** or **Pulumi**.
- Standardize environment configurations (Dev, Staging, Prod).

### 5.2 CI/CD Pipeline
1. **Static Analysis:** Ruff (linting), Bandit (security), MyPy (types).
2. **Automated Testing:** Run integration suite against ephemeral DBs.
3. **Containerization:** Build and scan Docker images for vulnerabilities.
4. **Blue/Green Deployment:** Use zero-downtime deployment strategies.

---

## 6. Immediate Quick Wins

1. **Refactor Idempotency:** Replace nested savepoint logic with `INSERT ... ON CONFLICT` for better performance.
2. **Connection Pooling Tuning:** Fine-tune `asyncpg` pool size and timeouts for production loads.
3. **Health Checks:** Enhance `/health` to include database connectivity and broker heartbeat checks.
