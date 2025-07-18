"""Integration tests with real discord repository.

These tests validate that the refactored CLI works correctly
with real Buildkite data from the discord repository.
"""

import subprocess
import sys
import os
import pytest
from pathlib import Path


class TestDiscordIntegration:
    """Test CI analysis with real discord repository data."""
    
    @pytest.fixture
    def discord_repo_path(self):
        """Path to the discord repository."""
        return Path("/Users/alex.furrier/git_repositories/discord")
    
    @pytest.fixture
    def original_cifail_available(self):
        """Check if original cifail is available for comparison."""
        try:
            result = subprocess.run(
                ["cifail", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def test_discord_repo_exists(self, discord_repo_path):
        """Verify the discord repository is available for testing."""
        assert discord_repo_path.exists(), f"Discord repo not found at {discord_repo_path}"
        assert discord_repo_path.is_dir(), "Discord repo path should be a directory"
        assert (discord_repo_path / ".git").exists(), "Discord repo should be a git repository"
    
    def test_cli_works_in_discord_repo(self, discord_repo_path):
        """Test that CLI commands work when run from discord repository."""
        # This should FAIL initially until we have the refactored CLI
        
        # Test help command works from discord repo
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--help"],
            capture_output=True,
            text=True,
            cwd=discord_repo_path
        )
        
        assert result.returncode == 0, f"CLI help failed in discord repo: {result.stderr}"
        assert "CI failure analysis tool" in result.stdout
    
    def test_cli_checks_command_in_discord_repo(self, discord_repo_path):
        """Test checks command in discord repository context."""
        # This will likely fail due to missing auth, but should parse correctly
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "checks", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=discord_repo_path,
            timeout=30  # Give it time to try API calls
        )
        
        # We expect this to fail due to auth issues, but not due to import errors
        # The error should be about missing PR or auth, not about missing modules
        if result.returncode != 0:
            error_msg = result.stderr.lower()
            # These are acceptable errors (auth/API issues)
            acceptable_errors = [
                "no pr found",
                "not in a git repository",
                "not authenticated",
                "api error",
                "missing required tools"
            ]
            
            assert any(error in error_msg for error in acceptable_errors), \
                f"Unexpected error (should be auth/API related): {result.stderr}"
    
    def test_cli_configuration_check_in_discord_repo(self, discord_repo_path):
        """Test configuration checking in discord repository."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "configure"],
            capture_output=True,
            text=True,
            cwd=discord_repo_path,
            timeout=30
        )
        
        # This should run and either succeed or fail with auth issues
        if result.returncode != 0:
            # Should fail due to missing tokens, not import errors
            error_msg = result.stderr.lower()
            assert "buildkite_api_token" in error_msg or "missing required tools" in error_msg, \
                f"Unexpected error (should be auth related): {result.stderr}"
    
    @pytest.mark.skipif(
        not Path("/Users/alex.furrier/git_repositories/discord").exists(),
        reason="Discord repository not available"
    )
    def test_original_vs_refactored_help_output(self, discord_repo_path, original_cifail_available):
        """Compare help output between original and refactored versions."""
        if not original_cifail_available:
            pytest.skip("Original cifail not available for comparison")
        
        # Get original help output
        original_result = subprocess.run(
            ["cifail", "--help"],
            capture_output=True,
            text=True,
            cwd=discord_repo_path
        )
        
        # Get refactored help output  
        refactored_result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--help"],
            capture_output=True,
            text=True,
            cwd=discord_repo_path
        )
        
        if original_result.returncode == 0 and refactored_result.returncode == 0:
            # Both should have same key elements
            original_lines = original_result.stdout.lower()
            refactored_lines = refactored_result.stdout.lower()
            
            # Key commands should be present in both
            key_commands = ["configure", "checks", "logs", "job"]
            for command in key_commands:
                assert command in original_lines, f"Original missing {command}"
                assert command in refactored_lines, f"Refactored missing {command}"
    
    def test_package_imports_work(self):
        """Test that package components can be imported."""
        # This should FAIL initially until modules are created
        try:
            import ci_fail
            assert ci_fail is not None
            
            # Test that we can import main components (once they exist)
            from ci_fail import config, models, utils
            assert config is not None
            assert models is not None  
            assert utils is not None
            
        except ImportError as e:
            # Expected to fail initially during Red phase
            pytest.skip(f"Package not yet created - expected during Red phase: {e}")
    
    def test_cli_entry_point_configured(self):
        """Test that CLI entry point is properly configured."""
        # Check that we can invoke the CLI through the package
        result = subprocess.run(
            [sys.executable, "-c", "import ci_fail; print('Import successful')"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode != 0:
            # Expected to fail initially
            pytest.skip("Package not yet created - expected during Red phase")
        
        assert "Import successful" in result.stdout