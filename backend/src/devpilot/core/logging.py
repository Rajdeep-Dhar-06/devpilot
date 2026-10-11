import logging
import sys
from collections.abc import Sequence


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
        redacted = original
        for secret in self.secrets:
            if secret in redacted:
                redacted = redacted.replace(secret, "[REDACTED]")
        return redacted


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
