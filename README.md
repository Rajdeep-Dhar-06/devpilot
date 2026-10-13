# DevPilot

> Autonomous AI software engineering platform orchestrating the complete issue-to-pull-request lifecycle with LangGraph, isolated sandbox environments, multi-agent review, and human-in-the-loop controls.

## Overview

DevPilot transforms GitHub issues into verified pull requests by coordinating specialized agents within deterministic workflow boundaries:
1. **Perceive & Explore**: Ingest issue details, initialize isolated E2B sandbox workspace, retrieve historical solutions via pgvector.
2. **Plan**: Formulate structured implementation plan and obtain human approval.
3. **Implement**: Create dedicated working branch, execute code changes with bounded subagent delegation.
4. **Verify & Review**: Parallel test execution and 4-way independent code review (Security, Requirement, Code Quality, Edge Case).
5. **QA & Guardrails**: Enforce automated quality gates and retry limits.
6. **Publish**: Obtain human publication sign-off, push branch, open PR, and index solution.

## Project Structure

```
devpilot/
├── backend/               # Python application package (FastAPI, LangGraph, agents)
│   ├── src/devpilot/      # Source tree (core, domain, workflows, agents, tools)
├── docs/                  # Architecture, Data Model, and Observability specs
├── docker-compose.yml     # Local services (PostgreSQL + pgvector)
├── Makefile               # Task runner (test, lint, typecheck, db)
└── design_doc.md          # Architectural decisions log
```

## Getting Started

1. Clone repository and set up environment:
   ```bash
   cp .env.example .env
   ```

2. Start database services:
   ```bash
   make db-up
   ```

3. Run verification checks:
   ```bash
   make check
   ```

## Observability

DevPilot integrates with [Langfuse](https://langfuse.com) for end-to-end tracing across all LangGraph nodes, multi-agent review subgraphs, and tool calls.
Configure the following in your `.env`:
```bash
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com"
```
If keys are omitted, tracing automatically acts as a zero-overhead no-op.
