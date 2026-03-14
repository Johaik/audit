# Implementation Plan: Agentic CI & Linear Integration with Google Jules

## Phase 1: CI Failure-to-Issue Automation

- [x] **Task: Implement CI Failure Detection & Issue Generation Script**
  - [x] Create `scripts/adlc/create_gh_issue_on_failure.py`.
  - [x] Implement robust deduplication logic matching by Error Signature and Test Case.
  - [x] Integrate GitHub API for issue creation with Labels (`bug`, `adlc-auto-remediation`).
  - [x] Add support for embedding full logs, Run URL, Changed Files, and initial AI-Analysis in the issue body.
- [x] **Task: Update CI Workflow to Trigger Issue Creation**
  - [x] Modify `.github/workflows/adlc-ci.yml` to call the creation script on `ci` job failure.
  - [x] Ensure required secrets (`GH_TOKEN`) are available to the script.
- [x] **Task: Conductor - User Manual Verification 'Phase 1: CI Failure-to-Issue Automation' (Protocol in workflow.md)**

## Phase 2: Jules-Linear-GitHub Synchronization

- [x] **Task: Configure Jules Analysis Workflow (Initial Stage)**
  - [x] Define a specialized Jules task that monitors GitHub issues with the `adlc-auto-remediation` label.
  - [x] Implement Linear synchronization logic using Jules' MCP integration.
  - [x] Ensure the Linear issue includes a back-link to the GitHub issue and initial analysis data.
- [x] **Task: Implement Jules-to-Linear-Sync Metadata Update**
  - [x] Update the GitHub issue with a "Linear Task Created" comment and metadata once synchronization is complete.
- [x] **Task: Conductor - User Manual Verification 'Phase 2: Jules-Linear-GitHub Synchronization' (Protocol in workflow.md)**

## Phase 3: Automated Remediation & PR Handling

- [x] **Task: Configure Jules Remediation Workflow (Execution Stage)**
  - [x] Define a second Jules task to pull synchronized issues and attempt an automated fix.
  - [x] Implement logic to run the failed tests locally to verify the fix.
  - [x] Ensure Jules pushes the fix to a new branch and creates a PR.
- [x] **Task: Link PR to Original GitHub Issue**
  - [x] Add a comment to the GitHub issue with the PR link once created.
  - [x] Verify that merging the PR closes the GitHub issue and moves the Linear task to 'Done'.

## Phase: Review Fixes
- [x] Task: Apply review suggestions 5698877
