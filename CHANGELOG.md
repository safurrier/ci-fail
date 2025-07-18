# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete CI failure analysis CLI tool for GitHub + Buildkite workflows
- Smart error detection and extraction from build logs
- Comprehensive CI status overview with pass/fail counts
- Multiple output formats (human-readable tables and JSON)
- Modular architecture with proper separation of concerns:
  - CLI interface (Click-based commands)
  - API interactions (GitHub and Buildkite)
  - Log analysis engine with regex-based error extraction
  - Rich console output formatting
  - Data models and configuration management
- Comprehensive test suite with 38 test cases covering:
  - CLI compatibility and integration
  - Module structure validation
  - Real-world integration testing
- Modern Python development workflow:
  - uv for dependency management
  - ruff for linting and formatting
  - mypy for type checking
  - pytest with coverage reporting
  - Pre-commit hooks for quality gates

### Changed
- Refactored monolithic `cifail.py` script into modular package structure
- Applied Test-Driven Development (TDD) approach with Red-Green-Refactor cycle
- Improved cognitive load by extracting helper functions from complex methods
- Fixed dependency conflicts in build system
- Updated project documentation to reflect CI analysis tool purpose

### Removed
- Original monolithic `cifail.py` script
- Template-specific code and documentation

## [0.1.0] - 2024-04-14
- Initial fork from eugeneyan/python-collab-template
- Added Docker environment management
- Setup package installation configuration
