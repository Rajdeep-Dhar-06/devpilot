"""Unit tests for DevPilot Langfuse observability module."""

from unittest.mock import MagicMock, patch

from devpilot.core.config import Settings
from devpilot.observability import (
    flush_observability,
    get_langfuse_client,
    get_langfuse_handler,
    record_human_decision,
    record_qa_result,
    sanitize_value,
)


def test_sanitize_value_redacts_secrets() -> None:
    """sanitize_value redacts configured secrets from nested dicts and lists."""
    secret_key = "sk-proj-verysecretkey123"
    token = "ghp_supersecretgithubtoken456"

    data = {
        "issue_url": "https://github.com/org/repo/issues/1",
        "nested": {
            "token": token,
            "normal": "hello world",
        },
        "list": [token, "ok"],
    }

    sanitized = sanitize_value(data, additional_secrets=[token, secret_key])

    assert sanitized["issue_url"] == "https://github.com/org/repo/issues/1"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["normal"] == "hello world"
    assert sanitized["list"][0] == "[REDACTED]"
    assert sanitized["list"][1] == "ok"


def test_noop_when_credentials_missing() -> None:
    """All observability functions are safe no-ops when Langfuse keys are absent."""
    with patch("devpilot.observability.settings", Settings(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")):
        # Reset global client so the missing-creds path is exercised
        with patch("devpilot.observability._langfuse_client", None):
            client = get_langfuse_client()
            assert client is None

        # Handler should also be None
        handler = get_langfuse_handler(
            issue_url="https://github.com/org/repo/issues/42",
            session_id="session-42",
        )
        assert handler is None

        # Scoring and flush must not raise
        record_human_decision("trace-1", "plan_review", "approve")
        record_qa_result("trace-1", "passed", 0)
        flush_observability()


def test_handler_initialized_when_credentials_present() -> None:
    """CallbackHandler is constructed with only public_key (v4 SDK API)."""
    fake_settings = Settings(
        LANGFUSE_PUBLIC_KEY="pk-lf-test",
        LANGFUSE_SECRET_KEY="sk-lf-test",
        LANGFUSE_HOST="https://cloud.langfuse.com",
    )

    with patch("devpilot.observability.settings", fake_settings):
        with patch("langfuse.langchain.CallbackHandler") as mock_handler:
            mock_instance = MagicMock()
            mock_handler.return_value = mock_instance

            handler = get_langfuse_handler(
                issue_url="https://github.com/org/repo/issues/10",
                session_id="issue-10",
                metadata={"repo": "org/repo"},
                tags=["custom-tag"],
            )

            assert handler == mock_instance
            mock_handler.assert_called_once()
            # v4 API: only public_key is passed to the constructor
            kwargs = mock_handler.call_args.kwargs
            assert kwargs.get("public_key") == "pk-lf-test"
            assert "secret_key" not in kwargs
            assert "host" not in kwargs
            assert "session_id" not in kwargs

            # Sanitised context is attached as private attributes
            assert mock_instance._devpilot_session_id == "issue-10"
            assert "devpilot" in mock_instance._devpilot_tags
            assert "custom-tag" in mock_instance._devpilot_tags
            assert mock_instance._devpilot_metadata["issue_url"] == "https://github.com/org/repo/issues/10"
            assert mock_instance._devpilot_metadata["repo"] == "org/repo"


def test_scoring_calls_create_score() -> None:
    """record_human_decision and record_qa_result call client.create_score (v4 API)."""
    mock_client = MagicMock()
    with patch("devpilot.observability.get_langfuse_client", return_value=mock_client):
        # 1. Approve → 1.0
        record_human_decision("trace-99", "plan_review", "approve", comment="looks great")
        mock_client.create_score.assert_called_with(
            trace_id="trace-99",
            name="human_plan_review",
            value=1.0,
            comment="Decision: approve - looks great",
        )

        # 2. Revise → 0.5
        mock_client.reset_mock()
        record_human_decision("trace-99", "plan_review", "revise")
        mock_client.create_score.assert_called_with(
            trace_id="trace-99",
            name="human_plan_review",
            value=0.5,
            comment="Decision: revise",
        )

        # 3. Reject → 0.0
        mock_client.reset_mock()
        record_human_decision("trace-99", "plan_review", "reject", comment="not acceptable")
        mock_client.create_score.assert_called_with(
            trace_id="trace-99",
            name="human_plan_review",
            value=0.0,
            comment="Decision: reject - not acceptable",
        )

        # 4. QA passed → 1.0
        mock_client.reset_mock()
        record_qa_result("trace-99", "passed", attempt=1)
        mock_client.create_score.assert_called_with(
            trace_id="trace-99",
            name="qa_verdict",
            value=1.0,
            comment="Status: passed, Attempt: 1",
        )

        # 5. QA failed → 0.0
        mock_client.reset_mock()
        record_qa_result("trace-99", "fix_required", attempt=2, feedback="test failure")
        mock_client.create_score.assert_called_with(
            trace_id="trace-99",
            name="qa_verdict",
            value=0.0,
            comment="Status: fix_required, Attempt: 2 - test failure",
        )


def test_scoring_without_trace_id_is_noop() -> None:
    """Scoring functions silently skip when trace_id is None."""
    mock_client = MagicMock()
    with patch("devpilot.observability.get_langfuse_client", return_value=mock_client):
        record_human_decision(None, "plan_review", "approve")
        record_qa_result(None, "passed", 0)
        mock_client.create_score.assert_not_called()


def test_init_failure_does_not_permanently_cache_none() -> None:
    """A failing Langfuse init does not permanently disable the client."""
    fake_settings = Settings(
        LANGFUSE_PUBLIC_KEY="pk-lf-test",
        LANGFUSE_SECRET_KEY="sk-lf-test",
    )
    with patch("devpilot.observability.settings", fake_settings):
        with patch("devpilot.observability._langfuse_client", None):
            with patch("devpilot.observability._langfuse_init_failed", False):
                with patch("langfuse.Langfuse", side_effect=RuntimeError("connect error")):
                    client = get_langfuse_client()
                    assert client is None  # Failed — returns None for this call

                # On next call with a working Langfuse, it should retry
                mock_lf = MagicMock()
                with patch("langfuse.Langfuse", return_value=mock_lf):
                    with patch("devpilot.observability._langfuse_client", None):
                        client2 = get_langfuse_client()
                        assert client2 == mock_lf


def test_flush_observability_calls_client_flush() -> None:
    """flush_observability calls client.flush."""
    mock_client = MagicMock()
    with patch("devpilot.observability.get_langfuse_client", return_value=mock_client):
        flush_observability()
        mock_client.flush.assert_called_once()


def test_flush_failure_does_not_raise() -> None:
    """flush_observability is safe even when client.flush raises."""
    mock_client = MagicMock()
    mock_client.flush.side_effect = RuntimeError("network error")
    with patch("devpilot.observability.get_langfuse_client", return_value=mock_client):
        flush_observability()  # Must not raise


def test_score_failure_does_not_raise() -> None:
    """record_* functions are safe even when create_score raises."""
    mock_client = MagicMock()
    mock_client.create_score.side_effect = RuntimeError("api error")
    with patch("devpilot.observability.get_langfuse_client", return_value=mock_client):
        record_human_decision("trace-x", "plan_review", "approve")  # Must not raise
        record_qa_result("trace-x", "passed", 1)  # Must not raise
