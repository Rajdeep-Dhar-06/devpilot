import logging
import sys
from collections.abc import Sequence


def redact_string(text: str, secrets: Sequence[str] | None = None) -> str:
    """Redacts known secrets from a string."""
    if not text:
        return text
    active_secrets = [s for s in (secrets or []) if s and len(s) > 4]
    redacted = text
    for secret in active_secrets:
        if secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


class SecretRedactingFormatter(logging.Formatter):
    """Logging formatter that redacts sensitive strings such as API keys and tokens."""

    def __init__(
        self,
        secrets: Sequence[str] | None = None,
        fmt: str | None = None,
        datefmt: str | None = None,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.secrets = [s for s in (secrets or []) if s and len(s) > 4]

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_string(original, self.secrets)


def setup_logging(
    log_level: str = "INFO",
    secrets_to_redact: Sequence[str] | None = None,
) -> None:
    """Configures root logging with secret redaction enabled."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = SecretRedactingFormatter(
        secrets=secrets_to_redact,
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]


def setup_logfire() -> None:
    """Configures Pydantic Logfire if LOGFIRE_TOKEN is set.

    Routes stdlib logging into Logfire and instruments Pydantic model
    validation. Safe to call even when Logfire is not configured — in that
    case it is a no-op.
    """
    try:
        import logfire

        from devpilot.core.config import settings

        if not settings.LOGFIRE_TOKEN:
            return

        logfire.configure(
            token=settings.LOGFIRE_TOKEN,
            send_to_logfire=True,
        )
        logfire.instrument_logging()
        logfire.instrument_pydantic()
    except Exception:
        # Logfire setup must never crash the application
        logging.getLogger(__name__).debug("Logfire setup skipped", exc_info=True)
