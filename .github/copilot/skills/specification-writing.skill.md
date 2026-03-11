# Skill: Specification Writing

## Purpose

This skill explains how to write a technical specification for a PHP-to-Python migration unit.

> Specifications are the contract between the PHP behaviour and the Python implementation.
> No code is written without an approved spec.

## When to Write a Spec

- Before migrating any PHP class, module, or feature to Python.
- When a developer or agent identifies a candidate for migration.
- When a bug in the PHP code should be fixed in the Python version (document the fix explicitly).

## Specification Template

Use the file `docs/specifications/spec-template.md` as a starting point.

## Required Sections

### 1. Overview

- Name of the component being specified.
- PHP source file(s).
- Python target file(s).
- Author and date.
- Status: `Draft` | `Review` | `Approved` | `Implemented`.

### 2. Purpose

One paragraph describing what this component does and why it exists in the system.

### 3. Inputs and Outputs

Describe the interface:

```
Input:
  - channel_id: str — unique identifier for the TV channel
  - start_date: datetime — start of the EPG window
  - end_date: datetime — end of the EPG window

Output:
  - list[Program] — list of programs in the given time window
```

Use Python type annotations even in the spec.

### 4. Behaviour Rules

List each business rule explicitly:

```
Rule 1: Programs must be sorted by start time in ascending order.
Rule 2: Programs with a duration of 0 must be excluded.
Rule 3: If the provider returns no data, return an empty list (do not raise an exception).
```

### 5. PHP Behaviour Reference

Describe or quote the relevant PHP logic.
Highlight any behaviour that should NOT be replicated (e.g., known bugs, deprecated features).

### 6. Edge Cases

List known edge cases and how they should be handled:

| Input Scenario              | Expected Behaviour                          |
|-----------------------------|---------------------------------------------|
| Empty program list          | Return `[]`                                 |
| Overlapping programs        | Keep both, log a warning                    |
| Malformed XML from provider | Raise `ProviderParseError` with details     |

### 7. Dependencies

List any Python packages or internal modules required.

### 8. Test Plan

Briefly describe the tests that will validate this spec:

- Unit tests for each business rule.
- Parity test comparing PHP and Python output.
- Edge case tests.

## Review Process

1. Author writes spec as `Draft`.
2. Another developer or the agent reviews it.
3. Status updated to `Review`, then `Approved`.
4. Only after `Approved` does code generation begin.

## File Naming

Store specs as:
```
docs/specifications/<component-name>-spec.md
```
