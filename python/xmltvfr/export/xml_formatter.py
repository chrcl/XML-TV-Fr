"""XmlFormatter — formats Channel/Program objects into XMLTV XML strings.

Migrated from PHP: src/Component/XmlFormatter.php
"""

from __future__ import annotations

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.domain.models.tag import Tag


class XmlFormatter:
    """Formats a :class:`~xmltvfr.domain.models.channel.Channel` and its programmes as XMLTV XML.

    The formatter also fills any mandatory XMLTV fields that are absent from a
    program (currently only ``<title>``, defaulting to ``"Aucun titre"``).
    """

    _DEFAULT_MANDATORY_FIELDS: dict[str, str] = {
        "title": "Aucun titre",
    }

    def format_channel(self, channel: Channel, provider: object | None) -> str:
        """Serialise all programs in *channel* as XMLTV ``<programme>`` elements.

        A comment line identifying the *provider* class is prepended when
        *provider* is not ``None``.  Each programme has its ``channel``
        attribute set to ``channel.id`` before serialisation.

        Parameters
        ----------
        channel:
            The channel whose programs are to be serialised.
        provider:
            The provider that fetched the EPG data (used for a comment header),
            or ``None`` if the source is unknown.

        Returns
        -------
        str
            A string of ``<programme>`` XML elements, separated by newlines.
        """
        content: list[str] = []
        if provider is not None:
            # Mimic PHP: <!-- racacax\XmlTv\Component\Provider\ProviderName -->
            provider_fqcn = f"{type(provider).__module__}.{type(provider).__name__}"
            content.append(f"<!-- {provider_fqcn} -->")

        for program in channel.get_programs():
            self._fill_mandatory_fields(program)
            program.add_attribute("channel", channel.id)
            content.append(program.as_xml())

        return "\n".join(filter(None, content))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fill_mandatory_fields(self, program: Program) -> None:
        """Ensure every mandatory XMLTV field exists on *program*."""
        for mandatory_field, default_value in self._DEFAULT_MANDATORY_FIELDS.items():
            if not program.get_children(mandatory_field):
                program.set_child(Tag(mandatory_field, default_value))
