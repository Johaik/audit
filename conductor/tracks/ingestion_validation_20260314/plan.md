# Implementation Plan: Enhance Ingestion Validation with Schema Enforcement

## Phase 1: Preparation & Schema Refinement
- [ ] **Task: Write Tests for Schema Validation**
    - [ ] Create `tests/test_ingestion_validation.py`.
    - [ ] Define test cases for invalid IDs (e.g., containing special characters).
    - [ ] Define test cases for invalid date formats.
    - [ ] Define test cases for missing required fields in the payload.
- [ ] **Task: Refine Pydantic Schemas**
    - [ ] Update `app/schemas/common.py` with stricter validation patterns.
    - [ ] Add regex for all ID fields.
    - [ ] Ensure `occurred_at` uses Pydantic's `datetime` type for automatic validation.
    - [ ] Run the new tests and verify they pass.
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: Preparation & Schema Refinement' (Protocol in workflow.md)**

## Phase 2: API Integration & Final Verification
- [ ] **Task: Update Ingestion Route**
    - [ ] Review `app/api/endpoints.py` to ensure it's using the refined schemas.
    - [ ] Update any manual validation logic that is now handled by Pydantic.
- [ ] **Task: Run Full Test Suite**
    - [ ] Run all unit tests: `pytest tests/test_ingestion_validation.py`.
    - [ ] Run existing integration tests: `pytest tests/test_api.py`.
    - [ ] Ensure all tests pass.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: API Integration & Final Verification' (Protocol in workflow.md)**
