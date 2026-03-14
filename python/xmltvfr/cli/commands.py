"""CLI commands — entry points for the XML TV Fr command-line tool.

Migrated from PHP: commands/export.php, commands/fetch-channel.php,
                   commands/help.php, commands/update-default-logos.php,
                   manager.php
"""

from __future__ import annotations

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Individual command implementations
# ---------------------------------------------------------------------------


def cmd_export(args: argparse.Namespace) -> None:
    """Generate the XMLTV output (``export`` command).

    Reads ``config/config.json``, generates EPG data, and exports XMLTV files
    to the configured output directory.

    Optional flags:
    * ``--skip-generation`` — export using only cached data (no provider fetch).
    * ``--keep-cache``      — do not discard expired cache entries after export.
    """
    import shutil

    from xmltvfr.config.configurator import Configurator
    from xmltvfr.utils import logger

    # Ensure default config / channels files exist
    if not os.path.exists("config/config.json"):
        os.makedirs("config", exist_ok=True)
        if os.path.exists("resources/config/default_config.json"):
            shutil.copy("resources/config/default_config.json", "config/config.json")

    if not os.path.exists("config/channels.json"):
        os.makedirs("config", exist_ok=True)
        if os.path.exists("resources/config/default_channels.json"):
            shutil.copy("resources/config/default_channels.json", "config/channels.json")

    logger.set_log_level("debug")
    logger.set_log_folder("var/logs/")

    configurator = Configurator.init_from_config_file("config/config.json")
    generator = configurator.get_generator()

    if not args.skip_generation:
        generator.generate()

    generator.export_epg(configurator.output_path)

    if not args.keep_cache:
        generator.clear_cache(configurator.cache_max_days)


def cmd_fetch_channel(args: argparse.Namespace) -> None:
    """Fetch a single channel for a given provider and date (``fetch-channel`` command).

    Writes the resulting XMLTV fragment to *args.file*.

    Usage::

        xmltvfr fetch-channel TF1.fr Orange 2025-12-14 content.xml
    """
    from xmltvfr.config.configurator import Configurator
    from xmltvfr.utils.utils import colorize, get_channel_data_from_provider, get_provider

    provider_class = get_provider(args.provider)
    if provider_class is None:
        print(f"Provider '{args.provider}' not found.", file=sys.stderr)
        sys.exit(1)

    client = Configurator.get_default_client()
    provider = provider_class(client, "", 0.5)

    data = get_channel_data_from_provider(provider, args.channel, args.date)
    with open(args.file, "w", encoding="utf-8") as fh:
        fh.write(data)

    print(colorize(f"Contenu exporté vers {args.file}", "green"))


def cmd_help(_args: argparse.Namespace | None = None) -> None:
    """Print a summary of available commands (``help`` command)."""
    commands = {
        "help": "Aide à propos du programme",
        "export": (
            "Générer le XMLTV.\n\tParamètres :\n"
            "\t   --skip-generation : Réaliser l'export sans génération (utilise uniquement le cache)\n"
            "\t   --keep-cache: Garde le cache même si expiré"
        ),
        "fetch-channel": (
            "Récupérer le programme d'une chaine pour une journée et un provider donné (dans var/cache/).\n\n"
            "\tUtilisation:\n"
            "\t\txmltvfr fetch-channel [CHANNEL] [PROVIDER] [DATE] [FILENAME]\n\n"
            "\tExample:\n"
            "\t\txmltvfr fetch-channel TF1.fr Orange 2025-12-14 content.xml"
        ),
        "update-default-logos": (
            "Mettre à jour tous les logos par défaut depuis un provider donné.\n\n"
            "\tUtilisation:\n"
            "\t\txmltvfr update-default-logos [PROVIDER]\n\n"
            "\tExample:\n"
            "\t\txmltvfr update-default-logos MyCanal"
        ),
    }
    print("\033[1mListe des commandes\n")
    for name, desc in commands.items():
        print(f"\033[1m{name}\t\033[0m{desc}\n")


def cmd_update_default_logos(args: argparse.Namespace) -> None:
    """Update default channel logos from a provider (``update-default-logos`` command).

    Reads ``resources/information/default_channels_infos.json``, fetches the
    logo URL for every channel from *args.provider*, and writes the updated
    file back to disk.

    Usage::

        xmltvfr update-default-logos MyCanal
    """
    import json

    from xmltvfr.config.configurator import Configurator
    from xmltvfr.utils.utils import colorize, get_provider

    provider_class = get_provider(args.provider)
    if provider_class is None:
        print(f"Provider '{args.provider}' not found.", file=sys.stderr)
        sys.exit(1)

    client = Configurator.get_default_client()
    provider = provider_class(client, "", 0.5)

    path = "resources/information/default_channels_infos.json"
    with open(path, encoding="utf-8") as fh:
        default_channel_infos: dict = json.load(fh)

    print(colorize(f"Mise à jour des logos depuis {args.provider}...", "green"))
    count = 0
    for key in default_channel_infos:
        try:
            logo_url = provider.get_logo(key)
            if logo_url:
                count += 1
                default_channel_infos[key]["icon"] = logo_url
                print(colorize(key, "cyan"))
        except Exception:  # noqa: BLE001
            pass

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(default_channel_infos, fh, ensure_ascii=False, indent=2)

    print(colorize(f"{count} logos mis à jour", "green"))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="xmltvfr",
        description="XML TV Fr — French EPG generator",
    )
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # export
    export_parser = subparsers.add_parser("export", help="Generate the XMLTV output")
    export_parser.add_argument(
        "--skip-generation",
        dest="skip_generation",
        action="store_true",
        help="Export without fetching new data (cache only)",
    )
    export_parser.add_argument(
        "--keep-cache",
        dest="keep_cache",
        action="store_true",
        help="Keep expired cache entries after export",
    )

    # fetch-channel
    fetch_parser = subparsers.add_parser(
        "fetch-channel",
        help="Fetch EPG data for a single channel / provider / date",
    )
    fetch_parser.add_argument("channel", help="Channel key (e.g. TF1.fr)")
    fetch_parser.add_argument("provider", help="Provider class name (e.g. Orange)")
    fetch_parser.add_argument("date", help="Date in YYYY-MM-DD format")
    fetch_parser.add_argument("file", help="Output filename")

    # help (also the default)
    subparsers.add_parser("help", help="Show this help message")

    # update-default-logos
    logos_parser = subparsers.add_parser(
        "update-default-logos",
        help="Update default channel logos from a provider",
    )
    logos_parser.add_argument("provider", help="Provider class name (e.g. MyCanal)")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Parse command-line arguments and dispatch to the appropriate handler."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "export": cmd_export,
        "fetch-channel": cmd_fetch_channel,
        "help": cmd_help,
        "update-default-logos": cmd_update_default_logos,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        cmd_help()
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
