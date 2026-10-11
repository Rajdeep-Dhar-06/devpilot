import logging

from devpilot.core.logging import SecretRedactingFormatter


def test_secret_redacting_formatter() -> None:
    formatter = SecretRedactingFormatter(
        secrets=["sk-proj-supersecret12345", "e2b_999888777666"],
        fmt="%(message)s",
    )
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Using key sk-proj-supersecret12345 and e2b_999888777666 to run sandbox",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "sk-proj-supersecret12345" not in formatted
    assert "e2b_999888777666" not in formatted
    assert "[REDACTED]" in formatted
