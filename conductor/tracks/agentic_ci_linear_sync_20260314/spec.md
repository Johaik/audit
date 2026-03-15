# Specification: Agentic CI & Linear Integration with Google Jules

## 1. Overview
This track enhances the Audit Service's **Agentic Development Life Cycle (ADLC)** by automating the full loop from CI failure to issue tracking and resolution. When the CI pipeline fails, a detailed GitHub issue will be automatically created (if one doesn't already exist). Google Jules will then analyze the issue, synchronize it with Linear for project management visibility, and attempt to resolve it by creating a pull request.

## 2. Functional Requirements

### 2.1 Automated GitHub Issue Creation
- **Trigger:** Any failure in the `ADLC - CI Pipeline`.
- **Deduplication Logic:** Before creating an issue, the system must check for existing open issues matching the **Error Signature** (error message + failed test name) or the specific **Test Case**.
- **Issue Content:**
  - **Title:** Descriptive title including the failed test/check name.
  - **Body:** 
    - Full logs of the failure.
    - URL to the failed GitHub Actions run.
    - List of files changed in the triggering commit.
    - AI-generated root cause analysis (provided by Jules or a specialized script).
- **Labels:** Automatically apply `bug` and `adlc-auto-remediation` labels.
- **Local Fallback:** The script supports local execution by falling back to `git diff HEAD~1` for changed files and "local" signatures when CI environment variables (e.g., `GITHUB_RUN_ID`, `GITHUB_SHA`) are absent.

### 2.2 Jules & Linear Synchronization
- **Trigger:** Jules will monitor GitHub issues with the `adlc-auto-remediation` label.
- **Linear Integration:** Once Jules has performed an initial analysis or attempted a fix, it will synchronize the task to **Linear** using its built-in MCP integration.
- **Linear Content:** The Linear issue should mirror the GitHub issue details and maintain a link to the original GitHub issue.

### 2.3 Automated Resolution Loop
- **Task Assignment:** Jules autonomously picks up the issue.
- **Fix Attempt:** Jules attempts to fix the code, runs tests locally, and pushes a PR.
- **Visibility:** Jules comments on the GitHub issue with a link to the generated PR.

## 3. Non-Functional Requirements
- **Efficiency:** Deduplication must be robust to prevent "flapping" or duplicate ticket spam.
- **Security:** Use GitHub (`GH_TOKEN`) and Linear tokens securely via repository secrets. Note: A custom `GH_TOKEN` is used to allow the script to trigger other workflows, overcoming limitations of the default `GITHUB_TOKEN`.
- **Observability:** Maintain clear logs of the automation steps in the GitHub Actions run.

## 4. Acceptance Criteria
- [x] CI failure triggers GitHub issue creation with all required metadata (Logs, URL, Files, Analysis).
- [x] No duplicate issues are created for the same recurring failure.
- [x] Jules successfully synchronizes the issue to Linear after initial analysis.
- [x] Jules creates a PR and links it back to the original GitHub issue.
- [x] Merging the fix automatically closes the GitHub issue and moves the Linear task to "Done".

## 5. Out of Scope
- Manual creation of Linear tasks.
- Remediation for infrastructure-level failures (e.g., runner timeouts).
