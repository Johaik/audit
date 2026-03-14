# Implementation Plan: Enhance Ingestion Validation with Schema Enforcement

## Phase 1: Preparation & Schema Refinement [checkpoint: 1923890]
- [x] **Task: Write Tests for Schema Validation** [3958d75]
    - [x] Create `tests/test_ingestion_validation.py`.
    - [x] Define test cases for invalid IDs (e.g., containing special characters).
    - [x] Define test cases for invalid date formats.
    - [x] Define test cases for missing required fields in the payload.
- [x] **Task: Refine Pydantic Schemas** [6472cc9]
    - [x] Update `app/schemas/common.py` with stricter validation patterns.
    - [x] Add regex for all ID fields.
    - [x] Ensure `occurred_at` uses Pydantic's `datetime` type for automatic validation.
    - [x] Run the new tests and verify they pass.
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Preparation & Schema Refinement' (Protocol in workflow.md)** [checkpoint: 1923890]

## Phase 2: API Integration & Final Verification
- [x] **Task: Update Ingestion Route** [26b20b1]
    - [x] Review `app/api/endpoints.py` to ensure it's using the refined schemas.
    - [x] Update any manual validation logic that is now handled by Pydantic.
- [x] **Task: Run Full Test Suite** [5ec7186]
    - [x] Run all unit tests: `pytest tests/test_ingestion_validation.py`.
    - [x] Run existing integration tests: `pytest tests/test_api.py`.
    - [x] Ensure all tests pass.
- [~] **Task: Conductor - User Manual Verification 'Phase 2: API Integration & Final Verification' (Protocol in workflow.md)**
