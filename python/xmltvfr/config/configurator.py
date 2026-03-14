"""Configurator — top-level configuration and object factory.

Migrated from PHP: src/Configurator.php
"""

from __future__ import annotations

import json
from datetime import date as date_module
from datetime import timedelta
from typing import Any

import requests
import urllib3

from xmltvfr.utils import logger

# Silence InsecureRequestWarning from urllib3 (SSL verification is disabled
# intentionally — mirrors the PHP Guzzle ``verify => false`` setting).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Configurator:
    """Holds all runtime configuration and produces ready-to-use objects.

    All parameters mirror their PHP equivalents.  The most important entry
    point is :meth:`init_from_config_file`, which loads a ``config.json`` and
    returns a fully initialised :class:`Configurator`.

    Parameters
    ----------
    nb_days:
        Number of days of EPG data to retrieve (default: 8).
    output_path:
        Directory where XMLTV output files are written (default: ``"./var/export/"``).
    cache_max_days:
        Discard cache entries older than this many days (default: 8; 0 = no cache).
    delete_raw_xml:
        Remove the plain ``.xml`` file after compression (default: ``False``).
    enable_gz:
        Write a ``.gz`` compressed copy of the XMLTV output (default: ``True``).
    enable_zip:
        Write a ``.zip`` archive (default: ``True``).
    enable_xz:
        Write a 7-zip ``.xz`` archive — requires *zip_bin_path* (default: ``False``).
    enable_dummy:
        Insert placeholder programs for channels that returned no data (default: ``False``).
    custom_priority_orders:
        Provider-specific priority overrides, keyed by simple provider class name.
    guides_to_generate:
        List of guide configuration dicts.  Each dict must contain at least
        ``"channels"`` (path to channels JSON) and ``"filename"`` (output filename).
    zip_bin_path:
        Path to the 7-zip binary (required only when *enable_xz* is ``True``).
    force_today_grab:
        Ignore cached data for today's date and re-fetch it (default: ``False``).
    nb_threads:
        Number of parallel channel-processing threads (default: 1).
    min_time_range:
        Minimum number of seconds of coverage for a cache entry to be considered
        complete (default: ``22 * 3600`` — 22 hours).
    extra_params:
        Arbitrary extra parameters forwarded to providers.
    ui:
        A UI strategy object.  Defaults to a new :class:`~xmltvfr.ui.multi_column_ui.MultiColumnUI`.
    """

    def __init__(
        self,
        nb_days: int = 8,
        output_path: str = "./var/export/",
        cache_max_days: int = 8,
        delete_raw_xml: bool = False,
        enable_gz: bool = True,
        enable_zip: bool = True,
        enable_xz: bool = False,
        enable_dummy: bool = False,
        custom_priority_orders: dict | None = None,
        guides_to_generate: list[dict] | None = None,
        zip_bin_path: str | None = None,
        force_today_grab: bool = False,
        nb_threads: int = 1,
        min_time_range: int = 22 * 3600,
        extra_params: dict | None = None,
        ui: Any = None,
    ) -> None:
        self.nb_days = nb_days
        self.output_path = output_path
        self.cache_max_days = cache_max_days
        self.delete_raw_xml = delete_raw_xml
        self.enable_gz = enable_gz
        self.enable_zip = enable_zip
        self.enable_xz = enable_xz
        self.enable_dummy = enable_dummy
        self.custom_priority_orders: dict = custom_priority_orders or {}
        self.guides_to_generate: list[dict] = guides_to_generate or [
            {"channels": "config/channels.json", "filename": "xmltv.xml"}
        ]
        self.zip_bin_path = zip_bin_path
        self.force_today_grab = force_today_grab
        self.nb_threads = nb_threads
        self.min_time_range = min_time_range
        self.extra_params: dict = extra_params or {}

        if ui is None:
            from xmltvfr.ui.multi_column_ui import MultiColumnUI  # noqa: PLC0415

            self._ui = MultiColumnUI()
        else:
            self._ui = ui

        self._provider_list: list[Any] | None = None

    # ------------------------------------------------------------------
    # Class-level factory
    # ------------------------------------------------------------------

    @classmethod
    def init_from_config_file(cls, file_path: str) -> Configurator:
        """Load a ``config.json`` file and return a configured :class:`Configurator`.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the JSON configuration file.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        """
        import os

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(file_path, encoding="utf-8") as fh:
            data: dict = json.load(fh)

        logger.log("\033[36m[CHARGEMENT] \033[39mChargement du fichier de config\n")
        logger.log("\033[36m[CHARGEMENT] \033[39mListe des paramètres : ")
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                display_value = json.dumps(value)
            elif isinstance(value, bool):
                display_value = "true" if value else "false"
            else:
                display_value = str(value)
            logger.log(f"\033[95m({key}) \033[39m=> \033[33m{display_value}\033[39m, ")
        logger.log("\n")

        from xmltvfr.utils.utils import get_ui  # noqa: PLC0415

        return cls(
            nb_days=data.get("days", 8),
            output_path=data.get("output_path", "./xmltv"),
            cache_max_days=data.get("cache_max_days", 8),
            delete_raw_xml=data.get("delete_raw_xml", False),
            enable_gz=data.get("enable_gz", True),
            enable_zip=data.get("enable_zip", True),
            enable_xz=data.get("enable_xz", False),
            enable_dummy=data.get("enable_dummy", False),
            custom_priority_orders=data.get("custom_priority_orders", {}),
            guides_to_generate=data.get(
                "guides_to_generate",
                [{"channels": "config/channels.json", "filename": "xmltv.xml"}],
            ),
            zip_bin_path=data.get("7zip_path"),
            force_today_grab=data.get("force_todays_grab", False),
            nb_threads=data.get("nb_threads", 1),
            min_time_range=data.get("min_timerange", 22 * 3600),
            extra_params=data.get("extra_params", {}),
            ui=get_ui(data.get("ui", "MultiColumnUI")),
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_ui(self) -> Any:
        """Return the active UI strategy."""
        return self._ui

    # ------------------------------------------------------------------
    # Provider factory
    # ------------------------------------------------------------------

    def get_providers(self, client: requests.Session) -> list[Any]:
        """Return all provider instances, sorted by descending priority.

        Results are cached; subsequent calls return the same list.

        Parameters
        ----------
        client:
            HTTP client session passed to each provider's constructor.
        """
        if self._provider_list is not None:
            return self._provider_list

        from xmltvfr.utils.utils import get_providers  # noqa: PLC0415

        provider_classes = get_providers()
        provider_objects: list[Any] = []

        for provider_class in provider_classes:
            name = provider_class.__name__
            priority_override = self.custom_priority_orders.get(name)
            try:
                provider = provider_class(client, "", priority_override if priority_override is not None else 0.5)
            except Exception:  # noqa: BLE001
                continue
            provider_objects.append(provider)

        provider_objects.sort(key=lambda p: p.get_priority(), reverse=True)
        self._provider_list = provider_objects
        return self._provider_list

    # ------------------------------------------------------------------
    # Generator factory
    # ------------------------------------------------------------------

    def get_generator(self) -> Any:
        """Build and return a fully configured :class:`~xmltvfr.core.generator.Generator`.

        The generator starts from yesterday and spans *nb_days* days.  Output
        formats are selected based on the compression flags.
        """
        from xmltvfr.core.multi_threaded_generator import MultiThreadedGenerator  # noqa: PLC0415
        from xmltvfr.export.xml_exporter import XmlExporter  # noqa: PLC0415
        from xmltvfr.providers.cache_file import CacheFile  # noqa: PLC0415

        yesterday = date_module.today() - timedelta(days=1)
        stop = yesterday + timedelta(days=self.nb_days)

        generator = MultiThreadedGenerator(yesterday, stop, self)
        generator.set_providers(self.get_providers(self.get_default_client()))

        output_format: list[str] = []
        if not self.delete_raw_xml:
            output_format.append("xml")
        if self.enable_gz:
            output_format.append("gz")
        if self.enable_xz and self.zip_bin_path:
            output_format.append("xz")
        if self.enable_zip:
            output_format.append("zip")

        generator.set_exporter(XmlExporter(output_format, self.zip_bin_path))
        generator.set_cache(CacheFile("var/cache", self))
        generator.add_guides(self.guides_to_generate)

        return generator

    # ------------------------------------------------------------------
    # HTTP client factory
    # ------------------------------------------------------------------

    @staticmethod
    def get_default_client() -> requests.Session:
        """Return a pre-configured :class:`requests.Session`.

        Mirrors PHP's ``Configurator::getDefaultClient()`` Guzzle settings:
        SSL verification disabled, cookie jar enabled, and Firefox User-Agent.

        .. note::
            SSL verification is intentionally disabled (``verify=False``) to match
            the original PHP configuration (``verify => false``).  Many EPG
            providers use self-signed or misconfigured TLS certificates that
            would otherwise cause fetch failures.  No credentials are sent over
            these connections; urllib3 warnings are suppressed globally in this
            module.
        """
        session = requests.Session()
        session.verify = False  # noqa: S501 — intentional, see docstring above
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
            }
        )
        # requests.Session has a built-in cookie jar (RequestsCookieJar)
        return session
