import os
import sys
import json
import httpx
from datetime import datetime

# Configuration from Environment Variables
GITHUB_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID")
GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL", "https://github.com")
GITHUB_SHA = os.getenv("GITHUB_SHA")

API_BASE = f"https://api.github.com/repos/{GITHUB_REPOSITORY}"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_failed_logs():
    """Fetches the logs of the current run's failed jobs.

    Returns:
        A concatenated string of all failure logs, or an empty string if none.
    """
    # Try reading from a local file first (if tee-ed in CI)
    if os.path.exists("full_log.txt"):
        with open("full_log.txt", "r") as f:
            return f.read()

    # Fallback to API if not available locally
    url = f"{API_BASE}/actions/runs/{GITHUB_RUN_ID}/jobs"
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return ""
    
    failed_logs = []
    for job in jobs:
        if job["conclusion"] == "failure":
            job_id = job["id"]
            log_url = f"{API_BASE}/actions/jobs/{job_id}/logs"
            log_response = httpx.get(log_url, headers=headers)
            if log_response.status_code == 200:
                failed_logs.append(f"--- Logs for Job: {job['name']} ---\n{log_response.text}")
    
    return "\n\n".join(failed_logs)

def get_changed_files():
    """Returns a list of files changed in the triggering commit.

    Returns:
        A list of filename strings.
    """
    # We can use the commit API
    url = f"{API_BASE}/commits/{GITHUB_SHA}"
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    files = [f["filename"] for f in response.json().get("files", [])]
    return files

def find_existing_issue(signature):
    """Checks for an open issue with the same signature in the title or labels.

    Args:
        signature: The unique failure signature string to search for.

    Returns:
        The first matching issue object if found, else None.
    """
    query = f"repo:{GITHUB_REPOSITORY} is:issue is:open \"{signature}\""
    url = f"https://api.github.com/search/issues?q={query}"
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    items = response.json().get("items", [])
    return items[0] if items else None

def create_issue(title, body, labels):
    """Creates a new GitHub issue in the repository.

    Args:
        title: The title of the issue.
        body: The detailed description of the failure.
        labels: A list of labels to apply to the issue.

    Returns:
        The created issue object from the GitHub API.
    """
    url = f"{API_BASE}/issues"
    data = {
        "title": title,
        "body": body,
        "labels": labels
    }
    response = httpx.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def main():
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not found.")
        sys.exit(1)
    
    print(f"Analyzing CI failure for run {GITHUB_RUN_ID} in {GITHUB_REPOSITORY}...")
    
    # Simple signature: failing run ID for now, but better would be the test name.
    # In a real scenario, we'd parse the logs to find the exact failed test.
    # Let's try to parse logs for 'FAILED tests/test_...'
    
    logs = get_failed_logs()
    
    # Find failure signature (e.g. FAILED tests/test_api.py::test_create_audit)
    import re
    failures = re.findall(r"FAILED\s+(tests/[^\s:]+::[^\s]+)", logs)
    
    if not failures:
        # Fallback if we can't parse specific test failures
        signature = f"CI Failure in {GITHUB_SHA[:7]}"
    else:
        signature = f"Failure in {failures[0]}"
    
    existing_issue = find_existing_issue(signature)
    if existing_issue:
        print(f"Found existing issue: {existing_issue['html_url']}")
        return

    changed_files = get_changed_files()
    run_url = f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"
    
    issue_title = f"[ADLC] {signature}"
    issue_body = f"""## CI Failure Detected

**Failed Test/Check:** `{signature}`
**Run URL:** {run_url}
**Triggering Commit:** {GITHUB_SHA}

### Changed Files in this Commit:
{chr(10).join(f"- {f}" for f in changed_files)}

### Failure Logs Snippet:
```text
{logs[-2000:] if logs else "Logs could not be retrieved or are too large."}
```

---
*This issue was automatically created by the ADLC CI Failure-to-Issue Automation.*
"""
    labels = ["bug", "adlc-auto-remediation"]
    
    new_issue = create_issue(issue_title, issue_body, labels)
    print(f"Created new issue: {new_issue['html_url']}")
    
    # Output issue number for GitHub Actions
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write(f"issue_number={new_issue['number']}\n")
            f.write(f"issue_url={new_issue['html_url']}\n")

if __name__ == "__main__":
    main()
