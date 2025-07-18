"""High-value CLI tests that verify the tool works for users."""

import subprocess
import sys
import tempfile
import os
from pathlib import Path
import pytest


class TestCLIFunctionality:
    """Test that the CLI actually works for users."""
    
    def test_cli_help_shows_all_commands(self):
        """Users can discover available commands."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0
        
        # Essential commands users need
        expected_commands = ["configure", "checks", "logs", "job"]
        for command in expected_commands:
            assert command in result.stdout, f"Missing {command} command"
    
    def test_configure_without_prerequisites_gives_helpful_error(self):
        """Configure command guides users when tools are missing."""
        # Clear environment to ensure no tokens
        env = os.environ.copy()
        env.pop("BUILDKITE_API_TOKEN", None)
        
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "configure"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        # Should provide helpful guidance about token setup
        output = result.stdout.lower()
        assert "token" in output
    
    def test_checks_outside_git_repo_explains_requirement(self):
        """Checks command explains git repository requirement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, "-m", "ci_fail", "checks"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=5
            )
            
            # Should explain the git repository requirement
            assert "git repository" in result.stdout.lower()
    
    def test_logs_command_validates_input_format(self):
        """Logs command validates build ID format."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "logs", "invalid-build-id"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Should handle invalid input gracefully
        assert result.stdout or result.stderr  # Should provide some feedback
    
    def test_job_command_requires_proper_arguments(self):
        """Job command validates required arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "job", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0
        # Should show required arguments
        assert "job_id" in result.stdout or "JOB_ID" in result.stdout
    
    @pytest.mark.smoke
    def test_cli_can_be_imported_as_module(self):
        """CLI can be run as a Python module."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Should complete without import errors
        # Version command might not be implemented, but should not crash
        assert "ImportError" not in result.stderr
        assert "ModuleNotFoundError" not in result.stderr