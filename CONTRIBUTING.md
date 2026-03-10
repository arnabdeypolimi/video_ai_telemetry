# Contributing to ModalTrace

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/video-ai-telemetry.git
cd video-ai-telemetry
git remote add upstream https://github.com/arnabdeypolimi/video-ai-telemetry.git
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch prefixes: `feature/`, `fix/`, `docs/`, `refactor/`

### 3. Set Up the Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,all]"
```

## Development Workflow

```bash
# Lint
ruff check src/ tests/
ruff format src/ tests/

# Tests
pytest tests/ -v

# Type check
mypy src/
```

## Making Changes

### Code Style

- Follow PEP 8
- Add docstrings to public functions/classes
- Keep functions focused

### Adding Features

1. Write failing tests in `tests/test_feature.py`
2. Implement the feature following existing patterns
3. Verify all tests pass
4. Update docs if the public API changed

### Bug Fixes

1. Write a test that reproduces the bug
2. Fix the bug
3. Confirm the test passes and no regressions

## Commit Guidelines

```
Short summary (50 chars max)

Longer explanation if needed (72 chars per line).
Explain why, not what.

Fixes #123
```

## Submitting Changes

1. Push to your fork: `git push origin feature/your-feature-name`
2. Open a PR against `main` with a clear title and description
3. Address any review feedback with new commits

### PR Description should include

- What changed and why
- How to test it
- Related issues (`Fixes #123`)

## Testing

```
tests/
├── test_module.py
├── conftest.py
└── ...
```

```python
import pytest
from modaltrace import ModalTraceConfig

def test_config_default_values():
    config = ModalTraceConfig()
    assert config.service_name == "modaltrace-pipeline"
    assert config.otlp_timeout_ms == 10_000

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

Run a specific test:

```bash
pytest tests/test_config.py::test_config_default_values -v
```

## Documentation

- `docs/ARCHITECTURE.md` — system architecture
- `docs/API.md` — API reference
- `docs/EXAMPLES.md` — usage examples

## Questions

- **GitHub Discussions** — general questions
- **GitHub Issues** — bugs and feature requests
- **Pull Requests** — code contributions

By contributing, you agree your work will be licensed under Apache License 2.0.
