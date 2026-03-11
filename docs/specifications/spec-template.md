# Migration Specification Template

> Copy this file and fill in each section for the component you are migrating.
> Status must be `Approved` before any Python code is written.

---

## Metadata

| Field         | Value                                  |
|---------------|----------------------------------------|
| **Component** | `<ComponentName>`                      |
| **PHP file**  | `src/<path>/<FileName>.php`            |
| **Python target** | `python/xmltvfr/<package>/<module>.py` |
| **Author**    | `<GitHub username>`                    |
| **Date**      | `YYYY-MM-DD`                           |
| **Status**    | `Draft` / `Review` / `Approved` / `Implemented` |

---

## 1. Overview

> Describe in one paragraph what this component does and why it exists.

_Example: The `Channel` value object represents a single TV channel with its identifier, display name, icon URL, and associated EPG provider. It is used throughout the system to carry channel metadata._

---

## 2. PHP Source Reference

> Provide the relevant PHP code snippet or a description of the PHP behaviour.

```php
// Paste or describe the relevant PHP code here
```

---

## 3. Inputs and Outputs

> Use Python type annotations.

**Constructor / Factory inputs:**

| Parameter   | Type    | Description                          | Required |
|-------------|---------|--------------------------------------|----------|
| `id`        | `str`   | Unique channel identifier            | Yes      |
| `name`      | `str`   | Display name                         | Yes      |
| `icon_url`  | `str \| None` | URL of the channel logo       | No       |

**Output / Return value:**

```python
# Example
@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    icon_url: str | None = None
```

---

## 4. Business Rules

> List each rule explicitly and unambiguously.

- **Rule 1:** `id` must be a non-empty string.
- **Rule 2:** `name` must be a non-empty string.
- **Rule 3:** `icon_url`, if provided, must be a valid URL starting with `http://` or `https://`.
- _(Add more rules as needed)_

---

## 5. Behaviour NOT Replicated

> List any PHP behaviour that should intentionally NOT be replicated in Python (e.g., known bugs, deprecated features).

| PHP Behaviour               | Reason not replicated                        |
|-----------------------------|----------------------------------------------|
| _(none)_                    |                                              |

---

## 6. Edge Cases

| Scenario                         | Expected Python Behaviour                        |
|----------------------------------|--------------------------------------------------|
| `id` is empty string             | Raise `ValueError("Channel id must not be empty")` |
| `icon_url` is invalid URL        | Raise `ValueError("Invalid icon_url: ...")`      |
| _(add more)_                     |                                                  |

---

## 7. Dependencies

| Dependency             | Type       | Notes                                   |
|------------------------|------------|-----------------------------------------|
| `dataclasses`          | stdlib     | For `@dataclass`                        |
| _(add more)_           |            |                                         |

---

## 8. Python Interface

> Show the proposed Python class/function signature with full type annotations.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    """Represents a single TV channel."""

    id: str
    name: str
    icon_url: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Channel id must not be empty")
        if not self.name:
            raise ValueError("Channel name must not be empty")
```

---

## 9. Test Plan

| Test case                        | Type    | Description                                          |
|----------------------------------|---------|------------------------------------------------------|
| `test_valid_channel_creation`    | Unit    | Create a channel with valid data, assert attributes. |
| `test_empty_id_raises`           | Unit    | Empty id raises `ValueError`.                        |
| `test_parity_with_php`           | Parity  | Python output matches PHP reference fixture.         |
| _(add more)_                     |         |                                                      |

---

## 10. Review Notes

> Add reviewer comments here during the Review phase.

_(none yet)_
