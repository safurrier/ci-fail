"""Main entry point for ci_fail package when run as a module."""

import sys


def main():
    """Main entry point for the CLI."""
    try:
        # Import CLI here to avoid circular imports
        from ci_fail.cli import cli

        cli()
    except ImportError as e:
        print(f"Error importing CLI: {e}", file=sys.stderr)
        print("Package modules may not be fully implemented yet.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
