"""Channel value object.

Migrated from PHP: src/ValueObject/Channel.php
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xmltvfr.domain.models.program import Program


class Channel:
    """Represents a single broadcast channel and its associated programs."""

    def __init__(self, id: str, icon: str | None, name: str | None) -> None:
        self.id: str = id
        self.icon: str | None = icon
        self.name: str | None = name
        self.programs: list[Program] = []

    # ------------------------------------------------------------------
    # Program list management
    # ------------------------------------------------------------------

    def add_program(self, program: Program) -> None:
        """Append *program* to the channel's program list."""
        self.programs.append(program)

    def order_program(self) -> None:
        """Sort programs in ascending start-time order (in-place)."""
        self.programs.sort(key=lambda p: p.get_start().timestamp())

    def pop_last_program(self) -> Program:
        """Remove and return the last program from the list.

        Raises:
            IndexError: If the program list is empty.
        """
        if not self.programs:
            raise IndexError("Cannot pop from an empty program list")
        return self.programs.pop()

    def get_programs(self) -> list[Program]:
        """Return the full list of programs."""
        return self.programs

    def get_program_count(self) -> int:
        """Return the total number of programs."""
        return len(self.programs)

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------

    def get_start_times(self) -> list[int]:
        """Return a list of each program's start time as a Unix timestamp."""
        return [int(p.get_start().timestamp()) for p in self.programs]

    def get_end_times(self) -> list[int]:
        """Return a list of each program's end time as a Unix timestamp."""
        return [int(p.get_end().timestamp()) for p in self.programs]

    def get_latest_start_date(self) -> int:
        """Return the largest start-time timestamp among all programs.

        Raises:
            ValueError: If the channel has no programs.
        """
        if not self.programs:
            raise ValueError("Cannot get latest start date from a channel with no programs")
        return max(self.get_start_times())
