---
name: migration-planning
description: Explains how to produce a step-by-step migration plan for a PHP module before writing any Python code. Use after PHP code analysis and specification writing to break the migration into verifiable steps.
version: "1.0"
---

# Skill: Migration Planning

## Purpose

This skill explains how to produce a migration plan for a PHP module before writing any Python code.

> **A migration plan must be written and reviewed before any code is generated.**

## When to Use

Use this skill when:
- A developer or agent has identified a PHP module to migrate.
- A specification has been written (see `specification-writing.skill.md`).
- The PHP code analysis is complete (see `php-code-analysis.skill.md`).

## Migration Plan Structure

A migration plan must contain the following sections:

### 1. Module Summary

- PHP file(s) involved.
- Python target location (package + module path).
- Brief description of what the module does.

### 2. Pre-conditions

- List of other modules that must be migrated first (dependencies).
- Required configuration or environment changes.
- Any PHP behaviour that is intentionally NOT replicated (with justification).

### 3. Migration Steps

Break the migration into small, verifiable steps:

```
Step 1: Create data models
  - Create Python @dataclass equivalents for each PHP value object.
  - Deliverable: `python/xmltvfr/domain/models/<module>.py`

Step 2: Implement service logic
  - Translate business methods to Python functions/methods.
  - Deliverable: `python/xmltvfr/domain/services/<service>.py`

Step 3: Write unit tests
  - Cover all business rules identified in the PHP analysis.
  - Deliverable: `python/tests/unit/test_<module>.py`

Step 4: Write parity tests
  - Compare PHP and Python output for the same input data.
  - Deliverable: `python/tests/integration/test_<module>_parity.py`

Step 5: Integrate with CLI (if applicable)
  - Add or update CLI command.
  - Deliverable: `python/xmltvfr/cli/<command>.py`
```

### 4. Validation Criteria

Define what "done" means for this migration step:

- [ ] All unit tests pass.
- [ ] Parity tests pass (Python output matches PHP output for all test fixtures).
- [ ] `mypy` reports no errors.
- [ ] `ruff` and `black` report no issues.
- [ ] Code review approved.
- [ ] Documentation updated.

### 5. Risk Assessment

| Risk                        | Likelihood | Mitigation                                      |
|-----------------------------|------------|-------------------------------------------------|
| Behavior difference in edge case | Medium | Add specific parity test for edge case.       |
| Missing PHP dependency equivalent | Low   | Research PyPI alternatives, document choice.  |
| Performance regression      | Low        | Benchmark if the module is performance-critical.|

## Output

Store the migration plan in `docs/migration/` as `<module-name>-migration-plan.md`.

## Checklist Before Starting Code

- [ ] PHP code analysis complete.
- [ ] Specification written and reviewed.
- [ ] Migration plan written.
- [ ] Target Python module location agreed upon.
- [ ] Test fixtures (sample PHP input/output) identified or created.
