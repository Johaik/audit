# Implementation Plan: Agentic CI & Linear Integration with Google Jules

## Phase 1: CI Failure-to-Issue Automation

- [ ] **Task: Implement CI Failure Detection & Issue Generation Script**
  - [ ] Create `scripts/adlc/create_gh_issue_on_failure.py`.
  - [ ] Implement robust deduplication logic matching by Error Signature and Test Case.
  - [ ] Integrate GitHub API for issue creation with Labels (`bug`, `adlc-auto-remediation`).
  - [ ] Add support for embedding full logs, Run URL, Changed Files, and initial AI-Analysis in the issue body.
- [ ] **Task: Update CI Workflow to Trigger Issue Creation**
  - [ ] Modify `.github/workflows/adlc-ci.yml` to call the creation script on `ci` job failure.
  - [ ] Ensure required secrets (`GH_TOKEN`) are available to the script.
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: CI Failure-to-Issue Automation' (Protocol in workflow.md)**

## Phase 2: Jules-Linear-GitHub Synchronization

- [ ] **Task: Configure Jules Analysis Workflow (Initial Stage)**
  - [ ] Define a specialized Jules task that monitors GitHub issues with the `adlc-auto-remediation` label.
  - [ ] Implement Linear synchronization logic using Jules' MCP integration.
  - [ ] Ensure the Linear issue includes a back-link to the GitHub issue and initial analysis data.
- [ ] **Task: Implement Jules-to-Linear-Sync Metadata Update**
  - [ ] Update the GitHub issue with a "Linear Task Created" comment and metadata once synchronization is complete.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Jules-Linear-GitHub Synchronization' (Protocol in workflow.md)**

## Phase 3: Automated Remediation & PR Handling

- [ ] **Task: Configure Jules Remediation Workflow (Execution Stage)**
  - [ ] Define a second Jules task to pull synchronized issues and attempt an automated fix.
  - [ ] Implement logic to run the failed tests locally to verify the fix.
  - [ ] Ensure Jules pushes the fix to a new branch and creates a PR.
- [ ] **Task: Link PR to Original GitHub Issue**
  - [ ] Add a comment to the GitHub issue with the PR link once created.
  - [ ] Verify that merging the PR closes the GitHub issue and moves the Linear task to 'Done'.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Automated Remediation & PR Handling' (Protocol in workflow.md)**
