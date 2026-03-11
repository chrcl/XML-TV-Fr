# Skill: Test Strategy

## Purpose

This skill explains how to derive Python tests from PHP behaviour during the migration process.

## Testing Principles

1. **Tests come from behaviour, not from code.** Derive test cases from the PHP logic and documented business rules, not by reading the Python implementation.
2. **Parity tests are mandatory.** Every migrated module must have at least one test that proves Python output matches PHP output for the same input.
3. **Tests must be independent.** No test should depend on another test's side effects or execution order.
4. **Use fixtures for shared data.** Store test data in `python/tests/fixtures/` as JSON or XML files.

## Test Types

### Unit Tests

- Test a single function or class method in isolation.
- Mock all external dependencies (I/O, HTTP, database).
- Location: `python/tests/unit/test_<module>.py`

Example:
```python
def test_program_excludes_zero_duration() -> None:
    programs = [
        Program(title="News", start=datetime(2024, 1, 1, 8, 0), duration=3600),
        Program(title="Empty", start=datetime(2024, 1, 1, 9, 0), duration=0),
    ]
    result = filter_valid_programs(programs)
    assert len(result) == 1
    assert result[0].title == "News"
```

### Integration Tests

- Test interaction between multiple components.
- May use real file system but should mock HTTP.
- Location: `python/tests/integration/test_<module>_integration.py`

### Parity Tests

- Load a known PHP input fixture.
- Run both PHP (via subprocess or pre-generated output) and Python on the same input.
- Assert that outputs are identical (or equivalent within defined tolerances).
- Location: `python/tests/integration/test_<module>_parity.py`

Example structure:
```python
def test_xml_export_parity() -> None:
    channel = load_fixture("channel_tmc.json")
    programs = load_fixture("programs_tmc.json")

    php_output = load_fixture("expected_tmc_output.xml")  # pre-generated from PHP
    python_output = XmlExporter().export(channel, programs)

    assert normalize_xml(python_output) == normalize_xml(php_output)
```

### Edge Case Tests

- Explicitly test boundary conditions and error scenarios documented in specifications.
- Always test: empty input, malformed input, maximum input size.

## Deriving Tests from PHP

For each PHP method being migrated:

1. Read the PHP method and list all conditions (`if`, `foreach`, `try/catch`).
2. Each condition branch becomes at least one test case.
3. Each documented business rule becomes at least one test case.
4. Each edge case in the spec becomes at least one test case.

## Test Fixtures

- Store PHP-generated reference outputs in `python/tests/fixtures/php_reference/`.
- Store sample input data in `python/tests/fixtures/inputs/`.
- Use descriptive file names: `channel_tmc_valid.json`, `programs_empty.json`.

## Coverage Requirements

| Module type      | Minimum coverage |
|------------------|------------------|
| Domain models    | 90%              |
| Domain services  | 85%              |
| Providers        | 75%              |
| Exporters        | 80%              |
| CLI              | 60%              |

## Running Tests

```bash
# All tests
pytest python/tests/

# Unit tests only
pytest python/tests/unit/

# With coverage
pytest --cov=python/xmltvfr python/tests/
```
