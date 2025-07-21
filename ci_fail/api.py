"""API interactions for GitHub and Buildkite."""

from typing import Any, Optional

from ci_fail.analysis import analyze_logs
from ci_fail.config import Patterns
from ci_fail.models import (
    APIError,
    BuildkiteFailure,
    BuildkiteInProgress,
    ChecksStatus,
    JobFailure,
    ValidationError,
)
from ci_fail.utils import (
    handle_api_response,
    parse_json_response,
    parse_log_response,
    run_command,
    validate_api_response,
)


def get_pr_info() -> Optional[tuple[str, str, str]]:
    """Get PR number, URL, and title for current branch.

    Returns:
        Tuple of (pr_number, pr_url, pr_title) or None if not found

    Raises:
        APIError: If API call fails
    """
    try:
        result = run_command(["gh", "pr", "view", "--json", "number,url,title"])
        if result.returncode != 0:
            return None

        data = parse_json_response(result.stdout, "PR data")
        if isinstance(data, list):
            raise APIError("Expected dict for PR data, got list")
        validate_api_response(data, ["number", "url", "title"])
        return str(data["number"]), data["url"], data["title"]
    except ValidationError:
        raise APIError("Invalid PR response format")


def get_pr_number() -> Optional[str]:
    """Get PR number for current branch.

    Returns:
        PR number as string, or None if not found

    Raises:
        APIError: If API call fails
    """
    pr_info = get_pr_info()
    return pr_info[0] if pr_info else None


def _count_check_states(
    checks: list[dict[str, Any]],
) -> tuple[int, int, int, int, int, int, int, int]:
    """Count checks by state.

    Args:
        checks: List of check dictionaries from GitHub API

    Returns:
        Tuple of (running, passed, failed, neutral, cancelled, skipped, timed_out, buildkite)
    """
    running = sum(1 for c in checks if c.get("state") in ("IN_PROGRESS", "PENDING"))
    passed = sum(1 for c in checks if c.get("state") == "SUCCESS")
    failed = sum(1 for c in checks if c.get("state") == "FAILURE")
    neutral = sum(1 for c in checks if c.get("state") == "NEUTRAL")
    cancelled = sum(1 for c in checks if c.get("state") == "CANCELLED")
    skipped = sum(1 for c in checks if c.get("state") == "SKIPPED")
    timed_out = sum(1 for c in checks if c.get("state") == "TIMED_OUT")
    buildkite = sum(1 for c in checks if "buildkite" in c.get("link", ""))
    return running, passed, failed, neutral, cancelled, skipped, timed_out, buildkite


def _extract_buildkite_failures(checks: list[dict[str, Any]]) -> list[BuildkiteFailure]:
    """Extract Buildkite failures from checks.

    Args:
        checks: List of check dictionaries from GitHub API

    Returns:
        List of BuildkiteFailure objects
    """
    failures = []
    for check in checks:
        if check.get("state") == "FAILURE" and "buildkite" in check.get("link", ""):
            match = Patterns.BUILDKITE_URL.search(check.get("link", ""))
            if match:
                failures.append(
                    BuildkiteFailure(
                        name=check["name"],
                        description=check.get("description", ""),
                        link=check["link"],
                        build_id=match.group(2),
                        pipeline_name=match.group(1),
                    )
                )
    return failures


def _extract_buildkite_in_progress(
    checks: list[dict[str, Any]],
) -> list[BuildkiteInProgress]:
    """Extract in-progress Buildkite checks.

    Args:
        checks: List of check dictionaries from GitHub API

    Returns:
        List of BuildkiteInProgress objects
    """
    in_progress = []
    for check in checks:
        state = check.get("state")
        if state in ("IN_PROGRESS", "PENDING") and "buildkite" in check.get("link", ""):
            match = Patterns.BUILDKITE_URL.search(check.get("link", ""))
            if match:
                in_progress.append(
                    BuildkiteInProgress(
                        name=check["name"],
                        description=check.get("description", ""),
                        link=check["link"],
                        build_id=match.group(2),
                        pipeline_name=match.group(1),
                    )
                )
    return in_progress


def get_checks_status() -> ChecksStatus:
    """Get comprehensive status of CI checks from GitHub PR.

    Returns:
        ChecksStatus object with complete status information

    Raises:
        APIError: If API call fails or parsing fails
    """
    cmd = [
        "gh",
        "pr",
        "checks",
        "--json",
        "name,state,description,workflow,link,bucket",
    ]

    try:
        result = run_command(cmd)
        response = handle_api_response(result, "get PR checks")
        checks_data = parse_json_response(response, "check results")

        # Ensure we have a list of checks
        if isinstance(checks_data, dict):
            raise APIError("Expected list of checks, got dict")
        checks = checks_data

        # Use helper functions to analyze checks
        running, passed, failed, neutral, cancelled, skipped, timed_out, buildkite = (
            _count_check_states(checks)
        )
        failures = _extract_buildkite_failures(checks)
        in_progress = _extract_buildkite_in_progress(checks)

        return ChecksStatus(
            total_checks=len(checks),
            buildkite_checks=buildkite,
            running_checks=running,
            passed_checks=passed,
            failed_checks=failed,
            neutral_checks=neutral,
            cancelled_checks=cancelled,
            skipped_checks=skipped,
            timed_out_checks=timed_out,
            failures=failures,
            in_progress=in_progress,
        )
    except Exception as e:
        # Let API errors pass through, wrap others
        if isinstance(e, APIError):
            raise
        raise APIError(f"Error in get_checks_status: {e}")


def get_failing_checks() -> list[BuildkiteFailure]:
    """Get failing CI checks from GitHub PR.

    Returns:
        List of BuildkiteFailure objects

    Raises:
        APIError: If API call fails or parsing fails
    """
    status = get_checks_status()
    return status.failures


def get_job_failures(build_id: str, pipeline_slug: str) -> list[JobFailure]:
    """Get failed jobs for a build.

    Args:
        build_id: Build ID
        pipeline_slug: Pipeline slug

    Returns:
        List of JobFailure objects

    Raises:
        APIError: If API call fails or parsing fails
    """
    try:
        result = run_command(
            ["bk", "api", f"/pipelines/{pipeline_slug}/builds/{build_id}"]
        )
        response = handle_api_response(
            result, f"get build {build_id} for pipeline {pipeline_slug}"
        )
        build_data = parse_json_response(response, "build results")
        if isinstance(build_data, list):
            raise APIError("Expected dict for build data, got list")
        validate_api_response(build_data, ["jobs"])

        jobs = build_data["jobs"]
        failures = []

        for job in jobs:
            if job.get("state") == "failed":
                job_failure = JobFailure(
                    job_id=job["id"], job_name=job.get("name", "Unknown job")
                )
                failures.append(job_failure)

        return failures
    except Exception as e:
        # Let API errors pass through, wrap others
        if isinstance(e, APIError):
            raise
        raise APIError(f"Error in get_job_failures: {e}")


def get_job_details(build_id: str, job_id: str, pipeline_slug: str) -> "JobFailure":
    """Get detailed failure information for a job.

    Args:
        build_id: Build ID
        job_id: Job ID
        pipeline_slug: Pipeline slug

    Returns:
        JobFailure object with detailed information

    Raises:
        APIError: If API call fails
    """
    try:
        # Get job logs directly - skip metadata fetch for now due to API issues
        result = run_command(
            [
                "bk",
                "api",
                f"/pipelines/{pipeline_slug}/builds/{build_id}/jobs/{job_id}/log",
            ]
        )
        response = handle_api_response(result, f"get logs for job {job_id}")
        logs = parse_log_response(response)

        # Analyze the logs
        analysis = analyze_logs(logs)

        return JobFailure(
            job_id=job_id,
            job_name="Job",  # We'll get the name from the job_failures call
            failing_command=analysis.failing_command,
            error_message=analysis.error_message,
            error_context=analysis.error_context,
        )
    except Exception as e:
        raise APIError(f"Error analyzing job {job_id}: {e}")
