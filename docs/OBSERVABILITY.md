# DevPilot Observability Specification & Metrics Guide

This document details the observability architecture implemented in DevPilot using **Langfuse**, explaining how data is captured, what metrics are monitored, how percentiles and latencies are calculated, and how to query them in the dashboard.

---

## 1. Observability Architecture Overview

DevPilot uses a **framework-native callback integration** with Langfuse (`backend/src/devpilot/observability.py`). Rather than requiring manual span decorators around every function, DevPilot hooks into LangGraph and LangChain runnables via `langfuse.langchain.CallbackHandler`.

### Architecture Flow:
```text
Workflow Run (Session: issue-{id}, Trace: devpilot-workflow)
  ├── ingest_issue_node
  ├── planner_node (Tag: "agent:planner")
  │     ├── ReAct Agent Loops
  │     ├── Tool Calls: find_files, search_code, read_file
  │     └── LLM Generations: gpt-4o (Tokens, Latency)
  ├── Human Checkpoint: Plan Review (Score: human_plan_review)
  ├── implement_node (Tag: "agent:implementer")
  │     ├── ReAct Agent Loops
  │     ├── Tool Calls: replace_in_file, bash, delegate_work
  │     │     └── Worker Subagents (Tag: "agent:worker")
  │     └── LLM Generations: gpt-4o (Tokens, Latency)
  ├── Parallel Verification:
  │     ├── test_node (Docker/E2B sandbox execution)
  │     └── reviewer_subgraph (Tags: "agent:reviewer", "reviewer:{category}")
  │           ├── Security Specialist (gpt-4o-mini)
  │           ├── Requirement Specialist (gpt-4o-mini)
  │           ├── Code Quality Specialist (gpt-4o-mini)
  │           └── Edge Case Specialist (gpt-4o-mini)
  ├── qa_node (Score: qa_verdict, Repair attempt counters)
  └── publish_pr_node (PR generation)
```

---

## 2. Metrics Captured

### 2.1 Latency Metrics (Per Agent, Node, and Tool)

| Metric | Captured? | Granularity | Details |
| :--- | :---: | :--- | :--- |
| **Duration / Latency per Agent** | ✅ Yes | Spans / Agents | Time spent inside Planner, Implementer, Reviewer specialists, or Worker subagents. |
| **Duration per Tool Call** | ✅ Yes | Tools | Execution latency for individual tools (`read_file`, `search_code`, `bash`, sandbox tests). |
| **Total Trace Latency** | ✅ Yes | Trace / Workflow | End-to-end execution time from issue ingestion to PR creation or rejection. |
| **P50 / P90 / P95 / P99 Latency** | ✅ Yes | Aggregated Server-side | Computed by Langfuse across all runs and filtered per tag (e.g., `agent:planner`, `agent:implementer`). |
| **Time to First Token (TTFT)** | ⚠️ Conditional | LLM Generations | Equal to total generation latency in default batch `ainvoke` mode. Requires streaming (`astream`) for chunk-level TTFT. |

### 2.2 Token Usage & Cost Metrics

| Metric | Captured? | Details |
| :--- | :---: | :--- |
| **Input (Prompt) Tokens** | ✅ Yes | Tracked per LLM call across all agents. |
| **Output (Completion) Tokens** | ✅ Yes | Tracked per generation. |
| **Total Tokens** | ✅ Yes | Summed per node, per agent role, and per full workflow run. |
| **Cost (USD)** | ✅ Yes | Calculated automatically by Langfuse based on the model tier (`gpt-4o` vs. `gpt-4o-mini`) and current pricing. |

### 2.3 Quality, Human-in-the-Loop & Reliability Scores

| Metric / Score Name | Type | Value Range | Meaning |
| :--- | :--- | :--- | :--- |
| `human_plan_review` | Numeric Score | `1.0` / `0.5` / `0.0` | `1.0` = Approved, `0.5` = Revised (with feedback), `0.0` = Rejected. |
| `qa_verdict` | Numeric Score | `1.0` / `0.0` | `1.0` = Passed quality gate, `0.0` = Fix required or retry limit reached. |
| `repair_attempts` | Metadata / Comment | Integer `0` to `3` | Tracks how many automated repair loops were executed before passing or halting. |
| `plan_revisions` | Metadata / Comment | Integer `0` to `3` | Tracks how many times human requested plan adjustments. |

### 2.4 Error & Reliability Metrics

| Metric | Captured? | Details |
| :--- | :---: | :--- |
| **Node / Agent Error Rate** | ✅ Yes | Unhandled exceptions in nodes mark spans as `ERROR` with stack traces in Langfuse. |
| **Tool Failure Rates** | ✅ Yes | Non-zero exit codes in tests or sandbox tool errors are recorded in span outputs. |
| **Retry Limit Exceeded** | ✅ Yes | QA circuit breaker triggers recorded as score `0.0` with status `retry_limit_reached`. |

---

## 3. Agent Role Tagging Matrix

Every span and generation emitted by DevPilot carries structured tags and metadata:

| Component | Role Tag | Sub-tags / Metadata | Model Tier |
| :--- | :--- | :--- | :--- |
| **Planner Agent** | `agent:planner` | `{"agent_role": "planner"}` | `gpt-4o` |
| **Implementer Agent** | `agent:implementer` | `{"agent_role": "implementer"}` | `gpt-4o` |
| **Security Reviewer** | `agent:reviewer` | `reviewer:security` | `gpt-4o-mini` |
| **Requirement Reviewer**| `agent:reviewer` | `reviewer:requirement` | `gpt-4o-mini` |
| **Code Quality Reviewer**| `agent:reviewer` | `reviewer:code_quality` | `gpt-4o-mini` |
| **Edge Case Reviewer** | `agent:reviewer` | `reviewer:edge_case` | `gpt-4o-mini` |
| **QA Evaluation Node** | `agent:qa` | `{"agent_role": "qa"}` | `gpt-4o-mini` |
| **Worker Subagents** | `agent:worker` | `{"declared_files": [...]}` | `gpt-4o-mini` |

---

## 4. Security & Data Redaction

DevPilot enforces strict credential masking before any data reaches Langfuse:
- **Redacted Values**: `OPENAI_API_KEY`, `E2B_API_KEY`, `LANGFUSE_SECRET_KEY`, and per-run `github_token`.
- **Scrubbing Engine**: Reuses `devpilot.core.logging.redact_string` to scrub inputs, metadata attributes, tags, and comments.
- **Zero-Token Leakage**: `github_token` is never injected into trace metadata or tags.

---

## 5. Graceful Degradation (No-Op Mode)

When `LANGFUSE_PUBLIC_KEY` or `LANGFUSE_SECRET_KEY` are unset:
- `get_langfuse_handler()` returns `None`.
- `get_langfuse_client()` returns `None`.
- All score recording and flush helpers safely no-op without exceptions or runtime overhead.

---

## 6. How to Query Metrics in the Langfuse UI

1. **Agent Latency & Percentiles (P50, P90, P99)**:
   - Navigate to **Traces** or **Dashboard** in Langfuse.
   - Filter by tag: `tags CONTAINS "agent:planner"`.
   - View the latency distribution chart for p50, p90, and p99 response times.
2. **Cost Breakdown by Agent**:
   - In the **Analytics** tab, group by tag `agent:*` to inspect spending across reasoning vs. execution tiers.
3. **Quality & Repair Analytics**:
   - In the **Scores** tab, view average `qa_verdict` trends and human approval conversion rates over time.
