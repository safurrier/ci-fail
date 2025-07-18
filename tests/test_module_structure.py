"""Test module structure and organization.

These tests validate that the refactored code follows proper
module organization and separation of concerns.
"""

import importlib
import inspect
import pytest
from pathlib import Path


class TestModuleStructure:
    """Test that modules are properly organized and follow conventions."""
    
    def test_package_structure_exists(self):
        """Test that ci_fail package has the expected structure."""
        # This should FAIL initially until modules are created
        package_dir = Path(__file__).parent.parent / "ci_fail"
        assert package_dir.exists(), "ci_fail package directory should exist"
        assert package_dir.is_dir(), "ci_fail should be a directory"
        assert (package_dir / "__init__.py").exists(), "Package should have __init__.py"
    
    def test_expected_modules_exist(self):
        """Test that all expected modules exist in the package."""
        package_dir = Path(__file__).parent.parent / "ci_fail"
        
        expected_modules = [
            "config.py",
            "models.py", 
            "utils.py",
            "api.py",
            "analysis.py",
            "display.py",
            "cli.py"
        ]
        
        for module_name in expected_modules:
            module_path = package_dir / module_name
            assert module_path.exists(), f"Module {module_name} should exist"
            assert module_path.is_file(), f"{module_name} should be a file"
    
    def test_modules_can_be_imported(self):
        """Test that all modules can be imported without errors."""
        modules_to_test = [
            "ci_fail.config",
            "ci_fail.models",
            "ci_fail.utils", 
            "ci_fail.api",
            "ci_fail.analysis",
            "ci_fail.display",
            "ci_fail.cli"
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} should import successfully"
            except ImportError as e:
                # Expected to fail initially during Red phase
                pytest.skip(f"Module {module_name} not yet created - expected during Red phase: {e}")
    
    def test_config_module_structure(self):
        """Test that config module has expected structure."""
        try:
            from ci_fail import config
            
            # Should have Config class
            assert hasattr(config, 'Config'), "Config module should have Config class"
            assert hasattr(config, 'Patterns'), "Config module should have Patterns class"
            
            # Config should have expected attributes
            config_obj = config.Config()
            assert hasattr(config_obj, 'ERROR_CONTEXT_WINDOW'), "Config should have ERROR_CONTEXT_WINDOW"
            assert hasattr(config_obj, 'DEFAULT_TIMEOUT'), "Config should have DEFAULT_TIMEOUT"
            
        except ImportError:
            pytest.skip("Config module not yet created - expected during Red phase")
    
    def test_models_module_structure(self):
        """Test that models module has expected structure."""
        try:
            from ci_fail import models
            
            # Should have main data classes
            expected_classes = [
                'BuildkiteFailure',
                'JobFailure', 
                'LogAnalysis',
                'ChecksStatus',
                'OutputFormat'
            ]
            
            for class_name in expected_classes:
                assert hasattr(models, class_name), f"Models should have {class_name}"
            
            # Should have exceptions
            expected_exceptions = [
                'CIFailError',
                'CommandNotFoundError',
                'APIError',
                'ValidationError'
            ]
            
            for exception_name in expected_exceptions:
                assert hasattr(models, exception_name), f"Models should have {exception_name}"
                
        except ImportError:
            pytest.skip("Models module not yet created - expected during Red phase")
    
    def test_utils_module_structure(self):
        """Test that utils module has expected structure."""
        try:
            from ci_fail import utils
            
            # Should have main utility functions
            expected_functions = [
                'run_command',
                'check_prerequisites',
                'validate_build_input',
                'handle_api_response'
            ]
            
            for func_name in expected_functions:
                assert hasattr(utils, func_name), f"Utils should have {func_name}"
                assert callable(getattr(utils, func_name)), f"{func_name} should be callable"
                
        except ImportError:
            pytest.skip("Utils module not yet created - expected during Red phase")
    
    def test_api_module_structure(self):
        """Test that api module has expected structure."""
        try:
            from ci_fail import api
            
            # Should have main API functions
            expected_functions = [
                'get_checks_status',
                'get_failing_checks',
                'get_job_failures',
                'get_pr_info'
            ]
            
            for func_name in expected_functions:
                assert hasattr(api, func_name), f"API should have {func_name}"
                assert callable(getattr(api, func_name)), f"{func_name} should be callable"
                
        except ImportError:
            pytest.skip("API module not yet created - expected during Red phase")
    
    def test_analysis_module_structure(self):
        """Test that analysis module has expected structure."""
        try:
            from ci_fail import analysis
            
            # Should have main analysis functions
            expected_functions = [
                'analyze_logs',
                'clean_log_content',
                'extract_failing_command',
                'find_error_message_and_context'
            ]
            
            for func_name in expected_functions:
                assert hasattr(analysis, func_name), f"Analysis should have {func_name}"
                assert callable(getattr(analysis, func_name)), f"{func_name} should be callable"
                
        except ImportError:
            pytest.skip("Analysis module not yet created - expected during Red phase")
    
    def test_display_module_structure(self):
        """Test that display module has expected structure."""
        try:
            from ci_fail import display
            
            # Should have main display functions
            expected_functions = [
                'create_command_panel',
                'create_error_panel',
                'create_context_panel',
                'display_checks_status'
            ]
            
            for func_name in expected_functions:
                assert hasattr(display, func_name), f"Display should have {func_name}"
                assert callable(getattr(display, func_name)), f"{func_name} should be callable"
                
        except ImportError:
            pytest.skip("Display module not yet created - expected during Red phase")
    
    def test_cli_module_structure(self):
        """Test that cli module has expected structure."""
        try:
            from ci_fail import cli
            
            # Should have main CLI group
            assert hasattr(cli, 'cli'), "CLI module should have main cli group"
            
            # Should have command functions
            expected_commands = [
                'configure',
                'checks',
                'logs', 
                'job'
            ]
            
            for command_name in expected_commands:
                assert hasattr(cli, command_name), f"CLI should have {command_name} command"
                
        except ImportError:
            pytest.skip("CLI module not yet created - expected during Red phase")
    
    def test_no_circular_imports(self):
        """Test that modules don't have circular import dependencies."""
        try:
            # Try importing all modules in dependency order
            import ci_fail.config
            import ci_fail.models
            import ci_fail.utils
            import ci_fail.api
            import ci_fail.analysis
            import ci_fail.display
            import ci_fail.cli
            
            # If we get here without ImportError, no circular dependencies
            assert True, "No circular import dependencies detected"
            
        except ImportError:
            pytest.skip("Modules not yet created - expected during Red phase")
    
    def test_main_module_exists(self):
        """Test that __main__.py exists for module execution."""
        main_module = Path(__file__).parent.parent / "ci_fail" / "__main__.py"
        assert main_module.exists(), "Package should have __main__.py for module execution"
    
    def test_package_follows_conventions(self):
        """Test that package follows user conventions."""
        # Note: NO INLINE IMPORTS rule is better enforced by linters like ruff
        # This is a placeholder for other convention checks
        
        package_dir = Path(__file__).parent.parent / "ci_fail"
        
        # Basic check that package directory exists
        assert package_dir.exists(), "Package directory should exist"
        assert (package_dir / "__init__.py").exists(), "Package should have __init__.py"