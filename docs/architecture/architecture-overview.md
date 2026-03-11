# Architecture Overview — XML-TV-Fr

> **Status:** Draft — Pre-migration
> **Last updated:** 2026-03-11
> **Audience:** Developers, AI migration agents

---

## 1. Project Purpose

XML-TV-Fr is an Electronic Program Guide (EPG) generator for French TV channels.
It fetches program data from various providers and exports it in the XMLTV format, which is consumed by media players and PVR software.

---

## 2. Current Architecture (PHP)

### High-Level Overview

```
[CLI Commands]
      │
      ▼
[Configurator]
      │
      ▼
[ChannelsManager] ──► [ChannelFactory]
      │
      ├──► [ProviderTask / ChannelThread]  ──► [External EPG Providers]
      │          │
      │          ▼
      │    [ProviderCache]
      │
      ▼
[Generator / MultiThreadedGenerator]
      │
      ▼
[XmlExporter / XmlFormatter]
      │
      ▼
[XMLTV Output File]
```

### Layer Descriptions

| Layer               | PHP Location              | Responsibility                                         |
|---------------------|---------------------------|--------------------------------------------------------|
| CLI                 | `commands/`               | Entry points: fetch, export, help                      |
| Configuration       | `src/Configurator.php`    | Load and validate channel/provider configuration       |
| Channel Management  | `src/Component/ChannelsManager.php`, `ChannelFactory.php` | Build channel list from config  |
| Provider Integration| `src/Component/ProviderTask.php`, `ProviderInterface.php` | Fetch EPG data per provider     |
| Caching             | `src/Component/ProviderCache.php`, `CacheFile.php`        | Cache provider responses        |
| Export              | `src/Component/XmlExporter.php`, `XmlFormatter.php`       | Serialize to XMLTV XML          |
| Value Objects       | `src/ValueObject/`        | Channel, Program, Tag, EPGEnum, DummyChannel           |
| Static Helpers      | `src/StaticComponent/`    | ChannelInformation, RatingPicto                        |
| Utilities           | `src/Component/Utils.php`, `Logger.php`, `ResourcePath.php` | Shared utilities              |

---

## 3. Target Architecture (Python)

### High-Level Overview

```
[CLI — cli/]
      │
      ▼
[Config — config/]
      │
      ▼
[Domain Services — domain/services/]
      │
      ├──► [Providers — providers/]  ──► [External EPG Providers]
      │          │
      │          ▼
      │    [Cache — domain/cache/]
      │
      ▼
[Export — export/]
      │
      ▼
[XMLTV Output File]
```

### Target Package Structure

```
python/
└── xmltvfr/
    ├── cli/            # CLI commands (argparse/click)
    ├── config/         # Configuration models and loaders
    ├── domain/
    │   ├── models/     # Value objects (@dataclass or Pydantic)
    │   └── services/   # Business logic
    ├── providers/      # Provider integrations (one module per provider)
    ├── export/         # XMLTV serialization
    └── utils/          # Shared utilities (logging, paths, etc.)
```

---

## 4. PHP → Python Component Mapping

| PHP Component              | Python Equivalent                                    |
|----------------------------|------------------------------------------------------|
| `src/ValueObject/Channel`  | `xmltvfr.domain.models.channel.Channel`              |
| `src/ValueObject/Program`  | `xmltvfr.domain.models.program.Program`              |
| `src/ValueObject/Tag`      | `xmltvfr.domain.models.tag.Tag`                      |
| `src/Configurator`         | `xmltvfr.config.configurator.Configurator`           |
| `src/Component/ChannelsManager` | `xmltvfr.domain.services.channels_manager`      |
| `src/Component/XmlExporter` | `xmltvfr.export.xml_exporter.XmlExporter`           |
| `src/Component/Logger`     | `xmltvfr.utils.logging` (stdlib `logging`)           |
| `commands/export.php`      | `xmltvfr.cli.export`                                 |

---

## 5. Migration Strategy

See `docs/migration/php-to-python-strategy.md` for the detailed migration plan.

The migration follows an **incremental, module-by-module** approach:
1. Value objects first (no dependencies).
2. Configuration next.
3. Business services.
4. Provider integrations.
5. Export layer.
6. CLI.

---

## 6. Quality Standards

| Concern         | Standard                                         |
|-----------------|--------------------------------------------------|
| Typing          | Full type annotations, validated by `mypy`       |
| Formatting      | `black` (88 chars/line)                          |
| Linting         | `ruff`                                           |
| Testing         | `pytest`, minimum 80% coverage on domain layer   |
| CI              | GitHub Actions (`python-quality.yml`)            |
