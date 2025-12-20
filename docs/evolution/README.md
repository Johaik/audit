# Project Evolution

This document tracks the high-level evolution of the Audit Service, mapping code changes and migrations to business requirements and architectural shifts.

## Phase 1: Inception & Core Schema
**Goal:** Establish a basic audit logging capability.

*   **Initial Schema:** Created basic tables for `events`.
*   **Tech Stack:** FastAPI + SQLAlchemy selected for async performance and strong typing.

## Phase 2: Multi-Tenancy & Security Hardening
**Goal:** Support multiple clients (tenants) securely in a shared database.

*   **Migration:** `add_tenants_and_rls`
*   **Change:**
    *   Introduced `Tenant` entity.
    *   Added `tenant_id` column to all major tables.
    *   **Major Architecture Shift:** Enabled PostgreSQL Row Level Security (RLS).
    *   Created the `audit_app` database user with restricted permissions (cannot bypass RLS).
*   **Reasoning:** To ensure strict data isolation between tenants without the operational overhead of managing separate databases per tenant.

## Phase 3: Schema Refinement
**Goal:** Align data model with specific querying requirements.

*   **Migration:** `align_schema_with_requirements`
*   **Change:**
    *   Refined `Event` model to include `actor_kind`, `actor_id`, and flexible `payload` (JSONB).
    *   Introduced `EventEntity` for polymorphic lookups (allowing queries like "find all events related to User X" regardless of whether they were the actor or the target).
    *   Added `idempotency_key` to prevent duplicate processing.

## Current State
The system is now a fully functional, multi-tenant audit service with:
*   **RLS-enforced isolation.**
*   **Keycloak-integrated authentication.**
*   **Optimized querying** via `EventEntity` mapping.

## Future Roadmap
For details on upcoming strategies for scaling and performance, see [Future Scaling and Performance Strategies](future-scaling-and-performance.md).
