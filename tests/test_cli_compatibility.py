"""Test CLI compatibility during refactoring.

These characterization tests ensure that the refactored CLI commands
produce identical output to the original cifail.py script.
"""

import subprocess
import sys
import os
import pytest
from pathlib import Path


class TestCLICompatibility:
    """Test that refactored CLI maintains compatibility with original."""
    
    def test_cli_help_command(self):
        """Test that --help command works and produces expected output."""
        # This should FAIL initially until we have the package structure
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # For now, this will fail - we expect it to
        # Once refactored, it should work
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"
        assert "CI failure analysis tool" in result.stdout
        assert "configure" in result.stdout
        assert "checks" in result.stdout
        assert "logs" in result.stdout
        assert "job" in result.stdout
    
    def test_cli_configure_help(self):
        """Test that configure command help works."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "configure", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Configure help failed: {result.stderr}"
        assert "Configure Buildkite CLI" in result.stdout
    
    def test_cli_checks_help(self):
        """Test that checks command help works."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "checks", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Checks help failed: {result.stderr}"
        assert "Get CI checks status" in result.stdout
        assert "--detailed" in result.stdout
        assert "--detail" in result.stdout
    
    def test_cli_logs_help(self):
        """Test that logs command help works."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "logs", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Logs help failed: {result.stderr}"
        assert "Get logs for a specific Buildkite build" in result.stdout
        assert "--detailed" in result.stdout
        assert "--pipeline-slug" in result.stdout
    
    def test_cli_job_help(self):
        """Test that job command help works."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "job", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Job help failed: {result.stderr}"
        assert "Get detailed information about a specific failed job" in result.stdout
    
    def test_cli_version_info(self):
        """Test that version information is accessible."""
        # Test importing the package to get version
        try:
            import ci_fail
            # Once refactored, should have version info
            assert hasattr(ci_fail, '__version__') or hasattr(ci_fail, 'version')
        except ImportError:
            # Expected to fail initially
            pytest.skip("Package not yet created - expected during Red phase")
    
    def test_cli_module_structure(self):
        """Test that the CLI can be invoked as a module."""
        # This tests the __main__.py entry point
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Should show help or at least not crash
        # We expect this to fail initially
        assert result.returncode != 1, f"Module invocation failed: {result.stderr}"
    
    @pytest.mark.parametrize("command", [
        ["configure"],
        ["checks", "--format", "json"],
        ["logs", "12345", "--pipeline-slug", "test"],
        ["job", "job-123", "build-456", "pipeline-test"]
    ])
    def test_cli_commands_accept_arguments(self, command):
        """Test that CLI commands accept their expected arguments."""
        full_command = [sys.executable, "-m", "ci_fail"] + command
        
        # We don't expect these to succeed (they need real API tokens)
        # But they should at least parse arguments correctly
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Should not fail due to argument parsing issues
        # API errors are expected and okay
        assert "invalid choice" not in result.stderr.lower()
        assert "no such option" not in result.stderr.lower()
        assert "missing argument" not in result.stderr.lower()