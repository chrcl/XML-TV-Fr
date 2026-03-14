"""XmlExporter — builds and writes XMLTV output files with optional compression.

Migrated from PHP: src/Component/XmlExporter.php
"""

from __future__ import annotations

import gzip
import os
import subprocess
import zipfile
from pathlib import Path

from lxml import etree

from xmltvfr.export.xml_formatter import XmlFormatter
from xmltvfr.utils import logger


class XmlExporter:
    """Assembles an XMLTV document and exports it in one or more formats.

    Supported output formats (selected via *output_format*):
    * ``"xml"``  — plain XMLTV file
    * ``"gz"``   — gzip-compressed XMLTV
    * ``"zip"``  — ZIP archive containing the XMLTV file
    * ``"xz"``   — 7-zip XZ archive (requires *seven_zip_path*)

    Usage
    -----
    Typical lifecycle::

        exporter = XmlExporter(output_format=["xml", "gz"], seven_zip_path=None)
        exporter.start_export("/var/export/xmltv.xml")
        exporter.add_channel("TF1.fr", "TF1", "http://...")
        exporter.add_programs_as_string(channel_xml_fragment)
        exporter.stop_export()
    """

    def __init__(self, output_format: list[str], seven_zip_path: str | None) -> None:
        self._formatter = XmlFormatter()
        self._output_format = output_format
        self._seven_zip_path = seven_zip_path
        self._root: etree._Element | None = None
        self._file_path: str = ""

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_formatter(self) -> XmlFormatter:
        """Return the embedded :class:`XmlFormatter` instance."""
        return self._formatter

    # ------------------------------------------------------------------
    # Export lifecycle
    # ------------------------------------------------------------------

    def start_export(self, file_path: str) -> None:
        """Initialise a new XMLTV document targeting *file_path*."""
        self._file_path = file_path

        self._root = etree.Element("tv")
        self._root.set("source-info-url", "https://github.com/racacax/XML-TV-Fr")
        self._root.set("source-info-name", "XML TV Fr")
        self._root.set("generator-info-name", "XML TV Fr")
        self._root.set("generator-info-url", "https://github.com/racacax/XML-TV-Fr")

    def add_channel(self, channel_key: str, name: str, icon: str | None) -> None:
        """Append a ``<channel>`` element to the document.

        Parameters
        ----------
        channel_key:
            Value for the ``id`` attribute.
        name:
            Display name text.
        icon:
            Optional icon URL; if ``None`` or empty the ``<icon>`` child is omitted.
        """
        assert self._root is not None, "start_export() must be called before add_channel()"

        channel_elem = etree.SubElement(self._root, "channel")
        channel_elem.set("id", channel_key)

        disp = etree.SubElement(channel_elem, "display-name")
        disp.text = name

        if icon:
            icon_elem = etree.SubElement(channel_elem, "icon")
            icon_elem.set("src", icon)

    def add_programs_as_string(self, programs: str) -> None:
        """Parse *programs* as XML fragments and append them to the root element.

        Parameters
        ----------
        programs:
            One or more ``<programme>`` XML elements as a string (without a
            wrapping root).  They are parsed inside a synthetic ``<root>``
            wrapper before being imported into the document.

        Raises
        ------
        etree.XMLSyntaxError
            If *programs* is not well-formed XML.
        """
        assert self._root is not None, "start_export() must be called before add_programs_as_string()"

        wrapped = f"<root>{programs}</root>"
        container = etree.fromstring(wrapped.encode("utf-8"))
        for child in container:
            self._root.append(child)

    def stop_export(self) -> None:
        """Finalise the XMLTV document and write all requested output formats."""
        assert self._root is not None, "start_export() must be called before stop_export()"

        # Serialise with pretty printing
        content = self._serialize()

        logger.log("\033[34m[EXPORT] \033[32mXML Généré\033[39m\n")

        file_path = self._file_path

        # Derive base path (without extension) and filename
        split_fp = file_path.rsplit(".", 1)
        if len(split_fp) == 1:
            shortened_file_path = file_path
        else:
            shortened_file_path = split_fp[0]
        shortened_file_name = os.path.basename(file_path)

        content_bytes = content.encode("utf-8")

        if "xml" in self._output_format or "xz" in self._output_format:
            Path(file_path).write_bytes(content_bytes)

        if "gz" in self._output_format:
            gz_filename = file_path + ".gz"
            logger.log("\033[34m[EXPORT] \033[39mCompression du XMLTV en GZ...\n")
            with gzip.open(gz_filename, "wb") as gz_file:
                gz_file.write(content_bytes)
            logger.log(f"\033[34m[EXPORT] \033[39mGZ : \033[32mOK\033[39m ({gz_filename})\n")

        if "zip" in self._output_format:
            zip_filename = shortened_file_path + ".zip"
            logger.log("\033[34m[EXPORT] \033[39mCompression du XMLTV en ZIP...\n")
            with zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(shortened_file_name, content_bytes)
            logger.log(f"\033[34m[EXPORT] \033[39mZIP : \033[32mOK\033[39m ({zip_filename})\n")

        if "xz" in self._output_format:
            if not self._seven_zip_path:
                logger.log("\033[34m[EXPORT] \033[31mImpossible d'exporter en XZ (chemin de 7zip non défini)\033[39m\n")
            else:
                xz_filename = shortened_file_path + ".xz"
                logger.log("\033[34m[EXPORT] \033[39mCompression du XMLTV en XZ...\n")
                result = subprocess.run(
                    [self._seven_zip_path, "a", "-t7z", xz_filename, file_path],
                    capture_output=True,
                    text=True,
                )
                logger.log(f"\033[34m[EXPORT] \033[39mRéponse de 7zip : {result.stdout.strip()}\n")
                if "xml" not in self._output_format:
                    Path(file_path).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _serialize(self) -> str:
        """Return the XMLTV document as a UTF-8 XML string."""
        xml_bytes = etree.tostring(
            self._root,
            encoding="unicode",
            pretty_print=True,
            xml_declaration=False,
        )
        header = '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Generated with XML TV Fr -->\n'
        return header + xml_bytes
