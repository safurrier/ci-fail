"""Shared utility functions for CI failure analysis."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from ci_fail.config import Config, Patterns
from ci_fail.models import APIError, CommandNotFoundError, ValidationError


def run_command(
    cmd: list[str], capture_output: bool = True, timeout: int = Config.DEFAULT_TIMEOUT
) -> subprocess.CompletedProcess:
    """Run a command with error handling.

    Args:
        cmd: Command and arguments to run
        capture_output: Whether to capture stdout/stderr
        timeout: Timeout in seconds

    Returns:
        CompletedProcess result

    Raises:
        CommandNotFoundError: If command is not found
        APIError: If command times out
    """
    # SECURITY WARNING: This function executes arbitrary commands from a limited set.
    # While we only call known commands (gh, bk, which), there's still potential for
    # argument injection if user input is not properly sanitized upstream.
    # shell=False provides some protection but arguments should still be validated.

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
            timeout=timeout,
            shell=False,  # Explicitly set for security
        )
        return result
    except FileNotFoundError:
        install_msg = Config.REQUIRED_TOOLS.get(cmd[0], f"Install {cmd[0]}")
        raise CommandNotFoundError(cmd[0], install_msg)
    except subprocess.TimeoutExpired:
        raise APIError(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")


def check_prerequisites() -> None:
    """Check if required tools are installed.

    Raises:
        CommandNotFoundError: If any required tool is missing
    """
    missing = []
    for tool, install_msg in Config.REQUIRED_TOOLS.items():
        try:
            result = run_command(["which", tool])
            if result.returncode != 0:
                missing.append((tool, install_msg))
        except CommandNotFoundError:
            missing.append((tool, install_msg))

    if missing:
        error_msg = "Missing required tools:\n"
        for _tool, msg in missing:
            error_msg += f"   • {msg}\n"
        raise CommandNotFoundError("prerequisites", error_msg.strip())


def check_configuration_full() -> None:
    """Check if required tools are properly configured with API validation.

    Raises:
        APIError: If any required tool is not configured
    """
    # Check GitHub CLI authentication
    try:
        result = run_command(["gh", "auth", "status"])
        if result.returncode != 0:
            raise APIError(
                "GitHub CLI is not authenticated.\n"
                "   Run: gh auth login\n"
                "   Or ensure you have a valid GitHub token"
            )
    except CommandNotFoundError:
        pass  # Will be caught by check_prerequisites

    # Check Buildkite CLI configuration
    try:
        result = run_command(["bk", "api", "/pipelines"])
        if result.returncode != 0:
            # Check if it's an auth issue vs config issue
            if (
                "authentication" in result.stderr.lower()
                or "token" in result.stderr.lower()
            ):
                raise APIError(
                    "Buildkite CLI is not properly configured.\n"
                    "   Run: cifail configure\n"
                    "   Or ensure BUILDKITE_API_TOKEN is set as an environment variable"
                )
            else:
                raise APIError(f"Buildkite API error: {result.stderr}")
    except CommandNotFoundError:
        pass  # Will be caught by check_prerequisites


def check_configuration_quick() -> None:
    """Quick local-only configuration check with warnings.

    Warns about potential configuration issues without failing.
    """
    warnings = []

    # Check GitHub CLI config
    gh_config = Path.home() / ".config/gh/hosts.yml"
    if not gh_config.exists():
        warnings.append("⚠️  GitHub CLI may not be configured. Run: gh auth login")

    # Check Buildkite CLI config
    bk_config = Path.home() / ".config/bk.yaml"
    if not bk_config.exists():
        warnings.append("⚠️  Buildkite CLI may not be configured. Run: cifail configure")

    # Check environment variable
    if not os.getenv("BUILDKITE_API_TOKEN"):
        warnings.append("⚠️  BUILDKITE_API_TOKEN not set in environment")

    # Show warnings if any
    if warnings:
        from rich.console import Console

        console = Console()
        for warning in warnings:
            console.print(warning, style="yellow")
        console.print(
            "💡 Run 'cifail configure' to set up authentication", style="blue"
        )


def validate_api_response(response_data: dict, required_fields: list[str]) -> bool:
    """Validate API response has required fields.

    Args:
        response_data: The API response data
        required_fields: List of required field names

    Returns:
        True if validation passes

    Raises:
        ValidationError: If validation fails
    """
    try:
        for field in required_fields:
            if field not in response_data:
                raise ValidationError(f"Missing required field: {field}")
        return True
    except (TypeError, AttributeError):
        raise ValidationError("Invalid API response format")


def validate_build_input(url_or_build_id: str) -> tuple[str, Optional[str]]:
    """Validate and parse Buildkite URL or build ID.

    Args:
        url_or_build_id: Either a Buildkite URL or build ID

    Returns:
        Tuple of (build_id, pipeline_slug)

    Raises:
        ValidationError: If input is invalid
    """
    if not url_or_build_id.strip():
        raise ValidationError("URL or build ID cannot be empty")

    if url_or_build_id.startswith("https://"):
        return _parse_buildkite_url(url_or_build_id)

    if not url_or_build_id.isdigit():
        raise ValidationError("Build ID must be numeric")

    return url_or_build_id, None


def _parse_buildkite_url(url: str) -> tuple[str, str]:
    """Parse Buildkite URL to extract build ID and pipeline.

    Args:
        url: Buildkite URL

    Returns:
        Tuple of (build_id, pipeline_slug)

    Raises:
        ValidationError: If URL cannot be parsed
    """
    if not url.startswith("https://buildkite.com/"):
        raise ValidationError("Only Buildkite URLs are supported")

    match = Patterns.BUILDKITE_URL.search(url)
    if not match:
        raise ValidationError("Could not extract pipeline and build ID from URL")

    return match.group(2), match.group(1)  # build_id, pipeline_slug


def handle_api_response(result: subprocess.CompletedProcess, context: str) -> str:
    """Standard API response handler.

    Args:
        result: Command execution result
        context: Context description for error messages

    Returns:
        Command stdout if successful

    Raises:
        APIError: If command failed
    """
    if result.returncode != 0:
        raise APIError(f"Failed to {context}: {result.stderr}")
    return result.stdout


def parse_json_response(response: str, context: str) -> dict | list:
    """Standard JSON response parser.

    Args:
        response: JSON response string
        context: Context description for error messages

    Returns:
        Parsed JSON dictionary

    Raises:
        APIError: If JSON parsing fails
    """
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise APIError(f"Error parsing {context}: {e}")


def parse_log_response(response: str) -> str:
    """Parse log response, handling both JSON and raw text formats.

    Args:
        response: API response that might be JSON or raw text

    Returns:
        Extracted log content
    """
    try:
        log_data = json.loads(response)
        if isinstance(log_data, dict) and "content" in log_data:
            return log_data["content"]
        return response
    except json.JSONDecodeError:
        return response
