"""ProviderProtocol — Python equivalent of ProviderInterface.php."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from xmltvfr.domain.models.channel import Channel


@runtime_checkable
class ProviderProtocol(Protocol):
    def construct_epg(self, channel: str, date: str) -> Channel | bool: ...

    @classmethod
    def get_priority(cls) -> float: ...

    def channel_exists(self, channel: str) -> bool: ...

    def get_channels_list(self) -> dict: ...

    def get_channel_state_from_times(
        self,
        start_times: list[int],
        end_times: list[int],
        config: object,
    ) -> int: ...

    @classmethod
    def get_min_max_date(cls, date: str) -> tuple: ...
