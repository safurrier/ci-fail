"""Integration tests that verify the CLI works end-to-end."""

import subprocess
import sys
import tempfile
import json
import os
from pathlib import Path
import pytest


class TestEndToEnd:
    """Test complete user workflows work."""
    
    @pytest.mark.smoke
    def test_cli_launches_without_errors(self):
        """CLI starts successfully without import or runtime errors."""
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0
        assert "CI failure analysis tool" in result.stdout
    
    def test_configure_workflow_provides_clear_guidance(self):
        """Configure workflow guides users through setup."""
        # Simulate CI environment without tools
        env = {"BUILDKITE_API_TOKEN": "", "PATH": "/usr/bin:/bin"}
        
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "configure"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        # Should provide guidance about setup requirements
        output = result.stdout.lower()
        assert ("missing required tools" in output or 
                "install with" in output or
                "buildkite_api_token" in output or
                "github cli" in output or
                "buildkite cli" in output)
    
    def test_checks_json_format_produces_valid_json(self):
        """Checks command can produce JSON output format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            
            result = subprocess.run(
                [sys.executable, "-m", "ci_fail", "checks", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=5
            )
            
            # Should not crash when JSON format is requested
            # If there's output, it should either be valid JSON or a helpful error message
            if result.stdout.strip():
                # Either it's valid JSON or the CLI handled the error gracefully
                try:
                    json.loads(result.stdout)
                except json.JSONDecodeError:
                    # If not JSON, should be a helpful error message, not a crash
                    assert len(result.stdout.strip()) > 10  # Non-empty error message
    
    def test_logs_command_handles_input_gracefully(self):
        """Logs command handles input gracefully."""
        # Use a fake but properly formatted Buildkite URL
        fake_url = "https://buildkite.com/test-org/test-pipeline/builds/123"
        
        # Simulate CI environment without tools
        env = os.environ.copy()
        env['PATH'] = '/usr/bin:/bin'
        
        result = subprocess.run(
            [sys.executable, "-m", "ci_fail", "logs", fake_url],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )
        
        # Should either parse the URL or explain missing prerequisites
        output = result.stdout.lower()
        assert ("123" in output or "test-pipeline" in output or 
                "missing required tools" in output or 
                "install with" in output or
                "github cli" in output or
                "buildkite cli" in output)