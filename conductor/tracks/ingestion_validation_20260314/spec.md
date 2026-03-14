# Specification: Enhance Ingestion Validation with Schema Enforcement

## 1. Overview
This track aims to improve the data integrity of the Audit Service by enforcing stricter schema validation for all incoming events. We will refine our Pydantic schemas and update the ingestion logic to ensure that every event meets our high standards for compliance and auditability.

## 2. Goals
*   **Stricter Validation:** Implement regex patterns and value range checks for all incoming fields (e.g., `occurred_at`, `actor_id`, `resource_id`).
*   **Consistent Error Handling:** Ensure that validation errors are returned in a clear, consistent format to the client services.
*   **Comprehensive Testing:** Add a suite of tests that cover various edge cases and invalid payloads to prevent regressions.

## 3. Scope
*   **Schemas:** Refine existing schemas in `app/schemas/common.py` and `app/schemas/admin.py`.
*   **Ingestion Logic:** Update `app/api/endpoints.py` to ensure it's using the latest schemas for validation.
*   **Tests:** Create a new test file `tests/test_ingestion_validation.py` to cover the new validation logic.

## 4. Technical Approach
*   **Pydantic V2:** Utilize the latest features of Pydantic V2 for efficient and expressive validation.
*   **Schema Refinement:** 
    *   Add regex for `id` fields (e.g., `^[a-zA-Z0-9_\-]+$`).
    *   Ensure `occurred_at` is always in a valid ISO-8601 format.
    *   Add constraints for `kind` and `type` fields to prevent arbitrary strings.
*   **TDD Workflow:** Follow the project's TDD workflow: Write tests first, then implement the changes.

## 5. Verification Plan
*   **Unit Tests:** Run all new unit tests in `tests/test_ingestion_validation.py`.
*   **Integration Tests:** Run existing ingestion tests in `tests/test_api.py` to ensure no regressions.
*   **Manual Verification:** Manually verify with a few sample payloads using `curl` or a REST client.
