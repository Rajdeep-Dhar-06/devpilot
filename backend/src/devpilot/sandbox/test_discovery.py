"""Hybrid discovery of project test, lint, and type-check commands.

Implements Decision 6:
1. Per-repo config file (devpilot.json) if present.
2. Auto-detection rules based on manifest files.
3. Explicit 'not_found' / missing result that fails safely in QA evaluation.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass
class DiscoveredCommands:
    """Discovered commands for testing and validation."""

    test_command: str | None
    lint_command: str | None
    typecheck_command: str | None
    source: str  # 'config', 'auto_detected', or 'not_found'

    @property
    def is_missing(self) -> bool:
        """Returns True if no test command could be discovered."""
        return self.test_command is None


class TestCommandDiscovery:
    """Discovers verification commands from files present in repository."""

    def discover(self, files: Mapping[str, str]) -> DiscoveredCommands:
        """Inspects provided repository file names and contents to determine commands.

        Args:
            files: Dictionary mapping file relative path to content or presence indicator.
        """
        # Strategy 1: Explicit repository configuration file
        if "devpilot.json" in files:
            try:
                cfg = json.loads(files["devpilot.json"])
                return DiscoveredCommands(
                    test_command=cfg.get("test_command"),
                    lint_command=cfg.get("lint_command"),
                    typecheck_command=cfg.get("typecheck_command"),
                    source="config",
                )
            except Exception:
                pass

        # Strategy 2: Auto-detection based on project manifests (Decision 14: Python prioritized)
        if "pyproject.toml" in files:
            content = files["pyproject.toml"]
            test_cmd = "pytest" if "pytest" in content else "python -m unittest"
            lint_cmd = "ruff check" if "ruff" in content else "flake8"
            type_cmd = "mypy" if "mypy" in content else None
            return DiscoveredCommands(
                test_command=test_cmd,
                lint_command=lint_cmd,
                typecheck_command=type_cmd,
                source="auto_detected",
            )

        if "package.json" in files:
            return DiscoveredCommands(
                test_command="npm test",
                lint_command="npm run lint",
                typecheck_command=None,
                source="auto_detected",
            )

        if "Makefile" in files:
            content = files["Makefile"]
            if "test:" in content:
                return DiscoveredCommands(
                    test_command="make test",
                    lint_command="make lint" if "lint:" in content else None,
                    typecheck_command="make typecheck" if "typecheck:" in content else None,
                    source="auto_detected",
                )

        # Strategy 3: Safe fallback when no test commands are found
        return DiscoveredCommands(
            test_command=None,
            lint_command=None,
            typecheck_command=None,
            source="not_found",
        )
