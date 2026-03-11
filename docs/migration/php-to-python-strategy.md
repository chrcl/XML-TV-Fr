# PHP-to-Python Migration Strategy

> **Project:** XML-TV-Fr
> **Last updated:** 2026-03-11
> **Status:** Draft

---

## 1. Guiding Principles

The migration from PHP to Python follows these principles:

1. **Incremental migration** — migrate one module at a time, never the whole codebase at once.
2. **Specification-first** — every module must have an approved specification before Python code is written.
3. **Parity testing** — Python output must be proven equivalent to PHP output before any PHP code is retired.
4. **Non-destructive** — PHP code is never deleted until its Python replacement is in production and validated.
5. **Reversible steps** — each migration step should be independently deployable and rollback-safe.

---

## 2. Migration Phases

### Phase 0 — Repository Preparation ✅

- Set up agent configuration, instructions, and skills.
- Create documentation structure.
- Create Python CI workflow (no-op until Python files exist).
- Write architecture overview and migration strategy.

### Phase 1 — Value Objects (Foundation)

Migrate pure data structures with no external dependencies.

**Targets:**
- `src/ValueObject/Channel.php` → `python/xmltvfr/domain/models/channel.py`
- `src/ValueObject/Program.php` → `python/xmltvfr/domain/models/program.py`
- `src/ValueObject/Tag.php` → `python/xmltvfr/domain/models/tag.py`
- `src/ValueObject/EPGEnum.php` → `python/xmltvfr/domain/models/epg_enum.py`
- `src/ValueObject/DummyChannel.php` → `python/xmltvfr/domain/models/dummy_channel.py`

**Validation:** Unit tests + parity tests for serialization.

### Phase 2 — Configuration

Migrate configuration loading and validation.

**Targets:**
- `src/Configurator.php` → `python/xmltvfr/config/configurator.py`
- Channel/provider config files → validated Pydantic models

**Validation:** Load all existing config files with the Python configurator.

### Phase 3 — Utilities and Helpers

Migrate stateless utility functions.

**Targets:**
- `src/Component/Utils.php` → `python/xmltvfr/utils/utils.py`
- `src/Component/Logger.php` → `python/xmltvfr/utils/logging.py` (wraps stdlib `logging`)
- `src/Component/ResourcePath.php` → `python/xmltvfr/utils/resource_path.py`
- `src/StaticComponent/` → `python/xmltvfr/domain/` static helpers

### Phase 4 — Provider Integrations

Migrate EPG provider fetching and parsing.

**Targets:**
- `src/Component/ProviderInterface.php` → `python/xmltvfr/providers/protocol.py`
- `src/Component/ProviderCache.php` → `python/xmltvfr/providers/cache.py`
- `src/Component/CacheFile.php` → `python/xmltvfr/providers/cache_file.py`
- Individual providers → `python/xmltvfr/providers/<provider_name>.py`

**Validation:** Integration tests with recorded HTTP fixtures (no live network calls in CI).

### Phase 5 — Business Services

Migrate orchestration and business logic.

**Targets:**
- `src/Component/ChannelFactory.php` → `python/xmltvfr/domain/services/channel_factory.py`
- `src/Component/ChannelsManager.php` → `python/xmltvfr/domain/services/channels_manager.py`
- `src/Component/ProviderTask.php` → `python/xmltvfr/domain/services/provider_task.py`
- `src/Component/Generator.php` → `python/xmltvfr/domain/services/generator.py`
- `src/Component/MultiThreadedGenerator.php` → `python/xmltvfr/domain/services/multi_threaded_generator.py`

**Validation:** Integration tests with real config files.

### Phase 6 — Export Layer

Migrate XML serialization.

**Targets:**
- `src/Component/XmlExporter.php` → `python/xmltvfr/export/xml_exporter.py`
- `src/Component/XmlFormatter.php` → `python/xmltvfr/export/xml_formatter.py`

**Validation:** Parity tests comparing PHP-generated and Python-generated XMLTV files.

### Phase 7 — CLI

Migrate command-line entry points.

**Targets:**
- `commands/export.php` → `python/xmltvfr/cli/export.py`
- `commands/fetch-channel.php` → `python/xmltvfr/cli/fetch_channel.py`
- `commands/help.php` → `python/xmltvfr/cli/help.py`
- `commands/update-default-logos.php` → `python/xmltvfr/cli/update_logos.py`

**Validation:** End-to-end tests running the Python CLI and comparing output.

### Phase 8 — Validation and Cutover

- Run full parity test suite comparing PHP and Python for all production channel configs.
- Get sign-off from maintainers.
- Update Docker image to use Python.
- Archive PHP codebase (do not delete immediately).

---

## 3. Parity Testing Strategy

Each phase includes parity tests:

1. **Capture PHP output** for a set of known inputs (stored as fixtures).
2. **Run Python implementation** on the same inputs.
3. **Assert equivalence**: XML structure, channel IDs, program times, titles.
4. **Automate in CI** so regressions are caught immediately.

---

## 4. Risk Mitigation

| Risk                               | Mitigation                                                   |
|------------------------------------|--------------------------------------------------------------|
| Silent behaviour difference        | Mandatory parity tests before retiring PHP module            |
| Provider API changes during migration | Freeze provider integration tests with recorded responses |
| PHP concurrency model vs Python    | Evaluate `concurrent.futures` or `asyncio` as replacements for PHP threads |
| Config format changes              | Keep config files identical; only change the loader          |
| Performance regression             | Benchmark generator phase before cutover                     |

---

## 5. Definition of Done (Per Module)

A module migration is complete when:

- [ ] Specification is `Approved`.
- [ ] Python implementation matches the spec.
- [ ] Unit tests pass with required coverage.
- [ ] Parity tests pass.
- [ ] `mypy` reports no errors.
- [ ] `ruff` and `black` report no issues.
- [ ] Code review approved by a maintainer.
- [ ] Documentation updated.
