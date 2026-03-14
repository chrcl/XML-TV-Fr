"""EPG cache state enumeration.

Migrated from PHP: src/ValueObject/EPGEnum.php
"""


class EPGEnum:
    """Cache-state constants for EPG data sources."""

    NO_CACHE: int = 0
    OBSOLETE_CACHE: int = 1
    PARTIAL_CACHE: int = 2
    FULL_CACHE: int = 3
