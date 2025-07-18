# ci-fail

A CLI tool for analyzing CI failures in GitHub + Buildkite workflows. Quickly identify what went wrong and get actionable insights to fix failing builds.

## Features

- 🔍 **Smart error detection** - Automatically extracts failing commands and error messages from build logs
- 📊 **Clear status overview** - Shows comprehensive CI check status with pass/fail counts  
- 🎯 **Focused analysis** - Highlights specific failures with detailed context
- 🚀 **Fast navigation** - Jump directly to failure details or full logs
- 📋 **Multiple formats** - Human-readable tables or JSON output for automation

## Installation

```bash
pip install ci-fail
```

Or with uv:
```bash
uv tool install ci-fail
```

## Quick Start

1. **Configure authentication** (one-time setup):
```bash
ci-fail configure
```

2. **Check CI status** in any GitHub repo with PRs:
```bash
ci-fail checks                    # Show status overview
ci-fail checks --detail 1         # Show details for failure #1
ci-fail checks --detailed         # Show all failure details inline
```

3. **Get detailed logs** for specific builds:
```bash
ci-fail logs <build-url-or-id>     # Analyze failed jobs
ci-fail logs <build-id> --detailed # Include commands and errors
```

## Commands

### `ci-fail configure`
Set up GitHub CLI and Buildkite CLI authentication. Creates API tokens and configures tools.

### `ci-fail checks`
Show CI status for the current PR:
- **`--detailed`** - Show failure details inline
- **`--detail 1,3`** - Show details for specific failures  
- **`--format json`** - Output as JSON

### `ci-fail logs <build-id>`
Analyze logs for a specific build:
- **`--detailed`** - Include failing commands and error messages
- **`--pipeline-slug name`** - Specify pipeline (auto-detected from URLs)
- **`--format json`** - Output as JSON

### `ci-fail job <job-id> <build-id> <pipeline-slug>`
Get detailed analysis of a specific failed job with commands and error context.

## Requirements

- **GitHub CLI** (`gh`) - Install with `brew install gh`
- **Buildkite CLI** (`bk`) - Install with `brew install buildkite/buildkite/bk@3`
- **Git repository** with GitHub PRs and Buildkite checks

## Configuration

Set these environment variables (or use `ci-fail configure`):

```bash
export BUILDKITE_API_TOKEN="your-token"           # Required
export BUILDKITE_ORG="your-org"                   # Optional (defaults to 'discord') 
export BUILDKITE_MAIN_PIPELINE="your-pipeline"    # Optional (defaults to 'discord')
```

## Examples

**Check PR status:**
```bash
$ ci-fail checks
📝 PR #123 - Fix user authentication bug
🔗 https://github.com/org/repo/pull/123

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
║ Metric             ║ Count    ║ Status          ║
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Total Checks       │ 12       │                 │
│ Buildkite Checks   │ 8        │                 │  
│ Running            │ 2        │ 🔄 In Progress  │
│ Passed             │ 7        │ ✅ Passing      │
│ Failed             │ 3        │ ❌ Failing      │
└────────────────────┴──────────┴─────────────────┘
```

**Get failure details:**
```bash
$ ci-fail checks --detail 1

💥 Failure #1: Backend Tests

🔧 CI Command (Failed)
pytest tests/test_auth.py::test_login_validation -v

❌ Error Message  
AssertionError: Expected login to succeed with valid credentials

📝 Error Context
1  │ def test_login_validation():
2  │     user = create_test_user("test@example.com", "password123")
3  │     result = auth_service.login("test@example.com", "password123") 
4  │ >   assert result.success is True
5  │     AssertionError: Expected login to succeed with valid credentials
```

## Development

This project uses modern Python development practices:

```bash
# Setup
make setup          # Install dependencies  
make check          # Run all quality checks
make test           # Run tests with coverage

# Quality checks
make lint           # Code linting with ruff
make format         # Code formatting  
make mypy           # Type checking
```

## Architecture

The project follows a modular architecture:

- **`ci_fail/cli.py`** - Click command definitions and user interface
- **`ci_fail/api.py`** - GitHub and Buildkite API interactions  
- **`ci_fail/analysis.py`** - Log parsing and error extraction
- **`ci_fail/display.py`** - Rich console output formatting
- **`ci_fail/models.py`** - Data structures and exceptions
- **`ci_fail/config.py`** - Configuration and regex patterns
- **`ci_fail/utils.py`** - Shared utility functions

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/awesome-feature`
3. Make your changes and add tests
4. Run quality checks: `make check`
5. Commit with clear messages (see contributing guidelines)
6. Submit a pull request

## License

MIT License - see LICENSE file for details.