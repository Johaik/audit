# ADLC Branch Protection Strategy

To maintain the integrity of the Agentic Development Life Cycle (ADLC), the following branch protection rules should be configured for the `master` branch in GitHub.

## 1. Required Status Checks
The following status checks must pass before a pull request can be merged:
*   **`adlc`**: This is the primary Agentic Development Life Cycle workflow. It ensures that:
    *   All unit and integration tests pass.
    *   Code coverage is above 80%.
    *   Dependency security scans (`pip-audit`) are clean.
    *   Jules security analysis has been initiated.

## 2. PR Requirements
*   **Require a pull request before merging:** All changes must be submitted via a PR.
*   **Require approvals:** At least one approval from a designated reviewer is recommended.
*   **Dismiss stale pull request approvals when new commits are pushed:** Ensures that every change is reviewed.

## 3. Jules Integration
*   The ADLC pipeline automatically invokes **Google Jules** for security analysis, test maintenance, and auto-remediation.
*   Failures in the `adlc` workflow will trigger a Jules auto-remediation session to attempt a fix.

## 4. Automation & Compliance
*   Scheduled nightly runs perform deep regression and security scans.
*   Weekly runs ensure all dependencies are up-to-date and free of known vulnerabilities.
