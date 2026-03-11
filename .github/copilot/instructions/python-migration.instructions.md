---
description: 'Python coding instructions for the PHP-to-Python migration of XML-TV-Fr. Enforces Python 3.12+, strict typing, Pythonic idioms, and spec-first development. Applies to all Python files.'
applyTo: 'python/**'
---

# Copilot Instructions — Python Migration

## Scope

These instructions apply to all Python code generated or reviewed in the context of the PHP-to-Python migration of the XML-TV-Fr project.

> **Do not migrate code automatically without a specification.**
> Every migration step must be preceded by a written, reviewed technical specification stored in `docs/specifications/`.

---

## Coding Philosophy

- Write **Pythonic code**: use language idioms, not direct PHP translations.
- Prefer **explicit over implicit**: avoid magic, metaclasses abuse, or implicit conversions.
- Apply **strong typing** everywhere: use the `typing` module and Python 3.12+ type annotations on all function signatures and class attributes.
- Enforce **clear module boundaries**: each Python package should have a single, well-defined responsibility.
- Design for **maintainability**: future developers should be able to understand and extend the code without reading the original PHP.

---

## Preferred Tools and Standards

| Tool / Standard   | Purpose                          | Minimum Version |
|-------------------|----------------------------------|-----------------|
| Python            | Runtime                          | 3.12+           |
| `typing`          | Type annotations                 | stdlib          |
| `dataclasses`     | Simple data containers           | stdlib          |
| `pydantic`        | Validated data models            | v2+             |
| `pytest`          | Testing framework                | latest stable   |
| `ruff`            | Linting and import sorting       | latest stable   |
| `black`           | Code formatting                  | latest stable   |
| `mypy`            | Static type checking             | latest stable   |

Use `dataclasses` for simple immutable value objects.
Use `pydantic` when input validation or serialization is required (e.g., channel configuration, EPG data).

---

## Migration Rules

### PHP Classes → Python Classes

- PHP classes with only data fields → Python `@dataclass` or Pydantic `BaseModel`.
- PHP classes with behaviour → Python classes with typed methods.
- PHP interfaces → Python `Protocol` or `abc.ABC`.
- PHP abstract classes → Python `abc.ABC` with abstract methods.
- PHP static classes/helpers → Python modules with top-level functions.

### PHP Arrays → Typed Python Structures

- PHP associative arrays used as records → `@dataclass` or `TypedDict`.
- PHP lists → `list[T]` with explicit element type.
- PHP heterogeneous arrays → Named tuples or Pydantic models.

### Architecture Layers

- Separate **business logic** from framework/IO concerns.
- Keep parsers, exporters, and HTTP logic in dedicated modules.
- Business rules must be testable without any IO or external dependencies.

### Functional Equivalence

- Every migrated module must produce identical output to its PHP counterpart for the same input.
- Write **parity tests** that compare PHP and Python output before removing the PHP version.

---

## Code Style Conventions

- Use `snake_case` for variables, functions, and module names.
- Use `PascalCase` for class names.
- Use `UPPER_SNAKE_CASE` for module-level constants.
- Maximum line length: **88 characters** (Black default).
- All public functions and methods must have docstrings.
- Prefer `pathlib.Path` over `os.path` for file system operations.
- Prefer `logging` module over `print()` for diagnostic output.

---

## Error Handling

- Use specific exception types, not bare `except Exception`.
- Define custom exceptions in a `exceptions.py` module per package.
- Never silence exceptions silently; always log or re-raise.

---

## Testing Conventions

- All tests go in the `tests/` directory, mirroring the source structure.
- Test files are named `test_<module>.py`.
- Use `pytest` fixtures for shared setup.
- Aim for 80%+ coverage on migrated modules.
- Write at least one parity test per migrated module.
