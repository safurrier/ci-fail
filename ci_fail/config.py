"""Configuration and pattern definitions for CI failure analysis."""

import re


class Config:
    """Configuration constants for the CI failure analysis tool."""

    ERROR_CONTEXT_WINDOW = 5
    DEFAULT_TIMEOUT = 30
    COMMAND_PREFIX = "+ "

    # Configurable organization settings
    DEFAULT_ORG = "discord"
    DEFAULT_MAIN_PIPELINE = "discord"

    ERROR_PATTERNS = ["error:", "failed:", "exception:", "fatal:"]
    CI_COMMAND_PATTERNS = [
        "clyde ",
        "bazel ",
        "npm run",
        "pytest",
        "mypy",
        "ruff",
        "black",
        "docker run",
        "make ",
        "cargo ",
        "go build",
        "python -m",
    ]

    BUILDKITE_URL_PATTERN = r"https://buildkite\.com/[^/]+/([^/]+)/builds/(\d+)"

    # Required tools with their installation instructions
    REQUIRED_TOOLS: dict[str, str] = {
        "gh": "GitHub CLI - Install with: brew install gh",
        "bk": "Buildkite CLI - Install with: brew install buildkite/buildkite/bk@3",
    }


class Patterns:
    """Compiled regex patterns for efficient matching."""

    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    BK_ESCAPE = re.compile(r"\x1b_bk;[^\x07]*\x07")
    BK_TIMESTAMP = re.compile(r"bk;t=\d+\$?\s*")
    BUILDKITE_URL = re.compile(Config.BUILDKITE_URL_PATTERN)

    # Buildkite artifacts patterns
    BK_ARTIFACTS: list[re.Pattern[str]] = [
        re.compile(r"^\s*\+\+\+\s*$"),  # +++ markers
        re.compile(r"^\s*---\s*$"),  # --- markers
        re.compile(r"^\s*~~~\s*$"),  # ~~~ markers
        re.compile(r"^\s*===\s*$"),  # === markers
        re.compile(r"^\s*\^\^\^\s*\+\+\+\s*$"),  # ^^^ +++ markers
    ]

    # Command detection patterns (in order of priority)
    COMMAND_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"^\+ (.+)$"),  # Standard + prefix (highest priority)
        re.compile(r"^\$ (.+)$"),  # $ prefix (shell commands)
        re.compile(
            r".*?(?:^|\s)(clyde\s+.+)$", re.IGNORECASE
        ),  # Discord clyde commands
        re.compile(r".*?(?:^|\s)(bazel\s+.+)$", re.IGNORECASE),  # Bazel build commands
        re.compile(
            r".*?(?:^|\s)(npm\s+run\s+.+)$", re.IGNORECASE
        ),  # npm script commands
        re.compile(
            r".*?(?:^|\s)(python\s+-m\s+.+)$", re.IGNORECASE
        ),  # Python module commands
        re.compile(r".*?(?:^|\s)(pytest\s+.+)$", re.IGNORECASE),  # pytest commands
        re.compile(r".*?(?:^|\s)(mypy\s+.+)$", re.IGNORECASE),  # mypy type checking
        re.compile(r".*?(?:^|\s)(ruff\s+.+)$", re.IGNORECASE),  # ruff linting
        re.compile(r".*?(?:^|\s)(make\s+.+)$", re.IGNORECASE),  # make commands
        re.compile(r".*?(?:^|\s)(cargo\s+.+)$", re.IGNORECASE),  # Rust cargo commands
        re.compile(
            r".*?(?:^|\s)(go\s+build\s+.+)$", re.IGNORECASE
        ),  # Go build commands
        re.compile(
            r".*?(?:^|\s)(docker\s+run\s+.+)$", re.IGNORECASE
        ),  # Docker run commands
    ]

    # Error detection patterns (in order of priority)
    ERROR_PATTERNS: list[re.Pattern[str]] = [
        # Specific error patterns
        re.compile(r".*Error: (.+)", re.IGNORECASE),  # "Error: message"
        re.compile(
            r'.*cannot find module [\'"](.+)[\'"]', re.IGNORECASE
        ),  # Node.js module errors
        re.compile(
            r".*modulenotfounderror: (.+)", re.IGNORECASE
        ),  # Python import errors
        re.compile(r".*syntaxerror: (.+)", re.IGNORECASE),  # Python syntax errors
        re.compile(r".*importerror: (.+)", re.IGNORECASE),  # Python import failures
        re.compile(r".*typeerror: (.+)", re.IGNORECASE),  # Python type errors
        re.compile(r".*valueerror: (.+)", re.IGNORECASE),  # Python value errors
        re.compile(r".*keyerror: (.+)", re.IGNORECASE),  # Python key errors
        re.compile(r".*attributeerror: (.+)", re.IGNORECASE),  # Python attribute errors
        # Build/CI specific errors
        re.compile(r".*bazel.*failed(.+)", re.IGNORECASE),  # Bazel build failures
        re.compile(r".*npm.*failed(.+)", re.IGNORECASE),  # npm/yarn failures
        re.compile(r".*compilation failed(.+)", re.IGNORECASE),  # Compilation errors
        re.compile(r".*test failed(.+)", re.IGNORECASE),  # Test failures
        re.compile(r".*build failed(.+)", re.IGNORECASE),  # Build failures
        re.compile(r".*command failed(.+)", re.IGNORECASE),  # Command failures
        re.compile(r".*process exited with.*code (\d+)", re.IGNORECASE),  # Exit codes
        re.compile(r".*killed.*signal (\d+)", re.IGNORECASE),  # Signal kills
        re.compile(r".*timeout.*after (\d+)", re.IGNORECASE),  # Timeout errors
        # Generic patterns (fallback)
        re.compile(
            r".*(error|fail|exception|fatal):\s*(.+)", re.IGNORECASE
        ),  # Generic errors
        re.compile(r".*🚨\s*Error:\s*(.+)", re.IGNORECASE),  # Formatted errors
        re.compile(r".*\^\^\^\s*\+\+\+.*"),  # Buildkite markers
    ]

    # Multi-line error patterns
    MULTILINE_ERROR_PATTERNS: list[re.Pattern[str]] = [
        re.compile(
            r"Traceback \(most recent call last\):", re.IGNORECASE
        ),  # Python stack traces
        re.compile(
            r"Error: Cannot find module", re.IGNORECASE
        ),  # Node.js module errors
        re.compile(r"ERROR: .*", re.IGNORECASE),  # Bazel errors
        re.compile(r"npm ERR!|pnpm ERR!", re.IGNORECASE),  # npm/pnpm errors
        re.compile(r"FAILED: ", re.IGNORECASE),  # Build failures
        re.compile(r"FAIL .*", re.IGNORECASE),  # Test failures
        re.compile(r"error: .*", re.IGNORECASE),  # Compilation errors
    ]
