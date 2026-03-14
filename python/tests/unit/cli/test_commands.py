"""Tests for CLI commands module."""

from __future__ import annotations

from xmltvfr.cli.commands import build_parser, cmd_help


def test_build_parser_returns_parser():
    import argparse

    parser = build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_parser_export_subcommand():
    parser = build_parser()
    args = parser.parse_args(["export"])
    assert args.command == "export"
    assert not args.skip_generation
    assert not args.keep_cache


def test_parser_export_skip_generation():
    parser = build_parser()
    args = parser.parse_args(["export", "--skip-generation"])
    assert args.skip_generation


def test_parser_export_keep_cache():
    parser = build_parser()
    args = parser.parse_args(["export", "--keep-cache"])
    assert args.keep_cache


def test_parser_fetch_channel():
    parser = build_parser()
    args = parser.parse_args(["fetch-channel", "TF1.fr", "Orange", "2025-01-01", "out.xml"])
    assert args.command == "fetch-channel"
    assert args.channel == "TF1.fr"
    assert args.provider == "Orange"
    assert args.date == "2025-01-01"
    assert args.file == "out.xml"


def test_parser_update_default_logos():
    parser = build_parser()
    args = parser.parse_args(["update-default-logos", "MyCanal"])
    assert args.command == "update-default-logos"
    assert args.provider == "MyCanal"


def test_cmd_help_prints_commands(capsys):
    cmd_help()
    captured = capsys.readouterr()
    assert "export" in captured.out
    assert "fetch-channel" in captured.out
    assert "update-default-logos" in captured.out


def test_main_no_command_prints_help(capsys):
    import sys

    import pytest

    from xmltvfr.cli.commands import main

    with pytest.raises(SystemExit):
        main([])
