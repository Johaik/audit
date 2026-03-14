# Tech Stack: Audit Service

## 1. Programming Languages
*   **Python 3.10+:** The primary language for API development, chosen for its asynchronous support (FastAPI) and rich ecosystem.

## 2. Backend Infrastructure
*   **FastAPI:** High-performance web framework for building APIs with Python.
*   **Uvicorn:** A lightning-fast ASGI server implementation for Python.

## 3. Storage & Data Management
*   **PostgreSQL 15+:** Robust relational database with advanced features like Row Level Security (RLS) for multi-tenancy.
*   **SQLAlchemy (AsyncPG):** The Python SQL Toolkit and Object Relational Mapper (ORM) with asynchronous database drivers.
*   **Alembic:** Lightweight database migration tool for SQLAlchemy.

## 4. Authentication & Security
*   **Keycloak (OIDC):** Open Source Identity and Access Management for managing tenant identities and issuing tokens.
*   **PyJWT:** Library for encoding, decoding, and verifying JSON Web Tokens (JWT).

## 5. Development & Testing
*   **Pytest:** Mature, full-featured Python testing tool for unit and integration tests.
*   **Pytest-Asyncio:** Pytest plugin for testing asynchronous code.
*   **HTTPX:** A next-generation HTTP client for Python, used for API testing.
*   **Docker & Docker Compose:** Containerization for consistent local development and production environments.
*   **structlog:** Structured JSON logging for production observability.
*   **OpenTelemetry:** Distributed tracing and metrics for system-wide visibility.
