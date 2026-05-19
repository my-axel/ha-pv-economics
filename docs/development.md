# Development

## Setup

```bash
uv venv
uv pip install homeassistant pytest-homeassistant-custom-component mypy ruff
```

## Tests

```bash
.venv/bin/python -m pytest
```

## Linting

```bash
.venv/bin/ruff check custom_components/pv_economics/
uv tool run mypy custom_components/pv_economics/
```
