# DevPilot Backend

Core engine for DevPilot, implementing agents, workflows, sandbox operations, and domain models.

## Observability (Langfuse)

DevPilot includes a Langfuse observability layer (`devpilot/observability.py`) following best practices:
- Automatic tracing of all LangGraph nodes, LLM calls, and tool steps via Langfuse's LangChain `CallbackHandler`.
- Agent role tagging (`planner`, `implementer`, `reviewer`, `tester`, `qa`) capturing token counts, latency, and model tiers.
- Automatic recording of QA retry cycles and human checkpoint decisions (`approve`, `revise`, `reject`).
- Sensitive credential and GitHub token redaction before any traces are emitted.
- Safe no-op behavior when credentials are not configured.

To enable Langfuse tracing, set the following environment variables in `.env`:

```bash
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com" # Or self-hosted URL
```