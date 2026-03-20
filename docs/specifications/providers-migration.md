# Provider Migration Specification

---

## Metadata

| Field | Value |
|---|---|
| **Component** | `Providers (remaining PHP provider set)` |
| **PHP file** | `src/Component/Provider/*.php` (except `Telerama.php`, `Tele7Jours.php`) |
| **Python target** | `python/xmltvfr/providers/*.py` |
| **Author** | `copilot` |
| **Date** | `2026-03-15` |
| **Status** | `Approved` |

---

## 1. Overview

This migration ports the remaining PHP EPG providers into the Python package so the Python runtime can discover and use the same provider set as the PHP application. The Python ports must stay close to the PHP behavior, remain additive, reuse the existing `AbstractProvider`/`ResourcePath`/`Program` infrastructure, and prioritise returning valid program content over incidental refactoring.

---

## 2. PHP Source Reference

The source of truth is the set of provider classes in `src/Component/Provider/`. The Python implementation must mirror the PHP URL generation, request headers where required, program filtering by requested day, and field mapping into `Program`/`Channel` objects. Existing Python providers `telerama.py` and `tele7jours.py` define the concrete constructor pattern and resource-path handling that new providers must follow.

---

## 3. Inputs and Outputs

**Constructor inputs:**

| Parameter | Type | Description | Required |
|---|---|---|---|
| `client` | `requests.Session` | HTTP session used by provider requests | Yes |
| `_json_path` | `str` | Ignored compatibility parameter | Yes |
| `priority` | `float` | Provider priority stored by `AbstractProvider` | Yes |
| `extra_params` | `dict[str, object] \| None` | Optional feature toggles and provider-specific overrides | No |

**Output / Return value:**

```python
Channel | bool
```

Each provider returns a populated `Channel` when the provider supports the channel and at least one program can be parsed for the requested date. It returns `False` when the channel is unsupported, the target day is outside the provider window, bootstrap data cannot be obtained, or the fetched payload does not contain usable program data.

---

## 4. Business Rules

- All concrete providers keep the compatibility constructor signature used by the current Python runtime.
- Concrete providers ignore `_json_path` and resolve the real bundled channel config with `ResourcePath.get_instance().get_channel_path(...)`.
- `construct_epg(channel, date)` must call `super().construct_epg(channel, date)` to obtain the channel object.
- Unsupported channels must return `False` immediately.
- Provider payloads are filtered to the requested calendar day using `AbstractProvider.get_min_max_date(date)` unless the PHP provider intentionally uses a different local timezone.
- Where the PHP provider merges previous-day and current-day data to compute the first in-range program, the Python provider must do the same.
- Optional detail requests must stay optional and be controlled by the same provider-specific flags as in PHP when such a flag exists.
- Browser-like headers or provider-specific API keys/user-agents must only be added where the PHP source shows they are necessary.
- The implementation should reuse small shared helpers for repeated parsing tasks, but should not introduce new abstractions that change provider behavior.

---

## 5. Behaviour NOT Replicated

| PHP Behaviour | Reason not replicated |
|---|---|
| PHP async request fan-out for some detail pages | Python ports may perform the same detail calls synchronously because the current Python provider architecture is synchronous and correctness is preferred over extra concurrency. |
| PHP echo/sleep side effects used only for CLI status or rate limiting diagnostics | Python ports keep status messages where useful but avoid reproducing unrelated CLI side effects. |

---

## 6. Edge Cases

| Scenario | Expected Python Behaviour |
|---|---|
| Unknown channel ID | Return `False` |
| Missing or malformed JSON/HTML payload | Return `False` or skip the malformed program, matching the PHP provider flow |
| First program of target day begins the previous day | Merge previous-day payload when the PHP provider does so |
| Provider requires bootstrap token/version/build-id and bootstrap fails | Return `False` for construction or leave provider unconfigured, matching PHP intent |
| Detail request fails | Keep the base program content and continue unless PHP treats the failure as fatal |

---

## 7. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| `requests` | project dependency | Existing HTTP client/session |
| `json`, `re`, `html`, `datetime`, `zoneinfo` | stdlib | Payload parsing and timezone handling |
| `xmltvfr.providers.abstract_provider.AbstractProvider` | internal | Shared provider infrastructure |
| `xmltvfr.utils.resource_path.ResourcePath` | internal | Bundled channel-config lookup |
| `xmltvfr.domain.models.channel.Channel` | internal | Provider output channel |
| `xmltvfr.domain.models.program.Program` | internal | Program XMLTV mapping |

---

## 8. Python Interface

```python
class ConcreteProvider(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None: ...

    def construct_epg(self, channel: str, date: str) -> Channel | bool: ...
```

Some providers additionally expose small internal helpers such as `generate_url(...)`, cached bootstrap methods (`get_api_key()`, `get_version()`, `get_build_id()`), or detail helpers (`add_details(...)`) when the PHP source requires them.

---

## 9. Test Plan

| Test case | Type | Description |
|---|---|---|
| `test_provider_returns_programs[...]` | Unit | For each newly migrated provider, patch channel config and HTTP responses and assert a populated `Channel` is returned with at least one program. |
| `test_provider_returns_false_for_unknown_channel[...]` | Unit | Representative providers return `False` for unsupported channels. |
| `test_provider_bootstrap_and_headers[...]` | Unit | Providers with API key/version/build-id bootstrap or required headers are exercised through mocked responses. |
| `test_provider_detail_toggle[...]` | Unit | Providers with optional detail loading preserve base program parsing when details are disabled or unavailable. |
| `pytest` | Regression | Re-run the Python test suite to ensure the migration does not break existing behavior. |

---

## 10. Review Notes

- The migration intentionally keeps the provider logic close to the PHP source rather than introducing a new generic scraping layer.
- Shared helpers should remain small and local to provider parsing concerns.
