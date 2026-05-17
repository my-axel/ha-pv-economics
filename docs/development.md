# Development

## Setup

```bash
uv venv
uv pip install homeassistant pytest pytest-asyncio
```

## Tests

```bash
.venv/bin/python -m pytest
```

## Linting

```bash
.venv/bin/ruff check custom_components/pv_economics/
```
