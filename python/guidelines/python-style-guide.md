# Python Style Guide — XML-TV-Fr

> This guide applies to all Python code in the `python/` directory.
> All contributors and AI agents must follow these conventions.

---

## 1. Language Version

- **Python 3.12+** is required.
- Use modern syntax: `type X = ...` type aliases, `match` statements where appropriate, `|` union types.

---

## 2. Project Structure Conventions

```
python/
├── xmltvfr/               # Main package
│   ├── __init__.py
│   ├── cli/               # CLI entry points
│   ├── config/            # Configuration
│   ├── domain/
│   │   ├── models/        # Value objects and data models
│   │   └── services/      # Business logic
│   ├── providers/         # External data providers
│   ├── export/            # Output serialization
│   └── utils/             # Shared utilities
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── pyproject.toml         # All tool configuration
└── README.md
```

Every package directory must contain an `__init__.py`.
Public exports should be declared in `__init__.py`.

---

## 3. Naming Conventions

| Element             | Convention        | Example                          |
|---------------------|-------------------|----------------------------------|
| Variables           | `snake_case`      | `channel_id`, `program_list`     |
| Functions           | `snake_case`      | `fetch_programs()`, `parse_xml()`|
| Classes             | `PascalCase`      | `Channel`, `XmlExporter`         |
| Constants           | `UPPER_SNAKE_CASE`| `DEFAULT_TIMEOUT`, `MAX_RETRIES` |
| Modules             | `snake_case`      | `xml_exporter.py`, `channel.py`  |
| Packages            | `snake_case`      | `xmltvfr/`, `domain/`            |
| Type aliases        | `PascalCase`      | `ProgramList = list[Program]`    |
| Protocol classes    | `PascalCase` + `Protocol` suffix | `ProviderProtocol`  |

---

## 4. Typing Standards

- **All** public functions and methods must have full type annotations.
- **All** class attributes must be typed.
- Use `str | None` instead of `Optional[str]` (Python 3.10+ union syntax).
- Use `list[T]` instead of `List[T]`, `dict[K, V]` instead of `Dict[K, V]`.
- Use `typing.Protocol` for structural subtyping (duck typing with type safety).
- Use `typing.TypedDict` for typed dictionary structures.
- Run `mypy --strict` as the type checking standard.

```python
# Good
def get_channel(channel_id: str) -> Channel | None:
    ...

# Bad
def get_channel(channel_id):
    ...
```

---

## 5. Python Idioms

### Use dataclasses for value objects

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    icon_url: str | None = None
```

### Use Pydantic for validated/serialized models

```python
from pydantic import BaseModel, HttpUrl


class ChannelConfig(BaseModel):
    id: str
    name: str
    icon_url: HttpUrl | None = None
```

### Use pathlib for file paths

```python
from pathlib import Path

config_path = Path("config") / "channels.json"
content = config_path.read_text(encoding="utf-8")
```

### Use f-strings for string formatting

```python
# Good
message = f"Fetching programs for channel {channel.id}"

# Bad
message = "Fetching programs for channel " + channel.id
```

### Use list/dict/set comprehensions

```python
# Good
valid_programs = [p for p in programs if p.duration > 0]

# Acceptable for complex logic
valid_programs = list(filter(lambda p: p.duration > 0, programs))
```

---

## 6. Error Handling Patterns

- Never use bare `except:` or `except Exception:` silently.
- Define custom exceptions per package in a `exceptions.py` module.
- Always provide a meaningful error message.

```python
# exceptions.py
class ProviderError(Exception):
    """Base exception for provider errors."""

class ProviderParseError(ProviderError):
    """Raised when provider response cannot be parsed."""
```

```python
# usage
try:
    programs = provider.fetch(channel_id)
except ProviderParseError as exc:
    logger.error("Failed to parse provider response: %s", exc)
    raise
```

---

## 7. Logging Best Practices

- Use the stdlib `logging` module. Never use `print()` for diagnostic output.
- Use `%s` style formatting in log calls (not f-strings), to defer formatting when log level is disabled.
- Use a named logger per module: `logger = logging.getLogger(__name__)`.
- Log levels: `DEBUG` for detailed tracing, `INFO` for normal operations, `WARNING` for unexpected but recoverable situations, `ERROR` for failures.

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Processing channel %s", channel.id)
logger.info("Exported %d programs for %s", len(programs), channel.name)
logger.warning("No programs found for channel %s", channel.id)
logger.error("Failed to fetch %s: %s", channel.id, exc)
```

---

## 8. Formatting and Linting

| Tool   | Configuration          | Purpose                     |
|--------|------------------------|-----------------------------|
| black  | `pyproject.toml`       | Code formatting (88 chars)  |
| ruff   | `pyproject.toml`       | Linting + import sorting    |
| mypy   | `pyproject.toml`       | Static type checking        |

Run before every commit:

```bash
black python/
ruff check python/
mypy python/
```

---

## 9. Testing Conventions

- All tests are in `python/tests/`.
- Test files are named `test_<module>.py`.
- Use `pytest` fixtures for shared setup (`conftest.py`).
- Do not use `unittest.TestCase` unless there is a specific reason.
- Use `pytest.raises` for exception testing.

```python
import pytest
from xmltvfr.domain.models.channel import Channel


def test_empty_channel_id_raises() -> None:
    with pytest.raises(ValueError, match="id must not be empty"):
        Channel(id="", name="TF1")
```

---

## 10. Documentation

- All public modules, classes, functions, and methods must have a docstring.
- Use Google-style docstrings.

```python
def filter_programs(programs: list[Program], min_duration: int = 0) -> list[Program]:
    """Filter programs by minimum duration.

    Args:
        programs: List of programs to filter.
        min_duration: Minimum duration in seconds (inclusive). Defaults to 0.

    Returns:
        List of programs with duration >= min_duration.
    """
    return [p for p in programs if p.duration >= min_duration]
```
