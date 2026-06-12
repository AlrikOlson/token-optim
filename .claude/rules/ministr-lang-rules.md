# Language Best Practices

Auto-generated rules based on detected project languages.

## Python

- Use type hints on all function signatures (PEP 484); run `mypy` or `pyright`
- Prefer `pathlib.Path` over `os.path` for filesystem operations
- Use `dataclasses` or `pydantic` for structured data; avoid raw dicts for domain objects
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes
- Use `ruff` or `black` for formatting, `ruff` for linting
- Prefer context managers (`with`) for resource management
- Use `pytest` for testing; prefer `fixtures` over `setUp`/`tearDown`
- Use virtual environments (`venv`, `uv`, or `poetry`) for dependency isolation
- Prefer f-strings over `.format()` or `%` formatting

