"""Log analysis and error extraction functions."""

from typing import Optional

from ci_fail.config import Config, Patterns
from ci_fail.models import LogAnalysis


def clean_log_content(logs: str) -> str:
    """Clean log content by removing ANSI escape sequences and control characters.

    Args:
        logs: Raw log content with escape sequences

    Returns:
        Cleaned log content
    """
    # Remove ANSI escape sequences (colors, cursor movements, etc.)
    cleaned = Patterns.ANSI_ESCAPE.sub("", logs)

    # Remove Buildkite-specific escape sequences
    cleaned = Patterns.BK_ESCAPE.sub("", cleaned)

    # Remove Buildkite timestamp prefixes (bk;t=1752684001018$ format)
    # This handles both the command prefix and regular log line prefixes
    cleaned = Patterns.BK_TIMESTAMP.sub("", cleaned)

    # Remove carriage returns that mess up formatting
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Remove common Buildkite formatting artifacts
    lines = cleaned.split("\n")
    cleaned_lines = []

    for line in lines:
        # Skip empty lines and common artifacts
        if not line.strip():
            continue

        # Check if line matches any artifact pattern
        is_artifact = False
        for pattern in Patterns.BK_ARTIFACTS:
            if pattern.match(line):
                is_artifact = True
                break

        if not is_artifact:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_failing_command(lines: list[str]) -> Optional[str]:
    """Extract the failing command from log lines.

    Args:
        lines: List of log lines

    Returns:
        Failing command string or None if not found
    """
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try each pattern in order of priority
        for pattern in Patterns.COMMAND_PATTERNS:
            match = pattern.search(line)
            if match:
                command = match.group(1).strip()
                # Filter out obviously wrong matches
                if (
                    len(command) > 3
                    and not command.startswith("---")
                    and not command.startswith("===")
                    and "info" not in command.lower()[:10]
                ):
                    return command

    return None


def find_error_message_and_context(lines: list[str]) -> tuple[Optional[str], list[str]]:
    """Find error message and surrounding context from log lines.

    Args:
        lines: List of log lines

    Returns:
        Tuple of (error_message, error_context) or (None, []) if not found
    """
    # First pass: look for specific error patterns
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        for pattern in Patterns.ERROR_PATTERNS:
            match = pattern.search(line_lower)
            if match:
                # Check if this is a fallback pattern (group 0 means use full line)
                if pattern.groups == 0:
                    error_message = line.strip()
                else:
                    # Try to extract the error message from the most relevant group
                    error_message = None
                    for group_idx in range(pattern.groups, 0, -1):
                        try:
                            candidate = match.group(group_idx).strip()
                            if candidate:
                                error_message = candidate
                                break
                        except IndexError:
                            continue

                    if not error_message:
                        error_message = line.strip()

                    # If we extracted just part of the error, include the full line
                    if len(error_message) < len(line.strip()) * 0.5:
                        error_message = line.strip()

                # Get context around the error
                start = max(0, i - Config.ERROR_CONTEXT_WINDOW)
                end = min(len(lines), i + Config.ERROR_CONTEXT_WINDOW)
                context = [line.strip() for line in lines[start:end] if line.strip()]
                return error_message, context

    # Second pass: look for exit status indicators
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if (
            "exited with status" in line_lower
            or "exit code" in line_lower
            or "command failed" in line_lower
        ):
            error_message = line.strip()
            start = max(0, i - Config.ERROR_CONTEXT_WINDOW)
            end = min(len(lines), i + Config.ERROR_CONTEXT_WINDOW)
            context = [line.strip() for line in lines[start:end] if line.strip()]
            return error_message, context

    # Third pass: look for any line containing common failure indicators
    failure_indicators = [
        "targets failed",
        "failed to",
        "unable to",
        "cannot",
        "missing",
        "not found",
        "permission denied",
        "access denied",
        "timeout",
        "connection refused",
        "network error",
        "socket error",
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if any(indicator in line_lower for indicator in failure_indicators):
            # Skip obviously non-error lines
            if (
                "all checks passed" in line_lower
                or "success" in line_lower
                or "completed" in line_lower
            ):
                continue

            error_message = line.strip()
            start = max(0, i - Config.ERROR_CONTEXT_WINDOW)
            end = min(len(lines), i + Config.ERROR_CONTEXT_WINDOW)
            context = [line.strip() for line in lines[start:end] if line.strip()]
            return error_message, context

    return None, []


def extract_detailed_error_info(lines: list[str]) -> tuple[Optional[str], list[str]]:
    """Extract detailed error information with enhanced context.

    Args:
        lines: List of log lines

    Returns:
        Tuple of (detailed_error_message, enhanced_context)
    """
    # Context sizes for each multi-line pattern
    context_sizes = [10, 5, 8, 5, 7, 6, 5]

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        for pattern, context_size in zip(
            Patterns.MULTILINE_ERROR_PATTERNS, context_sizes
        ):
            if pattern.search(line):
                # Found a multi-line error pattern
                start = max(0, i - 2)  # Include a bit before
                end = min(len(lines), i + context_size)
                context = [line.strip() for line in lines[start:end] if line.strip()]

                # Try to find the most informative error line in this context
                error_message = line.strip()
                for ctx_line in context[2:]:  # Skip first 2 lines of context
                    if (
                        "error:" in ctx_line.lower()
                        or "failed" in ctx_line.lower()
                        or "cannot" in ctx_line.lower()
                    ):
                        error_message = ctx_line.strip()
                        break

                return error_message, context

    return None, []


def _find_useful_error_lines(lines: list[str]) -> list[str]:
    """Find lines that might contain useful failure information."""
    useful_lines = []
    error_keywords = [
        "error",
        "fail",
        "exception",
        "cannot",
        "unable",
        "missing",
        "not found",
        "denied",
        "timeout",
        "refused",
    ]

    for line in lines:
        line_stripped = line.strip()
        if (
            line_stripped
            and len(line_stripped) > 10
            and any(word in line_stripped.lower() for word in error_keywords)
            and not line_stripped.startswith("INFO")
            and not line_stripped.startswith("DEBUG")
        ):
            useful_lines.append(line_stripped)

    return useful_lines


def _enhance_error_extraction(
    lines: list[str], error_message: Optional[str], error_context: list[str]
) -> tuple[Optional[str], list[str]]:
    """Enhance error extraction with detailed and fallback methods."""
    # Try detailed extraction if primary method didn't find enough
    if not error_message or len(error_context) < 3:
        detailed_error, detailed_context = extract_detailed_error_info(lines)
        if detailed_error:
            return detailed_error, detailed_context

    # Fallback to useful lines if still no good error info
    if not error_message and lines:
        useful_lines = _find_useful_error_lines(lines)
        if useful_lines:
            return useful_lines[0], useful_lines[:10]

    return error_message, error_context


def analyze_logs(logs: str) -> LogAnalysis:
    """Analyze build logs to extract failure information.

    Args:
        logs: Raw log content

    Returns:
        LogAnalysis object with extracted information
    """
    cleaned_logs = clean_log_content(logs)
    lines = cleaned_logs.split("\n")

    failing_command = extract_failing_command(lines)
    error_message, error_context = find_error_message_and_context(lines)

    # Enhance error extraction with fallback methods
    error_message, error_context = _enhance_error_extraction(
        lines, error_message, error_context
    )

    return LogAnalysis(
        failing_command=failing_command,
        error_message=error_message,
        error_context=error_context,
    )
