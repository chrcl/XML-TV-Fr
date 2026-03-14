"""ProviderTask — executes a single provider fetch in a worker thread.

Migrated from PHP: src/Component/ProviderTask.php
"""

from __future__ import annotations

from collections.abc import Callable

from xmltvfr.utils.utils import get_channel_data_from_provider, get_provider


class ProviderTask:
    """Fetches EPG data for one channel / date / provider combination.

    Intended to be executed via :func:`asyncio.to_thread` so that the blocking
    HTTP I/O does not stall the asyncio event loop.

    Parameters
    ----------
    provider_name:
        Simple class name of the provider (e.g. ``"Orange"``).
    date:
        Date string in ``"YYYY-MM-DD"`` format.
    channel_id:
        Channel identifier (e.g. ``"TF1.fr"``).
    extra_params:
        Optional extra configuration passed through from the
        :class:`~xmltvfr.config.configurator.Configurator`.
    status_callback:
        Optional callable invoked by the provider to report progress strings.
    """

    def __init__(
        self,
        provider_name: str,
        date: str,
        channel_id: str,
        extra_params: dict | None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._date = date
        self._channel_id = channel_id
        self._extra_params = extra_params or {}
        self._status_callback = status_callback

    def run_sync(self) -> str:
        """Execute the provider fetch synchronously and return the result.

        Returns
        -------
        str
            Formatted XMLTV fragment (``<programme>`` elements), or ``"false"``
            when no data could be retrieved.
        """
        import requests

        provider_class = get_provider(self._provider_name)
        if provider_class is None:
            return "false"

        # Build a new HTTP session for this worker (mirrors PHP ProviderTask.run).
        # SSL verification is intentionally disabled to match the original PHP
        # Guzzle configuration (``verify => false``).  Many EPG providers use
        # self-signed or misconfigured certificates that would otherwise cause
        # fetch failures.  urllib3 warnings are suppressed at the Configurator
        # level; no credentials travel over these connections.
        client = requests.Session()
        client.verify = False  # noqa: S501 — intentional, see comment above
        client.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
            }
        )

        try:
            provider = provider_class(client, "", 0.5)
        except Exception:  # noqa: BLE001
            return "false"

        if self._status_callback is not None:
            provider.set_status_callback(self._status_callback)

        return get_channel_data_from_provider(provider, self._channel_id, self._date)
