# Contributing to ModalTrace

Thank you for your interest in contributing to ModalTrace! We welcome contributions from everyone. This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/video-ai-telemetry.git
cd video-ai-telemetry
git remote add upstream https://github.com/arnabdeypolimi/video-ai-telemetry.git
```

### 2. Create a Dev Branch

```bash
git checkout -b feature/your-feature-name
```

Follow branch naming conventions:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation
- `refactor/` for refactoring

### 3. Set Up Development Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,all]"
```

## Development Workflow

### Run Tests

```bash
pytest tests/ -v
```

### Lint Code

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Run All Checks

```bash
# Lint
ruff check src/ tests/
ruff format --check src/ tests/

# Tests
pytest tests/ -v

# Type check
mypy src/
```

## Making Changes

### Code Style

- Follow PEP 8 conventions
- Use meaningful variable names
- Write clear, concise comments for complex logic
- Keep functions focused and modular

### Adding Features

1. **Write tests first** (TDD approach)
   ```bash
   # Create test file: tests/test_feature.py
   # Write failing tests
   pytest tests/test_feature.py -v
   ```

2. **Implement the feature**
   - Follow existing code patterns
   - Add docstrings to public functions/classes
   - Update type hints

3. **Verify all tests pass**
   ```bash
   pytest tests/ -v
   ```

4. **Update documentation**
   - Add examples to README if applicable
   - Update docstrings
   - Update API documentation if needed

### Bug Fixes

1. **Create a test that reproduces the bug**
2. **Fix the bug**
3. **Verify the test now passes**
4. **Run all tests to ensure no regressions**

## Commit Guidelines

Write clear, descriptive commit messages:

```
Short summary (50 chars max)

Longer explanation (if needed) wrapped at 72 characters.
Explain why this change was needed.

Fixes #123  (if applicable)
```

### Example

```bash
git commit -m "Fix GPU memory leak in aggregator

The ring buffer was not properly releasing GPU memory
when flushing metrics. Added explicit cleanup in the
flush_metrics() method.

Fixes #456"
```

## Submitting Changes

### 1. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 2. Create a Pull Request

Go to GitHub and create a PR from your fork to the main repository.

**PR Title:** Short, descriptive title
**PR Description:** Include:
- What changes were made
- Why these changes are needed
- How to test the changes
- Any related issues (e.g., "Fixes #123")

### 3. PR Review Process

- Code review for quality and correctness
- Automated tests must pass
- Linting must pass
- At least one approval required before merge

### 4. Address Feedback

If reviewers request changes:

```bash
# Make changes
git add <files>
git commit -m "Address review feedback"
git push origin feature/your-feature-name
```

## Testing

### Test Structure

```
tests/
├── test_module.py          # Test file for module
├── conftest.py            # Shared fixtures
└── ...
```

### Writing Tests

```python
import pytest
from modaltrace import ModalTraceConfig

def test_config_default_values():
    """Test that ModalTraceConfig uses correct defaults."""
    config = ModalTraceConfig()
    assert config.service_name == "modaltrace-pipeline"
    assert config.otlp_timeout_ms == 10_000

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await some_async_function()
    assert result is not None
```

### Running Specific Tests

```bash
# Single test file
pytest tests/test_config.py -v

# Specific test
pytest tests/test_config.py::test_config_default_values -v

# Tests matching pattern
pytest tests/ -k "config" -v
```

## Documentation

### Adding to README

- Keep it concise and well-organized
- Include code examples for features
- Link to detailed documentation

### Creating Doc Files

Store detailed documentation in the `docs/` directory:
- `docs/ARCHITECTURE.md` - System architecture
- `docs/API.md` - API reference
- `docs/EXAMPLES.md` - Usage examples

## Questions?

- **GitHub Discussions:** For general questions and discussions
- **GitHub Issues:** For bug reports and feature requests
- **Pull Requests:** For submitting code changes

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to ModalTrace! 🚀
