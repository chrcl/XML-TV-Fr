"""Tests for XmlExporter."""

from __future__ import annotations

import gzip
import zipfile
from pathlib import Path

import pytest

from xmltvfr.export.xml_exporter import XmlExporter


def test_start_export_creates_root(tmp_path):
    exporter = XmlExporter(output_format=["xml"], seven_zip_path=None)
    exporter.start_export(str(tmp_path / "xmltv.xml"))
    # Should not raise; root is created internally


def test_add_channel_and_stop_export_writes_file(tmp_path):
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=["xml"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_channel("TF1.fr", "TF1", "http://icon.png")
    exporter.stop_export()

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "<tv" in content
    assert 'id="TF1.fr"' in content
    assert "TF1" in content
    assert 'src="http://icon.png"' in content


def test_add_channel_no_icon(tmp_path):
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=["xml"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_channel("TF1.fr", "TF1", None)
    exporter.stop_export()

    content = out.read_text(encoding="utf-8")
    assert "<icon" not in content


def test_add_programs_as_string(tmp_path):
    out = tmp_path / "xmltv.xml"
    prog_xml = (
        '<programme start="20251214120000 +0100" stop="20251214130000 +0100" channel="TF1.fr">'
        "<title>Show</title></programme>"
    )
    exporter = XmlExporter(output_format=["xml"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_programs_as_string(prog_xml)
    exporter.stop_export()

    content = out.read_text(encoding="utf-8")
    assert "Show" in content


def test_gz_compression(tmp_path):
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=["xml", "gz"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_channel("TF1.fr", "TF1", None)
    exporter.stop_export()

    gz_file = Path(str(out) + ".gz")
    assert gz_file.exists()
    with gzip.open(gz_file, "rb") as f:
        decompressed = f.read().decode("utf-8")
    assert "<tv" in decompressed


def test_zip_compression(tmp_path):
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=["xml", "zip"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_channel("TF1.fr", "TF1", None)
    exporter.stop_export()

    zip_file = tmp_path / "xmltv.zip"
    assert zip_file.exists()
    with zipfile.ZipFile(zip_file, "r") as zf:
        names = zf.namelist()
        assert len(names) == 1
        content = zf.read(names[0]).decode("utf-8")
    assert "<tv" in content


def test_xz_without_path_skips(tmp_path, capsys):
    """XZ export without a 7zip path should log a warning and skip."""
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=["xz"], seven_zip_path=None)
    exporter.start_export(str(out))
    exporter.add_channel("TF1.fr", "TF1", None)
    exporter.stop_export()
    # No .xz file should be produced
    assert not (tmp_path / "xmltv.xz").exists()


def test_get_formatter_returns_xml_formatter():
    from xmltvfr.export.xml_formatter import XmlFormatter

    exporter = XmlExporter(output_format=[], seven_zip_path=None)
    assert isinstance(exporter.get_formatter(), XmlFormatter)


def test_add_programs_invalid_xml_raises(tmp_path):
    out = tmp_path / "xmltv.xml"
    exporter = XmlExporter(output_format=[], seven_zip_path=None)
    exporter.start_export(str(out))
    with pytest.raises(Exception):
        exporter.add_programs_as_string("<unclosed>")
