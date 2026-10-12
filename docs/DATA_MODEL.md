# DevPilot Data Model & State Architecture

This document describes every data type and state field in DevPilot, what they represent, and which node writes them.

## The Pipeline Map

Each run turns a GitHub issue into a verified Pull Request through a central LangGraph state (`DevPilotState`).
Read the table from top to bottom to follow how data flows through the application:

| Step | What it reads from state | What it writes to state | Data Type | Purpose |
|---|---|---|---|---|
| **Issue Node** | `issue_url`, `github_token` | `issue`, `workspace` | `GitHubIssue`, `WorkspaceInfo` | Ingests issue details from GitHub MCP and clones repository in sandbox |
| **Planner Agent** | `issue`, `plan_feedback` | `plan` | `ImplementationPlan` | Explores repo using read-only tools and designs proposed changes |
| **Human Checkpoint 1** | `plan` | `plan_decision`, `plan_feedback` | `Decision` (`'approve'`, `'revise'`, `'reject'`) | Developer reviews and approves the plan before code is written |
| **Implementer Agent** | `issue`, `plan`, `qa_feedback` | `branch_name`, `implementation_report` | `str`, `ImplementationReport` | Creates working branch, modifies files, and runs local test checks |
| **Testing Node** | `workspace` | `test_result` | `TestResult` | Runs test and lint commands inside sandbox (`pytest`, `ruff`, etc.) |
| **Reviewer Subgraph** | `issue`, `plan`, `branch_name`, `workspace` | `review_result` | `ReviewResult` | 4 parallel specialist reviewers (Security, Requirement, Code Quality, Edge Case) |
| **QA Node** | `test_result`, `review_result` | `qa_status`, `qa_feedback` | `QAStatus` (`'passed'`, `'fix_required'`, `'retry_limit_reached'`) | Evaluates whether repair is required or workflow can proceed |
| **Human Checkpoint 2** | `implementation_report`, `review_result` | `publication_decision` | `Decision` (`'approve'`, `'revise'`, `'reject'`) | Final human-in-the-loop sign-off before publishing |
| **PR Node** | `branch_name`, `issue`, `workspace` | `pull_request_url` | `str` | Pushes branch and opens GitHub Pull Request via GitHub MCP |

---

## The 3 Kinds of Types

### 1. The Clipboard (`DevPilotState`)
Defined in `devpilot/workflow.py`. A shared `TypedDict` that nodes read from and update.

### 2. Documents (Pydantic Models)
Structured objects with schema validation.
- **Shared models** (`devpilot/models.py`):
  - `GitHubIssue`: Issue title, body, labels, repository.
  - `WorkspaceInfo`: Sandbox ID, cloned path, base branch.
  - `TestResult`: Command run, exit code, stdout/stderr.
- **Agent models** (co-located in each agent's file):
  - `ImplementationPlan` (`agents/planner/agent.py`): Problem summary, target files, proposed steps, risks.
  - `ImplementationReport` (`agents/implementer/agent.py`): Changed files, completion status, summary.
  - `Finding` & `ReviewResult` (`agents/reviewer/agent.py`): Specific code review findings and overall verdict.

### 3. Choices (`Literal` Strings)
Simple Python string literals for fixed options:
- `Decision`: `"approve" | "revise" | "reject"`
- `QAStatus`: `"passed" | "fix_required" | "retry_limit_reached"`
- `Severity`: `"critical" | "high" | "medium" | "low" | "info"`
- `Category`: `"security" | "requirement" | "code_quality" | "edge_case"`
