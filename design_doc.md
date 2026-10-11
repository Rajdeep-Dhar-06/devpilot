# DevPilot Design Doc

Living record of architectural decisions made during design mode. No code is written until the user gives an explicit go-ahead.

## Decision 1: When to save issue/solution data to the RAG store

- **Decision:** Save at PR creation, inside the PR Node (V1).
- **Options considered:**
  1. At PR creation (chosen).
  2. After the PR is merged and checks pass, via webhook and a `post_merge` graph.
  3. Both: save as "unverified" at PR time, then promote after merge.
- **Why this one:** Simplest for V1. It matches the original spec and needs no webhook or second graph.
- **Trade-offs accepted:** Unmerged or incorrect fixes can enter the store and pollute retrieval.
- **Follow-ups for the structure:** `webhooks.py` and `workflows/post_merge/` are deferred to a later version. The records should carry a status field so verification can be added later without a migration.

## Decision 2: How worker agents are delegated

- **Decision:** The `delegate_work` tool starts a plain LangChain `create_agent()` worker (V1). It has no custom LangGraph subgraph.
- **Options considered:**
  1. Plain `create_agent()` worker (chosen).
  2. Worker as a LangGraph subgraph.
  3. No workers in V1.
- **Why this one:** It matches the original spec and is the least code. The tool's interface (task, acceptance criteria, workspace) stays the same, so a subgraph can replace it later.
- **Trade-offs accepted:** There is less visibility into worker steps, and no checkpointing inside the worker.
- **Follow-ups for the structure:** `tools/subagent.py` should expose `delegate_work` rather than `invoke_subgraph`. Workers get bounded tasks, and the Implementation Agent inspects their results before relying on them. Avoid simultaneous workers editing overlapping files.

## Decision 3: Keeping the Review Agent read-only while tests run in parallel

- **Decision:** Tool policy only. Reviewers and the Testing Node share one sandbox (V1).
- **Options considered:**
  1. Tool policy only (chosen).
  2. Separate read-only snapshot for reviewers.
  3. Run Testing first, then Review (sequential).
- **Why this one:** It is the simplest option, keeps one sandbox, and preserves the required parallel execution.
- **Trade-offs accepted:** Isolation is enforced in code only. Reviewers might see test artifacts that are half-written.
- **Follow-ups for the structure:** `tools/policy.py` and `sandbox/command_policy.py` give reviewers read-only tools and a command allowlist, with write commands rejected. Reviewer prompts say to ignore untracked and ignored files. Revisit option 2 if flakiness appears.

## Decision 4: How the branch leaves the sandbox without exposing the GitHub token

- **Decision:** The backend injects a short-lived, scoped token into the sandbox only for the push, and removes it right after (V1).
- **Options considered:**
  1. Short-lived token injected for the push only (chosen).
  2. Pull a `git bundle` or patch out and push from the backend.
  3. Create commits through the GitHub API or MCP.
- **Why this one:** It uses normal git and takes the least work. It is acceptable because the PR Node runs only after every agent has finished.
- **Trade-offs accepted:** The token briefly exists inside the sandbox. This is safe only if no agent or arbitrary command is running during the push.
- **Follow-ups for the structure:** `sandbox/git_ops.py` owns push and token cleanup. The PR Node must confirm that no agent is active before injecting the token. It must use a token scoped to the target repo with a short expiry, and it must remove the token even if the push fails. The token must never appear in logs or agent-visible output. Revisit option 2 if the threat model tightens.

## Decision 5: Checkpointing and background execution

- **Decision:** Postgres checkpointer for LangGraph, plus a separate Celery and Redis worker that runs the graphs (V1).
- **Options considered:**
  1. Postgres checkpointer plus FastAPI background tasks.
  2. Postgres checkpointer plus Celery and Redis worker (chosen).
  3. Postgres checkpointer plus a lighter queue (ARQ or a DB-backed job table).
- **Why this one:** Runs survive API restarts, workers can scale, and it matches the planned tree (`worker/`, Redis in docker-compose).
- **Trade-offs accepted:** More infrastructure (Redis, Celery, extra Docker services) and more debugging surface.
- **Follow-ups for the structure:** The checkpointer is mandatory, because human-in-the-loop pause and resume cannot work without it. The API only enqueues start and resume jobs through `run_service.py`. The worker owns graph execution. Approval endpoints save the decision and enqueue a resume job.

## Decision 6: How the Testing Node discovers test, lint and type-check commands

- **Decision:** Hybrid. Use a per-repo config if present, otherwise auto-detect by known files, otherwise return a structured "no test command found" result (V1).
- **Options considered:**
  1. Per-repo config file only.
  2. Auto-detection by rules only.
  3. An LLM agent figures it out.
  4. Hybrid (chosen).
- **Why this one:** It keeps the Testing Node deterministic, as the spec requires, with a safe fallback.
- **Trade-offs accepted:** More code than a single strategy. Auto-detection rules need maintenance and fail on unusual repos, and those cases fall back to the config or the failure result.
- **Follow-ups for the structure:** A missing test command must reach QA as an explicit failed or unknown state. It must never count as a pass. Detected commands still pass through `sandbox/command_policy.py`. The test result records which source supplied the commands (config or detected).

## Decision 7: Limit on plan revisions

- **Decision:** No limit on plan revisions in V1. The human decides when to stop.
- **Options considered:**
  1. No limit (chosen).
  2. Hard limit (default 3, configurable).
  3. Soft limit with a warning.
- **Why this one:** It is the simplest option and keeps the human in full control of the planning phase.
- **Trade-offs accepted:** Cost is unbounded, and a workflow can stay open indefinitely if the human keeps revising or never responds.
- **Follow-ups for the structure:** Keep a `plan_revisions` counter in state anyway. It costs nothing, shows in the UI and traces, and makes adding a limit later easy. Consider a task timeout or abandonment policy for runs left waiting on a human.

## Decision 8: Build order

- **Decision:** Build the agent layer first, with all agents and the workflow fully working. Add the API, Postgres persistence, Redis and Celery afterward.
- **Options considered:**
  1. Backend core first, UI last.
  2. Thin end-to-end slice of every layer first.
  3. Agent quality first, with infrastructure later.
  The choice is closest to options 1 and 3: agents and graph first, infrastructure second.
- **Why this one:** The main risk is the agents, the graph and the sandbox, so that is where to learn first.
- **Trade-offs accepted:** Pause/resume behaviour with Postgres and Celery is verified late. There is no UI and no API during phase 1.
- **Follow-ups for the structure:** Phase 1 covers `domain/`, `agents/`, `tools/`, `sandbox/`, `rag/`, `integrations/` and `workflows/`. Phase 2 covers `api/`, `services/`, `db/`, `worker/` and the Postgres checkpointer. Later phases cover the frontend, evals and observability. Phase 1 needs a way to run the graph and answer human approvals without the API.

## Decision 9: Human approvals and checkpointing in phase 1

- **Decision:** An interactive CLI collects approvals in phase 1, using a local Postgres checkpointer (run in Docker) from the start.
- **Options considered:**
  1. CLI with an in-memory checkpointer.
  2. CLI with a SQLite checkpointer.
  3. CLI with a local Postgres checkpointer (chosen).
- **Why this one:** There are no surprises when the API and worker arrive in phase 2. Pause/resume behaviour is tested against the real production store from day one.
- **Trade-offs accepted:** Phase 1 needs Docker and Postgres, so setup is heavier and early iteration is slower.
- **Follow-ups for the structure:** `docker-compose.yml` ships Postgres (with pgvector) in phase 1, which the RAG store can share. The CLI is a thin runner that starts the graph, shows the plan or diff at each interrupt, and resumes with the human's decision. It must contain no business logic, because phase 2 replaces it with the API and `services/`.

## Decision 10: LLM strategy

- **Decision:** One provider with tiered models. A strong model for the Planner and Implementer, and a cheaper model for reviewers, QA summaries and workers. The model name is configured per agent. **The provider is still open.**
- **Options considered:**
  1. One model for everything.
  2. One provider, tiered models (chosen).
  3. Multi-provider, configurable per agent.
- **Why this one:** A good cost and quality balance with a single API key. Per-agent model config keeps the path to multi-provider open.
- **Trade-offs accepted:** Each tier needs tuning, and a cheaper reviewer model may miss subtle issues. Evals should check this.
- **Follow-ups for the structure:** `build_agent()` takes the model as input. `core/config.py` holds the per-agent model names. `integrations/llm/client.py` is the single place that talks to the provider.

### Decision 10 update: provider chosen

- **Provider:** OpenAI, through `langchain-openai`.
- **Follow-ups:** Choose the exact model names per tier (strong and cheap) when implementation starts. Check the current OpenAI model list and LangChain docs first, because names change often.

## Decision 11: GitHub authentication

- **Decision:** A GitHub App. DevPilot mints short-lived, per-repo installation tokens (V1).
- **Options considered:**
  1. Fine-grained Personal Access Token.
  2. GitHub App (chosen).
  3. PAT now, GitHub App later behind an abstraction.
- **Why this one:** It is the production standard. Tokens are short-lived and scoped by design, which fits decision 4 (the token is injected into the sandbox only for the push).
- **Trade-offs accepted:** More setup up front: app registration, a private key and an installation on the target repos. Local development needs that setup too.
- **Follow-ups for the structure:** `integrations/github_mcp/client.py` and `core/security.py` handle the app ID, private key and installation token minting. The private key is stored as a secret and never reaches the sandbox. Permissions are minimal: read issues, read and write contents, write pull requests. The token function takes the repo and returns a token with a short expiry. Setup steps for the app go in `docs/security.md`.

## Decision 12: QA verdict and repair feedback

- **Decision:** The QA Node uses an LLM to judge the results and write the repair feedback, with hard rule guardrails the LLM cannot override (C2).
- **Options considered:**
  1. Pure rules.
  2. Rules for the verdict, LLM for the feedback.
  3. LLM decides everything.
  4. LLM decides, with hard guardrails (chosen).
- **Why this one:** It allows flexible judgment and well-prioritized feedback while keeping the safety properties from the spec. The LLM can only make the outcome stricter, never looser.
- **Trade-offs accepted:** Extra LLM cost and some non-determinism in the pass or fix decision. Routing, the retry counter and the guardrail checks stay deterministic and unit-testable.
- **Follow-ups for the structure:** The guardrail rules force "fix required" when tests failed or were not run, when lint or type checks failed, or when a high or critical finding exists. The exact thresholds are still open (next question). The QA code applies the guardrails after the LLM call and takes the stricter result. The routing function reads only the final `qa_status`. The QA result records whether a guardrail overrode the LLM, for observability and evals.

### Decision 12 update: guardrail severity threshold

- **Severity levels:** critical, high, medium, low, info (normalized by the Merge Node).
- **Threshold:** High and critical findings force "fix required".
- **Security exception:** Any security finding of medium or higher also forces a fix. This was proposed with the threshold and read as accepted when the user chose option B. It is open to correction.
- **Below the threshold:** The LLM weighs the remaining findings. It can make the outcome stricter but never looser.

## Decision 13: Sandbox lifetime across the run

- **Decision:** A single always-alive sandbox for the whole run (A1). The sandbox is created once and its timeout is extended throughout, including during human approval pauses (V1).
- **Options considered:**
  1. Always-alive sandbox (chosen).
  2. Alive while working, auto-pause when idle, with a re-clone fallback.
  3. Pause and resume at each approval.
  4. Recreate from git when needed.
- **Why this one:** Simplicity. The workflow code does not manage lifetime, and state (dependencies, branch, working tree) is always present.
- **Trade-offs accepted:** E2B caps continuous runtime (about 1 hour on Hobby and 24 hours on Pro, checked against current docs). Idle approval time is billed. A pause longer than the cap kills the run.
- **Known risk:** A human who is slow to approve (plan or publication) can cause the sandbox to be lost. Because there is no fallback, such a run must fail with a clear error and be restarted.
- **Follow-ups for the structure:** `sandbox/provider.py` owns timeout extension and detects a lost sandbox, raising a clear error. The run fails cleanly with the reason recorded. The E2B plan is still unconfirmed and sets the real cap. Revisit auto-pause with auto-resume if the cap or cost hurts, since it is a small change behind `provider.py`.

## Decision 14: Target repo scope for V1

- **Decision:** One language and a few repos, using standard tooling (A). **The language and the first target repo are still open.**
- **Options considered:**
  1. One language, a few repos (chosen).
  2. Two or three languages.
  3. Any repo.
- **Why this one:** It is faster to make reliable. The sandbox image, test detection (decision 6) and prompts stay focused. It lets the agents be tuned on real issues before widening.
- **Trade-offs accepted:** Other languages are unsupported until later.
- **Follow-ups for the structure:** The language choice drives the E2B sandbox template, the auto-detection rules, the allowlisted commands in `sandbox/command_policy.py` and parts of the agent prompts. The first target should be a repo the user controls, with some real or realistic issues for evals.

### Decision 14 update: language chosen

- **Language:** Python.
- **Standard tooling assumed by the Testing Node and command policy:** `pytest`, `ruff`, `mypy`, and `pip` or `uv`.
- **Still open:** Whether the first target is an existing repo or a small sample repo made for testing DevPilot.

## Decision 15: First target repo

- **Decision:** A small sample Python repo built for testing DevPilot (A). Move to an existing repo of the user's once the agents are stable.
- **Options considered:**
  1. Small sample repo (chosen).
  2. An existing repo of the user's.
  3. A public open-source repo (needs a fork).
- **Why this one:** The user controls it and can plant issues with known fixes, giving clear pass or fail signals. It seeds the evals dataset (`evals/datasets/issues.jsonl`).
- **Trade-offs accepted:** Less real-world messiness at first.
- **Follow-ups for the structure:** The sample repo is separate from the DevPilot repo, and the GitHub App is installed on it. It needs a working `pytest` suite, `ruff` and `mypy` config, and a few issues of varied difficulty.

## Decision 16: Deterministic branch verification

- **Decision:** After the Implementation Agent finishes, plain code (not the LLM) verifies the branch (B). The same check runs again at the PR Node.
- **Options considered:**
  1. Trust the agent's own report.
  2. Deterministic check after the agent (chosen).
  3. Check both before and after.
- **Why this one:** It is cheap and reliable. It catches a missing or wrong branch before testing and review work is wasted.
- **Trade-offs accepted:** One small extra step in the graph after implementation.
- **Follow-ups for the structure:** `sandbox/git_ops.py` provides the check. It confirms the current branch matches the expected name, that it differs from the base branch, and that it holds the changes. Code generates the branch name and passes it to the agent, and the agent does not invent it. The name is stored in state as `branch_name`. On failure the run ends with a clear error, or loops back to the Implementation Agent. The failure behavior is covered in the failure-outcome decision. The same branch is reused for QA repair attempts.

## Spec correction: `repair_attempts`

- `repair_attempts` appears twice in the spec's state (initial input and QA). It will be defined once in the state, as an optional field that defaults to 0 and is incremented by the QA routing.

## Decision 17: Failure and termination outcomes

- **Decision:** On any run that ends without a PR, discard the work (A). Kill the sandbox and record the failure reason.
- **Options considered:**
  1. Discard everything (chosen).
  2. Keep a failure report and diff as artifacts, with no push.
  3. Push the branch to GitHub for inspection.
- **Why this one:** Simplest for V1. There is no leftover cost, branches or stored artifacts to manage.
- **Trade-offs accepted:** Partial work is lost, so the cause of a failure cannot be inspected afterward beyond the recorded reason. This also removes the failure data that would have been useful for evals.
- **Applies to:** Repair limit reached, a lost sandbox, a failed branch check, a human rejection (plan or publication) and unexpected errors.
- **Follow-ups for the structure:** The `fail` and `end_rejected` nodes must always kill the sandbox, even when cleanup runs after an error. The recorded reason should still capture the last QA, test and review summaries in logs, as text. The log is the only trace left, and it must not contain secrets. Revisit option 2 when the evals phase starts.

## Decision 18: Worker limits

- **Decision:** At most 5 workers running in parallel. Workers cannot invoke other agents (no nesting). The limit is read from config.
- **Options considered:** worker count cap, sequential only, step limit per worker, file scope per task, or no limits.
- **Why this choice:** It bounds cost and fan-out, and it prevents recursive delegation by removing `delegate_work` from the worker's toolset.
- **Trade-offs accepted:** Parallel workers can edit overlapping files in the same sandbox and the same working tree, which the spec warned against. There is also no step limit per worker yet. Both are open (next question).
- **Follow-ups for the structure:** `tools/policy.py` gives workers a toolset without `delegate_work` or any agent-invoking tool. `tools/subagent.py` enforces the cap of 5 concurrent workers. An extra request while 5 are running should either wait or return a clear error to the Implementation Agent (to be decided). The Implementation Agent still inspects each worker's result before relying on it.

## Decision 19: Preventing parallel workers from overwriting each other

- **Decision:** Declared file scope, enforced (A). Each worker task must list the files or directories it may modify. A new worker whose scope overlaps a running worker's scope is rejected. The write tool blocks edits outside a worker's declared scope.
- **Options considered:**
  1. Declared scope, enforced (chosen).
  2. Declared scope, advisory only.
  3. Separate git worktrees per worker, merged afterward.
- **Why this one:** It prevents conflicts at the source and is easy to unit-test. Worktrees are too heavy for V1.
- **Trade-offs accepted:** The Implementation Agent must plan non-overlapping scopes up front. Read access is not restricted.
- **Follow-ups for the structure:** `tools/subagent.py` tracks the scopes of running workers and rejects overlaps with a clear error. `tools/policy.py` and `sandbox/command_policy.py` enforce write scope for worker commands. Enforcing scope on shell commands is harder than on a file-edit tool, so workers should write through a scoped file-edit tool and bash should be restricted for workers. The exact mechanism is for the implementation plan.
- **Still open:** What happens to a 6th worker request while 5 are running: wait in a queue, or return an error to the agent.

### Decision 18 update: behavior at the worker cap

- **Decision:** When a worker is requested while 5 are already running, `delegate_work` returns an error immediately (B). The error says the limit was reached and how many are running. The Implementation Agent then decides whether to do the task itself, wait or reorder. Nothing blocks silently.
- **Trade-offs accepted:** The Implementation Agent prompt must teach it to handle this error.
- **Still open:** A per-worker step and time limit was recommended with this choice, so that a stuck worker cannot hold a slot forever. It has not been confirmed. Without it, a stuck worker permanently consumes one of the 5 slots.
