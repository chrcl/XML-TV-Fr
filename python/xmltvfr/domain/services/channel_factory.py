"""ChannelFactory — domain service to create Channel instances.

Migrated from PHP: src/Component/ChannelFactory.php
"""

from __future__ import annotations

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.static.channel_information import ChannelInformation


class ChannelFactory:
    """Static factory that builds :class:`~xmltvfr.domain.models.channel.Channel` instances.

    Channel name and icon are resolved from
    :class:`~xmltvfr.domain.static.channel_information.ChannelInformation`.
    This class cannot be instantiated — all methods are static.
    """

    def __init__(self) -> None:
        raise TypeError("ChannelFactory is a static class and cannot be instantiated")

    @staticmethod
    def create_channel(channel_key: str) -> Channel:
        """Create a :class:`Channel` for *channel_key* using default metadata.

        Parameters
        ----------
        channel_key:
            The channel identifier (e.g. ``"TF1.fr"``).

        Returns
        -------
        Channel
            A new Channel instance populated with the default icon and name for
            the given key, or ``None`` values when no defaults are registered.
        """
        info = ChannelInformation.get_instance()
        return Channel(
            id=channel_key,
            icon=info.get_default_icon(channel_key),
            name=info.get_default_name(channel_key),
        )
