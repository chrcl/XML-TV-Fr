# Skill: PHP Code Analysis

## Purpose

This skill describes how the migration agent should analyze legacy PHP code in the XML-TV-Fr project before proposing any Python equivalent.

## Steps

### 1. Identify Module Boundaries

- List all classes and interfaces in the file or directory being analyzed.
- Identify which classes are **value objects** (data only) vs **services** (behaviour).
- Identify **entry points** (CLI commands, public methods called from outside the module).

### 2. Map Dependencies

- List all `use` imports and external dependencies (Composer packages).
- Identify which dependencies are internal (same project) vs external (third-party libraries).
- Note any global state, static properties, or singletons.

### 3. Extract Business Logic

- Identify methods that contain business rules (transformations, validations, calculations).
- Separate business logic from I/O operations (file reads, HTTP calls, XML generation).
- Document any implicit assumptions or magic values (hardcoded strings, constants).

### 4. Assess Complexity

Rate each component:

| Level    | Description                                                   |
|----------|---------------------------------------------------------------|
| Simple   | Pure data container or single-purpose utility function.       |
| Medium   | Class with several methods, some dependencies.                |
| Complex  | Multiple dependencies, side effects, or unclear boundaries.   |

### 5. Document Findings

For each analyzed PHP component, produce a short summary:

```
Component: <ClassName>
File: <relative path>
Type: ValueObject | Service | Interface | Helper
Complexity: Simple | Medium | Complex
Dependencies: [list]
Business rules: [summary]
Side effects: [list or "none"]
Migration notes: [any special considerations]
```

## Output

The analysis output should be stored in `docs/specifications/` as part of the migration spec for that module.
