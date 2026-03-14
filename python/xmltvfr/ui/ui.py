"""UI protocol — interface for terminal display strategies.

Migrated from PHP: src/Component/UI/UI.php
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from xmltvfr.core.channels_manager import ChannelsManager


@runtime_checkable
class UIProtocol(Protocol):
    """Strategy interface for terminal display during EPG generation.

    Implementations return an *async* view coroutine that runs concurrently
    with the generator loop and refreshes the display until all channels have
    been processed.
    """

    def get_closure(
        self,
        threads: list[Any],
        manager: ChannelsManager,
        guide: dict,
        log_level: str,
        index: int,
        guides_count: int,
    ) -> Any:
        """Return a no-argument callable that, when invoked, produces a coroutine.

        The coroutine runs the display loop until all channels in *manager*
        have been processed and all *threads* have stopped running.

        Parameters
        ----------
        threads:
            List of :class:`~xmltvfr.core.channel_thread.ChannelThread` objects
            currently active for this guide.
        manager:
            The :class:`~xmltvfr.core.channels_manager.ChannelsManager` for
            this guide, used to poll channel status and events.
        guide:
            The guide configuration dict (contains at least ``"filename"``).
        log_level:
            The effective log level (``"none"`` suppresses all output).
        index:
            1-based index of the current guide (for progress display).
        guides_count:
            Total number of guides being generated.

        Returns
        -------
        Callable[[], Coroutine]
            An async function that drives the display loop.
        """
        ...
