---
name: python-architecture
description: Defines how Python modules, packages, and layers should be structured in the migrated XML-TV-Fr codebase. Use when creating new Python files or deciding where a migrated component should live.
version: "1.0"
---

# Skill: Python Architecture

## Purpose

This skill defines how Python modules, packages, and layers should be structured when building the migrated XML-TV-Fr Python codebase.

## Package Structure

```
python/
├── xmltvfr/
│   ├── __init__.py
│   ├── cli/                  # CLI entry points (Click or argparse)
│   │   └── __init__.py
│   ├── config/               # Configuration loading and validation
│   │   └── __init__.py
│   ├── domain/               # Business logic (no I/O)
│   │   ├── __init__.py
│   │   ├── models/           # Value objects and data models
│   │   └── services/         # Business services
│   ├── providers/            # EPG provider integrations
│   │   └── __init__.py
│   ├── export/               # XML/EPG export logic
│   │   └── __init__.py
│   └── utils/                # Generic utilities
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── unit/
    └── integration/
```

## Layer Responsibilities

### `domain/models/`

- Pure data structures: `@dataclass` or Pydantic `BaseModel`.
- No I/O, no external dependencies.
- Maps to PHP `src/ValueObject/`.

### `domain/services/`

- Business logic operating on domain models.
- Accepts and returns domain objects.
- No direct I/O; dependencies are injected.
- Maps to PHP `src/Component/` business logic.

### `providers/`

- Each EPG provider is a separate module.
- Implements a `ProviderProtocol` (Python `Protocol` class).
- Handles HTTP fetching and raw data parsing.
- Maps to PHP provider implementations.

### `export/`

- Converts domain objects to output formats (XML, JSON, etc.).
- No business logic; only serialization.
- Maps to PHP `src/Component/XmlExporter.php` and `XmlFormatter.php`.

### `config/`

- Loads and validates configuration from files or environment variables.
- Uses Pydantic `BaseSettings` or `@dataclass` with validation.
- Maps to PHP `src/Configurator.php`.

### `cli/`

- CLI commands using `argparse` or `click`.
- Thin wrappers: parse arguments, call domain services, handle output.
- Maps to PHP `commands/`.

## Dependency Rules

- `domain/` must NOT import from `providers/`, `export/`, or `cli/`.
- `providers/` and `export/` may import from `domain/`.
- `cli/` may import from all layers but must not contain business logic.
- Circular imports are forbidden.

## Protocols and Interfaces

Define protocols in `domain/` for any pluggable component:

```python
from typing import Protocol

class ProviderProtocol(Protocol):
    def fetch_programs(self, channel_id: str) -> list[Program]: ...
```

## Naming Conventions

| PHP concept           | Python equivalent                     |
|-----------------------|---------------------------------------|
| `ChannelInterface`    | `ChannelProtocol` (Protocol class)    |
| `ChannelFactory`      | `channel_factory.py` module or class  |
| `XmlExporter`         | `XmlExporter` class in `export/`      |
| `ValueObject`         | `@dataclass(frozen=True)`             |
