"""DummyChannel value object — a channel pre-filled with placeholder programs.

Migrated from PHP: src/ValueObject/DummyChannel.php
"""

from __future__ import annotations

from datetime import UTC, datetime

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program


class DummyChannel(Channel):
    """A channel populated with 12 consecutive 2-hour placeholder programs.

    Programs start at midnight on the given *date* and each carries the title
    ``"Aucun programme"``.  Icon and display name are resolved from
    :class:`~xmltvfr.domain.static.channel_factory.ChannelFactory` at runtime
    (lazy import to avoid circular dependencies).

    Parameters
    ----------
    id_:
        The channel identifier (e.g. ``"TF1"``).
    date:
        A date string accepted by :func:`datetime.fromisoformat`, e.g.
        ``"2025-01-01"``.
    """

    def __init__(self, id_: str, date: str) -> None:
        # Lazy import to avoid a circular dependency at module load time.
        from xmltvfr.domain.services.channel_factory import ChannelFactory  # noqa: PLC0415

        ref = ChannelFactory.create_channel(id_)
        icon = ref.icon
        name = ref.name

        super().__init__(id=id_, icon=icon, name=name)

        # Midnight (00:00:00 UTC) on the requested date
        midnight = datetime.fromisoformat(date).replace(tzinfo=UTC)
        base_ts = int(midnight.timestamp())
        two_hours = 2 * 3600

        for i in range(12):
            start_ts = base_ts + i * two_hours
            end_ts = start_ts + two_hours
            program = Program.with_timestamp(start_ts, end_ts)
            program.add_title("Aucun programme")
            self.add_program(program)
