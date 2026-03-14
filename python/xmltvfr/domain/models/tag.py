"""Tag value object — generic XML element builder.

Migrated from PHP: src/ValueObject/Tag.php
"""

from __future__ import annotations

import html
import sys


class Tag:
    """Represents a single XML element with optional attributes and children.

    The ``value`` field drives how the element is serialised:

    * ``None``  → self-closing tag  ``<name attr1="v1"/>``
    * ``dict``  → element with child tags  ``<name>...</name>``
    * ``str``   → element with text content  ``<name>text</name>``
    """

    def __init__(
        self,
        name: str,
        value: dict[str, list[Tag]] | str | None = None,
        attributes: dict[str, str | None] | None = None,
        sorted_children: list[str] | None = None,
    ) -> None:
        self.name: str = name
        self.value: dict[str, list[Tag]] | str | None = value
        self.attributes: dict[str, str | None] = attributes if attributes is not None else {}
        self._sorted_children: list[str] = sorted_children if sorted_children is not None else []

    # ------------------------------------------------------------------
    # Child management
    # ------------------------------------------------------------------

    def add_child(self, tag: Tag) -> None:
        """Append *tag* to the list of children keyed by tag name."""
        if not isinstance(self.value, dict):
            self.value = {}
        if tag.name not in self.value:
            self.value[tag.name] = []
        self.value[tag.name].append(tag)

    def get_children(self, tag_name: str) -> list[Tag]:
        """Return all children whose name matches *tag_name*."""
        if isinstance(self.value, dict):
            return self.value.get(tag_name, [])
        return []

    def get_all_children(self) -> list[Tag] | None:
        """Return a flat, sorted list of all children, or ``None`` if value is not a dict."""
        if not isinstance(self.value, dict):
            return None

        children: list[Tag] = []
        for tags in self.value.values():
            children.extend(tags)

        if self._sorted_children:

            def _sort_key(tag: Tag) -> int:
                try:
                    return self._sorted_children.index(tag.name)
                except ValueError:
                    return sys.maxsize

            children.sort(key=_sort_key)

        return children

    def set_child(self, tag: Tag) -> None:
        """Replace all existing children named *tag.name* with *tag*."""
        if not isinstance(self.value, dict):
            self.value = {}
        self.value[tag.name] = [tag]

    # ------------------------------------------------------------------
    # Value / attribute setters
    # ------------------------------------------------------------------

    def set_value(self, value: dict[str, list[Tag]] | str) -> None:
        """Overwrite the current value directly."""
        self.value = value

    def add_attribute(self, key: str, value: str) -> None:
        """Add or overwrite a single attribute."""
        self.attributes[key] = value

    # ------------------------------------------------------------------
    # XML serialisation
    # ------------------------------------------------------------------

    def as_xml(self) -> str:
        """Render this element as an XML string (including trailing newline)."""
        attrs = self._render_attributes()

        # Self-closing element
        if self.value is None:
            return f"<{self.name}{attrs}/>\n"

        # Element with child tags
        if isinstance(self.value, dict):
            children_xml = ""
            for tag in self.get_all_children() or []:
                children_xml += tag.as_xml()
            return f"<{self.name}{attrs}>\n{children_xml}</{self.name}>\n"

        # Element with text content
        escaped = html.escape(self.value, quote=True)
        return f"<{self.name}{attrs}>{escaped}</{self.name}>\n"

    def _render_attributes(self) -> str:
        """Build the attribute string, skipping entries whose value is ``None``."""
        parts: list[str] = []
        for key, val in self.attributes.items():
            if val is not None:
                parts.append(f'{key}="{html.escape(val, quote=True)}"')
        return (" " + " ".join(parts)) if parts else ""
