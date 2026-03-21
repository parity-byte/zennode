# Contributing to AuDHD Pipeline

We're thrilled you want to contribute! To ensure high-quality code and prevent regressions, we strictly enforce a `uv`-based local development cycle with `ruff` and `pytest`.

## Code Standards
1. **Type Hints**: All functions must have Python parameter and return type hints.
2. **Formatting**: We use `ruff check --fix` and `ruff format`.
3. **No Hardcoded Paths**: Never use `os.path.expanduser('~')` directly in your code for application data. Use `Config.get_obsidian_vault_path()` or environment variable overrides from `config.py`.

## Getting Started
1. Fork the repo and clone it locally.
2. Install dependencies:
   ```bash
   uv sync --all-extras --dev
   ```
3. Create a branch for your feature:
   ```bash
   git checkout -b feature/my-cool-idea
   ```

## Running the Linter
Before opening a PR, run Ruff:
```bash
uv run ruff check src/
uv run ruff format src/
```

## Running Tests
We enforce rigorous testing for the Pipeline logic without actually calling the remote LLM APIs (use mocking).
```bash
uv run pytest
```

## Submitting your PR
1. Ensure GitHub Actions pass.
2. Write a clear, descriptive PR Summary explaining the "How and Why" of your change.
