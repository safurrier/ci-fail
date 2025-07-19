"""Click CLI commands for CI failure analysis."""

import json
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ci_fail.api import get_checks_status, get_job_failures, get_pr_info
from ci_fail.config import Config
from ci_fail.display import (
    _display_checks_basic_info,
    _display_failed_checks,
    _display_in_progress_checks,
    _display_status_messages_and_suggestions,
    _format_checks_json_output,
    create_command_panel,
    create_context_panel,
    create_error_panel,
    create_info_panel,
    format_jobs_human,
    format_jobs_json,
)
from ci_fail.models import (
    APIError,
    ChecksStatus,
    CommandNotFoundError,
    OutputFormat,
    ValidationError,
)
from ci_fail.utils import (
    check_configuration_full,
    check_configuration_quick,
    check_prerequisites,
    run_command,
    validate_build_input,
)

console = Console()


def parse_detail_numbers(detail_str: str) -> list[int]:
    """Parse detail numbers from string like "1" or "1,3,5".

    Args:
        detail_str: String containing comma-separated numbers

    Returns:
        List of integers

    Raises:
        ValidationError: If parsing fails
    """
    if not detail_str:
        return []

    try:
        numbers = []
        for num_str in detail_str.split(","):
            num = int(num_str.strip())
            if num <= 0:
                raise ValidationError(f"Detail number must be positive: {num}")
            numbers.append(num)
        return numbers
    except ValueError:
        raise ValidationError(
            f"Invalid detail numbers: {detail_str}. Use format like '1' or '1,3,5'"
        )


def _handle_specific_detail_request(status: ChecksStatus, detail: str) -> None:
    """Handle specific detail number requests.

    Args:
        status: ChecksStatus object with complete status information
        detail: Detail numbers string (e.g., "1" or "1,3")

    Raises:
        ValidationError: If detail numbers are invalid
    """
    from ci_fail.display import display_failure_details

    detail_numbers = parse_detail_numbers(detail)
    for num in detail_numbers:
        if num <= len(status.failures):
            display_failure_details(status.failures[num - 1], num)
        else:
            console.print(
                f"\n❌ Failure #{num} not found. Only {len(status.failures)} failures available.",
                style="red",
            )


@click.group()
def cli() -> None:
    """CI failure analysis tool for GitHub + Buildkite workflows.

    Note: Buildkite CLI may create .bk.yaml files - add to .gitignore.
    """
    pass


def _validate_token_setup() -> Optional[str]:
    """Validate API token setup and provide user guidance if missing."""
    token = os.getenv("BUILDKITE_API_TOKEN")
    if not token:
        console.print("❌ BUILDKITE_API_TOKEN not set", style="red")
        console.print(
            "   1. Create token at: https://buildkite.com/user/api-access-tokens"
        )
        console.print(
            '   2. Set environment variable: export BUILDKITE_API_TOKEN="your-token"'
        )
        console.print(
            "   3. Optional: Set BUILDKITE_ORG=\"your-org\" (defaults to 'discord')"
        )
        console.print(
            "   4. Optional: Set BUILDKITE_MAIN_PIPELINE=\"your-main-pipeline\" (defaults to 'discord')"
        )
        console.print("   5. Reload shell or restart terminal")
        return None

    console.print("✅ BUILDKITE_API_TOKEN is set", style="green")
    return token


def _configure_buildkite_cli(token: str, org: str) -> bool:
    """Configure Buildkite CLI in home directory to avoid local files."""
    console.print("⚙️  Configuring CLI...", style="cyan")
    os.environ["ACCESSIBLE"] = "true"

    original_cwd = os.getcwd()
    try:
        os.chdir(Path.home())
        result = run_command(
            ["bk", "configure", "--force", "--token", token, "--org", org]
        )
        return result.returncode == 0
    finally:
        os.chdir(original_cwd)


def _post_configuration_setup(org: str) -> None:
    """Handle post-configuration tasks: cleanup, org setup, validation."""
    # Show where config was saved
    config_path = Path.home() / ".config" / "bk.yaml"
    console.print(f"📁 Configuration saved to: {config_path}", style="blue")

    # Clean up any stray .bk.yaml files in the current directory
    local_config = Path(".bk.yaml")
    if local_config.exists():
        local_config.unlink()
        console.print("🧹 Cleaned up local .bk.yaml file", style="yellow")

    # Set the default organization
    console.print("🔧 Setting default organization...", style="cyan")
    try:
        run_command(["bk", "use", org])
        console.print(f"✅ Default organization set to: {org}", style="green")
    except Exception as e:
        console.print(f"⚠️  Warning: Could not set default org: {e}", style="yellow")

    # Test the configuration with full API validation
    console.print("🧪 Testing configuration...", style="cyan")
    try:
        check_configuration_full()
        console.print("✅ Configuration test successful", style="green")
    except APIError as e:
        console.print("❌ Configuration test failed", style="red")
        console.print(f"   Error: {e}")


@cli.command()
def configure() -> None:
    """Configure Buildkite CLI with authentication."""
    console.print("🔧 Configuring Buildkite CLI...", style="cyan")

    try:
        check_prerequisites()

        token = _validate_token_setup()
        if not token:
            return

        org = os.getenv("BUILDKITE_ORG", Config.DEFAULT_ORG)

        if _configure_buildkite_cli(token, org):
            console.print("✅ Buildkite CLI configured successfully", style="green")
            _post_configuration_setup(org)
        else:
            console.print("❌ Failed to configure Buildkite CLI", style="red")

    except CommandNotFoundError as e:
        console.print(f"❌ {e}", style="red")
        console.print(f"   {e.install_message}")
    except APIError as e:
        console.print(f"❌ Configuration failed: {e}", style="red")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")


def _validate_git_repository() -> bool:
    """Validate we're in a git repository."""
    if not Path(".git").exists():
        console.print("❌ Not in a git repository", style="red")
        return False
    return True


def _get_pr_info_with_validation() -> Optional[tuple[str, str, str]]:
    """Get PR info with user-friendly error handling."""
    pr_info = get_pr_info()
    if not pr_info:
        console.print("❌ No PR found for current branch", style="red")
        console.print("   Create PR with: gh pr create")
        return None
    return pr_info


def _handle_checks_output(
    format_enum: OutputFormat,
    status: ChecksStatus,
    pr_info: tuple[str, str, str],
    detailed: bool,
    detail: Optional[str],
) -> None:
    """Handle output formatting for checks command."""
    if format_enum == OutputFormat.JSON:
        output = _format_checks_json_output(status, pr_info)
        console.print(json.dumps(output, indent=2))
    else:
        _display_checks_basic_info(status, pr_info)

        # Handle specific detail numbers
        if detail:
            try:
                _handle_specific_detail_request(status, detail)
                return
            except ValidationError as e:
                console.print(f"\n❌ {e}", style="red")
                return

        # Show detailed tables
        _display_in_progress_checks(status)
        _display_failed_checks(status, detailed)
        _display_status_messages_and_suggestions(status, detailed, detail)


@cli.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.HUMAN.value,
    help="Output format",
)
@click.option(
    "--detailed", is_flag=True, help="Show detailed failure information inline"
)
@click.option(
    "--detail", help='Show details for specific failure numbers (e.g., "1" or "1,3")'
)
def checks(output_format: str, detailed: bool, detail: Optional[str]) -> None:
    """Get CI checks status from GitHub PR.

    Examples:
        cifail checks                    # Show status overview
        cifail checks --detailed         # Show all failure details inline
        cifail checks --detail 1         # Show details for failure #1
        cifail checks --detail 1,3       # Show details for failures #1 and #3
    """
    try:
        check_prerequisites()
        check_configuration_quick()
        format_enum = OutputFormat(output_format)

        if not _validate_git_repository():
            return

        pr_info = _get_pr_info_with_validation()
        if not pr_info:
            return

        status = get_checks_status()
        _handle_checks_output(format_enum, status, pr_info, detailed, detail)

    except CommandNotFoundError as e:
        console.print(f"❌ {e}", style="red")
        console.print(f"   {e.install_message}")
    except APIError as e:
        console.print(f"❌ API error: {e}", style="red")
    except ValidationError as e:
        console.print(f"❌ Validation error: {e}", style="red")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")


@cli.command()
@click.argument("build_id")
@click.option(
    "--detailed",
    is_flag=True,
    help="Get detailed failure information including commands and errors",
)
@click.option(
    "--pipeline-slug", help="Pipeline slug (will be extracted from URL if not provided)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.HUMAN.value,
    help="Output format",
)
def logs(
    build_id: str, detailed: bool, pipeline_slug: Optional[str], output_format: str
) -> None:
    """Get logs for a specific Buildkite build."""
    try:
        check_prerequisites()
        check_configuration_quick()
        format_enum = OutputFormat(output_format)

        # Parse build ID and pipeline slug
        build_id, parsed_pipeline_slug = validate_build_input(build_id)
        if parsed_pipeline_slug:
            pipeline_slug = parsed_pipeline_slug
            if format_enum == OutputFormat.HUMAN:
                console.print(
                    f"📋 Extracted pipeline: {pipeline_slug}, build: {build_id}"
                )

        if not pipeline_slug:
            if format_enum == OutputFormat.HUMAN:
                console.print(
                    "❌ Pipeline slug is required. Provide URL or use --pipeline-slug option.",
                    style="red",
                )
            return

        if format_enum == OutputFormat.HUMAN:
            console.print(
                f"🔍 Getting logs for build {build_id} in pipeline {pipeline_slug}...",
                style="cyan",
            )

        # Get failed jobs
        job_failures = get_job_failures(build_id, pipeline_slug)

        if not job_failures:
            if format_enum == OutputFormat.JSON:
                console.print(
                    json.dumps(
                        {
                            "build_id": build_id,
                            "pipeline_slug": pipeline_slug,
                            "failed_jobs": [],
                        },
                        indent=2,
                    )
                )
            else:
                console.print("✅ No failed jobs found", style="green")
            return

        # Format output
        if format_enum == OutputFormat.JSON:
            output = format_jobs_json(build_id, pipeline_slug, job_failures, detailed)
            console.print(json.dumps(output, indent=2))
        else:
            format_jobs_human(build_id, pipeline_slug, job_failures, detailed)

    except CommandNotFoundError as e:
        console.print(f"❌ {e}", style="red")
        console.print(f"   {e.install_message}")
    except APIError as e:
        console.print(f"❌ API error: {e}", style="red")
    except ValidationError as e:
        console.print(f"❌ Validation error: {e}", style="red")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")


@cli.command()
@click.argument("job_id")
@click.argument("build_id")
@click.argument("pipeline_slug")
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat]),
    default=OutputFormat.HUMAN.value,
    help="Output format",
)
def job(job_id: str, build_id: str, pipeline_slug: str, output_format: str) -> None:
    """Get detailed information about a specific failed job."""
    try:
        check_prerequisites()
        check_configuration_quick()

        # Convert string to enum
        format_enum = OutputFormat(output_format)

        if format_enum == OutputFormat.HUMAN:
            console.print(f"🔍 Getting details for job {job_id}...", style="cyan")

        from ci_fail.api import get_job_details

        details = get_job_details(build_id, job_id, pipeline_slug)

        if format_enum == OutputFormat.JSON:
            # JSON output
            output = {
                "job_id": job_id,
                "build_id": build_id,
                "pipeline_slug": pipeline_slug,
                "failing_command": details.failing_command,
                "error_message": details.error_message,
                "error_context": details.error_context,
            }
            console.print(json.dumps(output, indent=2))
        else:
            # Human-readable output with improved formatting
            if details.failing_command:
                console.print(create_command_panel(details.failing_command))

            if details.error_message:
                console.print(create_error_panel(details.error_message))

            if details.error_context and "\n".join(details.error_context).strip():
                console.print(create_context_panel(details.error_context))

            if (
                not details.failing_command
                and not details.error_message
                and not details.error_context
            ):
                console.print(
                    create_error_panel(
                        "❌ Could not extract failure details", title=f"Job {job_id}"
                    )
                )

            # Add helpful footer
            console.print(
                create_info_panel(
                    f"💡 Full logs: bk api /pipelines/{pipeline_slug}/builds/{build_id}/jobs/{job_id}/log",
                    title="Pro Tip",
                )
            )

    except CommandNotFoundError as e:
        console.print(f"❌ {e}", style="red")
        console.print(f"   {e.install_message}")
    except APIError as e:
        console.print(f"❌ API error: {e}", style="red")
    except ValidationError as e:
        console.print(f"❌ Validation error: {e}", style="red")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")


if __name__ == "__main__":
    cli()
