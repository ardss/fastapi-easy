# Contributing to FastAPI-Easy

Thank you for your interest in contributing to FastAPI-Easy! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Contribution Guidelines](#contribution-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Development Setup

### Prerequisites

- Python 3.8 or higher (3.11+ recommended)
- Git
- A code editor with Python support (VS Code, PyCharm, etc.)

### Quick Start

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/your-username/fastapi-easy.git
   cd fastapi-easy
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Unix/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate

   # Install in development mode with all dependencies
   pip install -e ".[dev]"
   ```

3. **Set Up Pre-commit Hooks**
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

4. **Verify Setup**
   ```bash
   # Run tests to ensure everything works
   pytest

   # Run code quality checks
   pre-commit run --all-files
   ```

### IDE Configuration

#### VS Code

Create a `.vscode/settings.json` file in your workspace:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "python.sortImports.args": ["--profile", "black", "--line-length", "100"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm

1. Go to Settings → Editor → Code Style → Python
2. Set right margin to 100
3. Enable "Line wrapping" and "Visual guides"
4. Install Black and isort plugins
5. Configure to run Black and isort on save

## Contribution Guidelines

### Types of Contributions

We welcome the following types of contributions:

1. **Bug Reports**: Report bugs using GitHub Issues
2. **Feature Requests**: Propose new features or enhancements
3. **Code Contributions**: Submit pull requests with bug fixes or new features
4. **Documentation**: Improve documentation, examples, and guides
5. **Test Coverage**: Add or improve tests
6. **Performance**: Identify and fix performance issues

### Before You Start

1. **Check Existing Issues**: Search for existing issues or PRs related to your contribution
2. **Discuss Major Changes**: For significant changes, open an issue for discussion first
3. **Understand the Codebase**: Read the documentation and explore the code structure

### Branch Naming

Use descriptive branch names:
- `fix/issue-description` for bug fixes
- `feat/feature-description` for new features
- `docs/documentation-update` for documentation changes
- `refactor/code-improvement` for refactoring

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `fix(core): resolve pagination issue with large datasets`
- `feat(auth): add OAuth2 integration with Google`
- `docs(readme): update installation instructions`

Types:
- `fix`: Bug fixes
- `feat`: New features
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

## Pull Request Process

### 1. Prepare Your PR

1. **Sync with Main**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run Tests and Checks**
   ```bash
   # Run full test suite
   pytest

   # Run code quality checks
   pre-commit run --all-files

   # Check type hints
   mypy src/fastapi_easy

   # Check documentation builds
   mkdocs build
   ```

3. **Update Documentation**
   - Add or update docstrings for any public API changes
   - Update relevant documentation files
   - Add examples for new features

### 2. Submit Your PR

1. **Create Pull Request**
   - Use a descriptive title
   - Link to related issues
   - Use the PR template if available

2. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update

   ## Testing
   - [ ] All tests pass
   - [ ] Added new tests for new functionality
   - [ ] Manual testing completed

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] Commit messages follow conventional format
   ```

### 3. Code Review Process

1. **Review Requirements**
   - At least one maintainer approval required
   - All automated checks must pass
   - All PR discussions must be resolved

2. **Address Feedback**
   - Make requested changes promptly
   - Explain any disagreements with suggestions
   - Keep PR discussions focused and professional

## Coding Standards

### Code Style

We use the following tools to maintain code quality:
- **Black**: Code formatting (100 character line length)
- **isort**: Import sorting
- **mypy**: Type checking
- **ruff**: Linting and code analysis
- **bandit**: Security scanning

### Python Version Support

- **Minimum**: Python 3.8
- **Target**: Python 3.8-3.12
- **Tested**: All supported versions in CI

### Type Hints

All code must include type hints:
```python
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

def process_data(
    data: List[Dict[str, Any]],
    config: Optional[Config] = None
) -> Result:
    """Process the provided data with optional configuration."""
    pass
```

### Documentation

Follow the [Documentation Standards](DOCUMENTATION_STANDARDS.md):
- Use Google-style docstrings
- Include type hints in docstrings
- Provide examples for complex APIs
- Document all public APIs

### Error Handling

Use the project's error handling patterns:
```python
from fastapi_easy.core.errors import AppError, ErrorCode

def example_function(data: str) -> str:
    """Example function with error handling."""
    if not data:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            message="Data cannot be empty"
        )
    return data.upper()
```

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (requires external resources)
├── e2e/           # End-to-end tests (slow, full flow)
├── performance/   # Performance tests
└── conftest.py    # Pytest configuration and fixtures
```

### Writing Tests

1. **Unit Tests**
   - Test individual functions and methods
   - Use mocking for external dependencies
   - Focus on edge cases and error conditions

2. **Integration Tests**
   - Test component interactions
   - Use test databases or external services
   - Verify API contracts

3. **Test Naming**
   ```python
   class TestClassName:
       def test_method_should_behavior_when_condition(self):
           """Test should follow BDD-style naming."""
           pass
   ```

4. **Test Organization**
   - Use descriptive test names
   - Group related tests in classes
   - Use fixtures for common setup/teardown

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_core.py

# Run with coverage
pytest --cov=src/fastapi_easy --cov-report=html

# Run specific marker
pytest -m unit

# Run in parallel
pytest -n auto
```

### Test Requirements

- New features must include tests
- Bug fixes must include regression tests
- Maintain at least 85% code coverage
- All tests must pass before merging

## Documentation

### Documentation Types

1. **API Documentation**: Auto-generated from docstrings
2. **User Guides**: Step-by-step tutorials
3. **Reference Guides**: Comprehensive explanations
4. **Examples**: Working code examples

### Writing Documentation

1. **Use Markdown**: All documentation in Markdown format
2. **Include Examples**: Every feature should have examples
3. **Code Blocks**: Use proper syntax highlighting
4. **Links**: Internal links should use relative paths

### Building Documentation

```bash
# Build docs locally
mkdocs serve

# Build static site
mkdocs build

# Check for broken links
mkdocs build --strict
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Pre-release**
   - [ ] All tests pass
   - [ ] Documentation updated
   - [ ] Changelog updated
   - [ ] Version number updated
   - [ ] Security scan completed

2. **Release**
   - [ ] Create git tag
   - [ ] Build and publish to PyPI
   - [ ] Update GitHub releases
   - [ ] Notify users

3. **Post-release**
   - [ ] Update documentation website
   - [ ] Announce in community channels
   - [ ] Monitor for issues

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/ardss/fastapi-easy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ardss/fastapi-easy/discussions)
- **Documentation**: [Project Documentation](https://fastapi-easy.readthedocs.io/)

## Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Annual project summary

Thank you for contributing to FastAPI-Easy! 🎉