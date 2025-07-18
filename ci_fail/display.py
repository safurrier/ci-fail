"""Display and formatting functions for console output."""

import os
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ci_fail.api import get_job_details, get_job_failures
from ci_fail.config import Config
from ci_fail.models import BuildkiteFailure, ChecksStatus, JobFailure

console = Console()


# === DISPLAY HELPERS ===


def create_command_panel(command: str, title: str = "🔧 Failing Command") -> Panel:
    """Create a formatted panel for displaying commands."""
    return Panel(
        Syntax(command, "bash", theme="monokai", line_numbers=False),
        title=title,
        border_style="yellow",
    )


def create_error_panel(error: str, title: str = "❌ Error Message") -> Panel:
    """Create a formatted panel for displaying errors."""
    return Panel(error, title=title, border_style="red")


def create_context_panel(context: list[str], title: str = "📝 Error Context") -> Panel:
    """Create a formatted panel for displaying error context."""
    context_text = "\n".join(context)
    return Panel(
        Syntax(context_text, "text", theme="monokai", line_numbers=True),
        title=title,
        border_style="red",
    )


def create_info_panel(info: str, title: str, border_style: str = "blue") -> Panel:
    """Create a formatted panel for displaying information."""
    return Panel(info, title=title, border_style=border_style)


def display_job_details(
    details: JobFailure,
    job_failure: JobFailure,
    job_number: int,
    build_id: Optional[str] = None,
    pipeline_slug: Optional[str] = None,
) -> None:
    """Display detailed job failure information.

    Args:
        details: Detailed job failure information
        job_failure: Basic job failure information
        job_number: Job number for display
        build_id: Build ID for pro tip commands
        pipeline_slug: Pipeline slug for pro tip commands
    """
    # Show CI Command that failed
    if details.failing_command:
        console.print(
            create_command_panel(details.failing_command, "🔧 CI Command (Failed)")
        )

    # Show error message
    if details.error_message:
        console.print(create_error_panel(details.error_message))

    # Show error context with line numbers
    if details.error_context and "\n".join(details.error_context).strip():
        console.print(create_context_panel(details.error_context))

    # Job info panel
    job_info = f"🆔 Job ID: {job_failure.job_id}"
    if not details.failing_command and not details.error_message:
        job_info += "\n❌ Could not extract detailed failure information"

    console.print(
        create_info_panel(
            job_info,
            title=f"Job {job_number}: {job_failure.job_name}",
            border_style="blue",
        )
    )

    # Add pro tip for getting full logs
    if build_id and pipeline_slug:
        console.print(
            create_info_panel(
                f"💡 For complete logs: cifail logs {build_id} --pipeline-slug {pipeline_slug}",
                title="Pro Tip",
                border_style="green",
            )
        )


def display_job_summary(job_failure: JobFailure, job_number: int) -> None:
    """Display summary job failure information.

    Args:
        job_failure: Job failure information
        job_number: Job number for display
    """
    job_info = f"🆔 Job ID: {job_failure.job_id}\n\n💡 Use --detailed to get failing commands and errors"
    console.print(
        create_info_panel(
            job_info,
            title=f"Job {job_number}: {job_failure.job_name}",
            border_style="red",
        )
    )


def display_checks_status(status: ChecksStatus) -> None:
    """Display comprehensive status of CI checks.

    Args:
        status: ChecksStatus object with complete status information
    """
    # Create status table
    table = Table(title="CI Checks Status", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Count", style="white", width=10)
    table.add_column("Status", style="white", width=15)

    # Add rows with appropriate styling
    table.add_row("Total Checks", str(status.total_checks), "")
    table.add_row("Buildkite Checks", str(status.buildkite_checks), "")

    # Running checks
    running_status = "🔄 In Progress" if status.running_checks > 0 else "⏸️ None"
    table.add_row("Running", str(status.running_checks), running_status)

    # Passed checks
    passed_status = "✅ Passing" if status.passed_checks > 0 else "❌ None"
    table.add_row("Passed", str(status.passed_checks), passed_status)

    # Failed checks
    failed_status = "❌ Failing" if status.failed_checks > 0 else "✅ None"
    table.add_row("Failed", str(status.failed_checks), failed_status)

    # Other states (combine non-actionable states)
    other_count = (
        status.neutral_checks
        + status.cancelled_checks
        + status.skipped_checks
        + status.timed_out_checks
    )
    if other_count > 0:
        other_status = "⚪ Neutral/Other"
        table.add_row("Other", str(other_count), other_status)

    # Success rate - only count actionable checks (passed + failed)
    actionable_checks = status.passed_checks + status.failed_checks
    if actionable_checks > 0:
        success_rate = (status.passed_checks / actionable_checks) * 100
        rate_display = f"{success_rate:.1f}%"
        table.add_row("Success Rate", rate_display, "")

    console.print(table)


def _display_trigger_job_info(failure: BuildkiteFailure) -> None:
    """Display information for trigger jobs in main pipeline."""
    console.print(
        create_info_panel(
            f"🔗 Build Link: {failure.link}\n📝 Description: {failure.description}",
            title="Main Pipeline Build (Contains Trigger Jobs)",
            border_style="blue",
        )
    )

    console.print(
        create_info_panel(
            f"💡 This build contains trigger jobs that spawn the failing builds shown above.\n"
            f"The actual failures are in the individual triggered pipeline builds.\n"
            f"Use 'cifail logs {failure.build_id} --pipeline-slug {failure.pipeline_name}' to see trigger job details.",
            title="About Trigger Jobs",
            border_style="yellow",
        )
    )


def _display_build_info_fallback(failure: BuildkiteFailure) -> None:
    """Display fallback build information when job details unavailable."""
    console.print(
        create_info_panel(
            f"🔗 Build Link: {failure.link}\n📝 Description: {failure.description}",
            title="Build Information",
            border_style="blue",
        )
    )
    console.print(
        create_info_panel(
            f"💡 Use 'cifail logs {failure.build_id} --pipeline-slug {failure.pipeline_name}' for detailed logs.",
            title="Getting Detailed Logs",
            border_style="yellow",
        )
    )


def _display_job_failures(failure: BuildkiteFailure) -> None:
    """Display detailed job failure information."""
    try:
        job_failures = get_job_failures(failure.build_id, failure.pipeline_name)
        if job_failures:
            for i, job_failure in enumerate(job_failures, 1):
                details = get_job_details(
                    failure.build_id, job_failure.job_id, failure.pipeline_name
                )
                display_job_details(
                    details, job_failure, i, failure.build_id, failure.pipeline_name
                )
                if i < len(job_failures):
                    console.print()  # Add spacing between jobs
        else:
            _display_build_info_fallback(failure)
    except Exception:
        _display_build_info_fallback(failure)


def display_failure_details(failure: BuildkiteFailure, number: int) -> None:
    """Display detailed failure information for a specific failure.

    Args:
        failure: BuildkiteFailure object
        number: Failure number for display
    """
    console.print(f"\n[bold red]💥 Failure #{number}: {failure.name}[/bold red]")

    main_pipeline = os.getenv("BUILDKITE_MAIN_PIPELINE", Config.DEFAULT_MAIN_PIPELINE)
    is_main_org_pipeline = failure.pipeline_name == main_pipeline

    if is_main_org_pipeline:
        _display_trigger_job_info(failure)
    else:
        _display_job_failures(failure)


def format_jobs_human(
    build_id: str, pipeline_slug: str, job_failures: list[JobFailure], detailed: bool
) -> None:
    """Format job failures for human consumption.

    Args:
        build_id: Build ID
        pipeline_slug: Pipeline slug
        job_failures: List of job failures
        detailed: Whether to show detailed information
    """
    console.print(f"💥 Found {len(job_failures)} failed jobs:", style="red")

    for i, job_failure in enumerate(job_failures, 1):
        if detailed:
            details = get_job_details(build_id, job_failure.job_id, pipeline_slug)
            display_job_details(details, job_failure, i, build_id, pipeline_slug)
        else:
            display_job_summary(job_failure, i)

        console.print()  # Add spacing between jobs

    # Add helpful footer
    console.print(
        create_info_panel(
            f"💡 Full logs command: bk api /pipelines/{pipeline_slug}/builds/{build_id}/jobs/<job-id>/log",
            title="Pro Tip",
        )
    )


def format_jobs_json(
    build_id: str, pipeline_slug: str, job_failures: list[JobFailure], detailed: bool
) -> dict:
    """Format job failures as JSON output.

    Args:
        build_id: Build ID
        pipeline_slug: Pipeline slug
        job_failures: List of job failures
        detailed: Whether to include detailed information

    Returns:
        Dictionary ready for JSON serialization
    """
    jobs_data = []
    for job_failure in job_failures:
        job_data = {"job_id": job_failure.job_id, "job_name": job_failure.job_name}

        if detailed:
            details = get_job_details(build_id, job_failure.job_id, pipeline_slug)
            job_data.update(
                {
                    "failing_command": details.failing_command,
                    "error_message": details.error_message,
                    "error_context": details.error_context,
                }
            )

        jobs_data.append(job_data)

    return {
        "build_id": build_id,
        "pipeline_slug": pipeline_slug,
        "failed_jobs": jobs_data,
    }


def _format_checks_json_output(
    status: ChecksStatus, pr_info: tuple[str, str, str]
) -> dict:
    """Format checks status as JSON output.

    Args:
        status: ChecksStatus object with complete status information
        pr_info: Tuple of (pr_number, pr_url, pr_title)

    Returns:
        Dictionary ready for JSON serialization
    """
    pr_number, pr_url, pr_title = pr_info

    return {
        "pr_number": pr_number,
        "pr_url": pr_url,
        "total_checks": status.total_checks,
        "buildkite_checks": status.buildkite_checks,
        "running_checks": status.running_checks,
        "passed_checks": status.passed_checks,
        "failed_checks": status.failed_checks,
        "neutral_checks": status.neutral_checks,
        "cancelled_checks": status.cancelled_checks,
        "skipped_checks": status.skipped_checks,
        "timed_out_checks": status.timed_out_checks,
        "failing_checks": [
            {
                "name": f.name,
                "description": f.description,
                "link": f.link,
                "build_id": f.build_id,
                "pipeline_name": f.pipeline_name,
            }
            for f in status.failures
        ],
        "in_progress_checks": [
            {
                "name": f.name,
                "description": f.description,
                "link": f.link,
                "build_id": f.build_id,
                "pipeline_name": f.pipeline_name,
            }
            for f in status.in_progress
        ],
    }


def _display_checks_basic_info(
    status: ChecksStatus, pr_info: tuple[str, str, str]
) -> None:
    """Display basic PR and checks information.

    Args:
        status: ChecksStatus object with complete status information
        pr_info: Tuple of (pr_number, pr_url, pr_title)
    """
    pr_number, pr_url, pr_title = pr_info

    console.print(f"📝 PR #{pr_number} - {pr_title}", style="cyan")
    console.print(f"🔗 {pr_url}", style="blue")
    display_checks_status(status)


def _display_in_progress_checks(status: ChecksStatus) -> None:
    """Display in-progress checks table.

    Args:
        status: ChecksStatus object with complete status information
    """
    if not status.in_progress:
        return

    console.print("\n🔄 Buildkite In Progress:", style="yellow")

    table = Table(title="In Progress Buildkite Checks")
    table.add_column("#", style="dim", width=3)
    table.add_column("Pipeline", style="cyan")
    table.add_column("Build ID", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Link", style="blue")

    for i, check in enumerate(status.in_progress, 1):
        table.add_row(
            str(i), check.pipeline_name, check.build_id, check.description, check.link
        )

    console.print(table)


def _display_failed_checks(status: ChecksStatus, detailed: bool) -> None:
    """Display failed checks table and optionally detailed info.

    Args:
        status: ChecksStatus object with complete status information
        detailed: Whether to show detailed failure information
    """
    if not status.failures:
        return

    console.print("\n💥 Buildkite Failures:", style="red")

    table = Table(title="Failing Buildkite Checks")
    table.add_column("#", style="dim", width=3)
    table.add_column("Pipeline", style="cyan")
    table.add_column("Build ID", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Link", style="blue")

    for i, failure in enumerate(status.failures, 1):
        table.add_row(
            str(i),
            failure.pipeline_name,
            failure.build_id,
            failure.description,
            failure.link,
        )

    console.print(table)

    # Show detailed info if --detailed flag is used
    if detailed:
        for i, failure in enumerate(status.failures, 1):
            display_failure_details(failure, i)


def _display_status_messages_and_suggestions(
    status: ChecksStatus, detailed: bool, detail: Optional[str]
) -> None:
    """Display status messages and smart suggestions.

    Args:
        status: ChecksStatus object with complete status information
        detailed: Whether detailed info was shown
        detail: Whether specific detail was requested
    """
    # Show status message
    if not status.failures and not status.in_progress:
        console.print(
            "\n✅ No failing or in-progress Buildkite checks found", style="green"
        )
    elif not status.failures:
        console.print("\n✅ No failing Buildkite checks found", style="green")
    elif not status.in_progress:
        console.print("\n⏸️ No in-progress Buildkite checks found", style="yellow")

    # Add smart suggestions if there are failures and no detailed info was shown
    if status.failures and not detailed and not detail:
        suggestions = []

        # Quick detail commands
        if len(status.failures) == 1:
            suggestions.append("cifail checks --detail 1")
        else:
            suggestions.append("cifail checks --detail 1,2")
        suggestions.append("cifail checks --detailed")

        # Full logs commands
        for _i, failure in enumerate(status.failures, 1):
            suggestions.append(
                f"cifail logs {failure.build_id} --pipeline-slug {failure.pipeline_name}"
            )

        # Add explanations for commands
        suggestion_explanations = [
            f"  • {suggestions[0]} - Show details for specific failures",
            f"  • {suggestions[1]} - Show all failure details inline",
            f"  • {suggestions[2]} - Get complete build logs"
            if len(suggestions) > 2
            else None,
            f"  • {suggestions[3]} - Get complete build logs"
            if len(suggestions) > 3
            else None,
        ]

        suggestion_text = "\n".join(
            filter(None, suggestion_explanations[:4])
        )  # Show max 4 suggestions

        # Add additional context about when to use full logs
        if len(status.failures) > 0:
            suggestion_text += "\n\n💡 Tips:"
            suggestion_text += "\n  • If failure details are incomplete, use 'cifail logs' for complete build logs"
            suggestion_text += "\n  • For trigger jobs, look at the triggered pipeline jobs above for actual failures"
            suggestion_text += "\n  • Trigger jobs spawn sub-pipelines - the real errors are in the triggered jobs"

        console.print(
            create_info_panel(
                f"💡 Next steps:\n{suggestion_text}",
                title="Quick Actions",
                border_style="blue",
            )
        )
