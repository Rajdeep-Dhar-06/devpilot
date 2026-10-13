"""Observability layer for DevPilot powered by Langfuse.

Follows Langfuse best practices:
- Framework integration via CallbackHandler to automatically capture LLMs,
  subagent nodes, token counts, and latencies without manual span duplication.
- Strict secret redaction reusing devpilot.core.logging.redact_string.
- Graceful no-op when credentials are missing.
- Captures workflow runs (session_id, trace metadata), QA retries, and Human decisions.
- Safe flush on process shutdown.
"""

import logging
import threading
from collections.abc import Sequence
from typing import Any

import logfire

from devpilot.core.config import settings
from devpilot.core.logging import redact_string

logger = logging.getLogger(__name__)

# Global cached client with a lock for thread-safe lazy initialisation
_langfuse_client: Any = None
_langfuse_init_failed: bool = False
_client_lock = threading.Lock()


def _get_known_secrets() -> list[str]:
    """Collects known application secrets to redact from traces."""
    secrets = [
        settings.OPENAI_API_KEY,
        settings.E2B_API_KEY,
        settings.LANGFUSE_SECRET_KEY,
    ]
    return [s for s in secrets if s and len(s) > 4]


def sanitize_value(val: Any, additional_secrets: Sequence[str] | None = None) -> Any:
    """Recursively sanitizes and redacts secrets from dictionary/string metadata."""
    secrets = _get_known_secrets() + list(additional_secrets or [])
    if isinstance(val, str):
        return redact_string(val, secrets)
    if isinstance(val, dict):
        return {k: sanitize_value(v, additional_secrets) for k, v in val.items()}
    if isinstance(val, list):
        return [sanitize_value(item, additional_secrets) for item in val]
    return val


def _make_mask_fn():
    """Returns a Langfuse-compatible mask function that redacts secrets from traces.

    NOTE: This only redacts string-typed values in the data that the Langfuse
    SDK passes to the mask function. Complex nested LLM payloads may not be
    fully covered — treat this as a best-effort safeguard, not a guarantee.
    """

    def _mask(*, data: Any) -> Any:
        return sanitize_value(data)

    return _mask


def get_langfuse_client() -> Any:
    """Returns the Langfuse client if configured, otherwise returns None.

    Thread-safe. Allows recovery from temporary init failures on subsequent
    calls by not permanently caching failed initialisation.
    """
    global _langfuse_client, _langfuse_init_failed

    # Fast path: already successfully initialised
    if _langfuse_client is not None:
        return _langfuse_client

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None

    with _client_lock:
        # Re-check inside the lock (another thread may have initialised)
        if _langfuse_client is not None:
            return _langfuse_client

        try:
            from langfuse import Langfuse

            _langfuse_client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
                mask=_make_mask_fn(),
            )
            _langfuse_init_failed = False
            logfire.info("Langfuse client initialised")
        except Exception:
            # Reset failed flag so the next call can retry
            _langfuse_client = None
            _langfuse_init_failed = True
            logfire.warn("Langfuse client initialisation failed; observability disabled for this attempt")
            logger.warning("Langfuse client initialisation failed", exc_info=True)

    return _langfuse_client


def get_langfuse_handler(
    issue_url: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    additional_secrets: Sequence[str] | None = None,
) -> Any:
    """Returns a Langfuse CallbackHandler for LangChain / LangGraph if configured.

    If credentials are missing or langfuse is not installed, returns None (no-op).

    NOTE: The v4 CallbackHandler constructor only accepts ``public_key`` and
    ``trace_context``. Session ID, tags, and metadata must be passed through
    ``RunnableConfig["metadata"]`` keys (``langfuse_session_id``,
    ``langfuse_tags``, ``langfuse_trace_name``) at the call site.
    """
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        try:
            from langfuse.callback import CallbackHandler  # type: ignore[no-redef]
        except ImportError:
            logfire.warn("Langfuse CallbackHandler not available; LangChain tracing disabled")
            return None

    sanitized_meta = sanitize_value(metadata or {}, additional_secrets=additional_secrets)
    if issue_url:
        sanitized_meta["issue_url"] = sanitize_value(issue_url, additional_secrets=additional_secrets)

    active_tags = list(tags or [])
    if "devpilot" not in active_tags:
        active_tags.append("devpilot")

    try:
        # v4 SDK: pass only public_key; session/tags/metadata go via RunnableConfig
        handler = CallbackHandler(public_key=settings.LANGFUSE_PUBLIC_KEY)
        # Store sanitized context so callers can inject it into RunnableConfig metadata
        handler._devpilot_session_id = session_id  # type: ignore[attr-defined]
        handler._devpilot_metadata = sanitized_meta  # type: ignore[attr-defined]
        handler._devpilot_tags = active_tags  # type: ignore[attr-defined]
        return handler
    except Exception:
        logfire.warn("Failed to create Langfuse CallbackHandler; LangChain tracing disabled")
        logger.warning("Failed to create Langfuse CallbackHandler", exc_info=True)
        return None


def record_human_decision(
    trace_id: str | None,
    checkpoint_name: str,
    decision: str,
    comment: str | None = None,
) -> None:
    """Records a human review checkpoint decision as a Langfuse score and event."""
    client = get_langfuse_client()
    if not client or not trace_id:
        return

    score_val = 1.0 if decision == "approve" else (0.5 if decision == "revise" else 0.0)
    sanitized_comment = sanitize_value(
        f"Decision: {decision}" + (f" - {comment}" if comment else "")
    )
    try:
        client.create_score(
            trace_id=trace_id,
            name=f"human_{checkpoint_name}",
            value=score_val,
            comment=sanitized_comment,
        )
    except Exception:
        logfire.warn("Failed to record human decision score to Langfuse")
        logger.warning("Failed to record human decision score to Langfuse", exc_info=True)


def record_qa_result(
    trace_id: str | None,
    status: str,
    attempt: int,
    feedback: str | None = None,
) -> None:
    """Records QA evaluation verdict and attempt count as a Langfuse score."""
    client = get_langfuse_client()
    if not client or not trace_id:
        return

    score_val = 1.0 if status == "passed" else 0.0
    sanitized_comment = sanitize_value(
        f"Status: {status}, Attempt: {attempt}" + (f" - {feedback}" if feedback else "")
    )
    try:
        client.create_score(
            trace_id=trace_id,
            name="qa_verdict",
            value=score_val,
            comment=sanitized_comment,
        )
    except Exception:
        logfire.warn("Failed to record QA result score to Langfuse")
        logger.warning("Failed to record QA result score to Langfuse", exc_info=True)


def flush_observability() -> None:
    """Flushes queued events to Langfuse before shutdown."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
        except Exception:
            logfire.warn("Langfuse flush failed; some events may be lost")
            logger.warning("Langfuse flush failed", exc_info=True)
