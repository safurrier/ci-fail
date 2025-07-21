"""Data models and exceptions for CI failure analysis."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# === EXCEPTIONS ===


class CIFailError(Exception):
    """Base exception for CI failure analysis errors."""

    pass


class CommandNotFoundError(CIFailError):
    """Raised when a required command is not found."""

    def __init__(self, command: str, install_message: str = ""):
        self.command = command
        self.install_message = install_message
        super().__init__(f"Command not found: {command}")


class APIError(CIFailError):
    """Raised when API calls fail."""

    pass


class ValidationError(CIFailError):
    """Raised when validation fails."""

    pass


# === ENUMS ===


class OutputFormat(Enum):
    """Output format options for the CLI."""

    JSON = "json"
    HUMAN = "human"


# === DATA MODELS ===


@dataclass
class BuildkiteFailure:
    """Represents a failing Buildkite check."""

    name: str
    description: str
    link: str
    build_id: str
    pipeline_name: str


@dataclass
class BuildkiteInProgress:
    """Represents an in-progress Buildkite check."""

    name: str
    description: str
    link: str
    build_id: str
    pipeline_name: str


@dataclass
class JobFailure:
    """Represents a failing job within a build."""

    job_id: str
    job_name: str
    failing_command: Optional[str] = None
    error_message: Optional[str] = None
    error_context: list[str] = field(default_factory=list)


@dataclass
class LogAnalysis:
    """Results of log analysis."""

    failing_command: Optional[str] = None
    error_message: Optional[str] = None
    error_context: list[str] = field(default_factory=list)


@dataclass
class ChecksStatus:
    """Status of CI checks."""

    total_checks: int
    buildkite_checks: int
    running_checks: int
    passed_checks: int
    failed_checks: int
    neutral_checks: int
    cancelled_checks: int
    skipped_checks: int
    timed_out_checks: int
    failures: list[BuildkiteFailure] = field(default_factory=list)
    in_progress: list[BuildkiteInProgress] = field(default_factory=list)
