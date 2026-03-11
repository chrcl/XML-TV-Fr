# AI-Assisted PHP-to-Python Migration — Developer Guide

## Purpose

This document explains how the AI-assisted migration infrastructure is set up in this repository and how developers should use it to convert the XML-TV-Fr PHP codebase to Python.

The setup leverages **GitHub Copilot Agents** and **Copilot Workspace** to guide, accelerate, and safeguard the migration process.

> **Important:** No PHP-to-Python translation has happened yet.
> This repository is in **Phase 0** (preparation). The PHP codebase remains untouched and authoritative.

---

## Repository Structure

```
.github/
├── copilot/
│   ├── agents/
│   │   └── python-migration-agent.md      # Agent persona and rules
│   ├── instructions/
│   │   └── python-migration.instructions.md  # Global coding instructions
│   └── skills/
│       ├── php-code-analysis.skill.md     # How to analyze PHP code
│       ├── python-architecture.skill.md   # Target Python structure
│       ├── migration-planning.skill.md    # How to plan a migration
│       ├── specification-writing.skill.md # How to write specs
│       └── test-strategy.skill.md         # How to derive tests
├── workflows/
│   └── python-quality.yml                 # CI for Python code (no-op until Python exists)
docs/
├── architecture/
│   └── architecture-overview.md          # System architecture (PHP + Python target)
├── specifications/
│   └── spec-template.md                  # Template for migration specs
└── migration/
    └── php-to-python-strategy.md         # Overall migration strategy
python/
└── guidelines/
    └── python-style-guide.md             # Python coding standards
```

---

## How to Write a Migration Specification

Before any Python code is written for a PHP module, a specification must be created and approved.

### Steps

1. **Copy the template:**
   ```bash
   cp docs/specifications/spec-template.md docs/specifications/<component-name>-spec.md
   ```

2. **Fill in the spec:**
   - Describe the PHP component's purpose and behaviour.
   - Define inputs, outputs, and business rules explicitly.
   - List edge cases and error scenarios.
   - Propose the Python interface with type annotations.

3. **Submit for review:**
   Open a Pull Request with the spec. The spec status must be updated from `Draft` to `Approved` before code is written.

4. **Use the agent:**
   In Copilot Chat, reference the spec and ask the migration agent to implement it:
   > "Using the approved spec in `docs/specifications/channel-spec.md`, implement the Python `Channel` dataclass."

---

## How to Trigger Copilot Agents

### In Copilot Chat (VS Code / GitHub)

The migration agent is configured with instructions that Copilot automatically applies when working in this repository.

Use natural language prompts that reference the agent skills:

- **Analyze PHP code:**
  > "Analyze `src/ValueObject/Channel.php` using the PHP code analysis skill and produce a component summary."

- **Write a spec:**
  > "Write a migration spec for `src/Component/XmlExporter.php` using the spec template."

- **Plan a migration:**
  > "Create a migration plan for Phase 1 value objects."

- **Generate Python code:**
  > "Implement the `Channel` dataclass in Python according to `docs/specifications/channel-spec.md`."

- **Write tests:**
  > "Write pytest tests for `Channel` following the test strategy skill."

### In Copilot Workspace

1. Open the repository in GitHub Copilot Workspace.
2. Describe your task: "Migrate `src/ValueObject/Program.php` to Python."
3. The agent will apply the migration instructions automatically.
4. Review the proposed plan before accepting any code changes.

---

## Recommended Workflow for Converting a PHP Module

```
1. SELECT a module to migrate (start with Phase 1: value objects).
         │
         ▼
2. ANALYZE the PHP code (use php-code-analysis.skill.md).
         │
         ▼
3. WRITE a specification (use spec-template.md, store in docs/specifications/).
         │
         ▼
4. REVIEW & APPROVE the specification (PR review).
         │
         ▼
5. IMPLEMENT Python code (use the agent with the approved spec).
         │
         ▼
6. WRITE tests (unit tests + parity tests).
         │
         ▼
7. RUN CI (python-quality.yml must pass: ruff, black, mypy, pytest).
         │
         ▼
8. CODE REVIEW + merge.
         │
         ▼
9. DOCUMENT the completed migration (update architecture-overview.md).
```

---

## Python CI Pipeline

The `.github/workflows/python-quality.yml` workflow runs automatically on any PR that touches the `python/` directory. It performs:

| Check        | Tool    | Description                              |
|--------------|---------|------------------------------------------|
| Lint         | `ruff`  | Code style and import order              |
| Format       | `black` | Consistent formatting (88 chars/line)    |
| Type check   | `mypy`  | Static type analysis                     |
| Tests        | `pytest`| Unit and integration tests               |

> The workflow gracefully skips all checks if no Python `.py` files exist yet, so it will not break CI during Phase 0.

---

## Rules and Guardrails

1. **Never edit PHP files** — the PHP codebase is read-only until a module is fully migrated.
2. **Never generate Python code without an approved spec.**
3. **Always run the CI pipeline** before merging Python changes.
4. **Parity tests are mandatory** — Python must match PHP output before PHP is retired.
5. **Follow the style guide** in `python/guidelines/python-style-guide.md`.

---

## Useful References

- [Architecture Overview](docs/architecture/architecture-overview.md)
- [Migration Strategy](docs/migration/php-to-python-strategy.md)
- [Spec Template](docs/specifications/spec-template.md)
- [Python Style Guide](python/guidelines/python-style-guide.md)
- [Agent Configuration](.github/copilot/agents/python-migration-agent.md)
- [Copilot Instructions](.github/copilot/instructions/python-migration.instructions.md)
