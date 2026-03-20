from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any


def strip_tags(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"<[^>]+>", "", html.unescape(value)).strip()


def match1(pattern: str, content: str, flags: int = 0) -> str | None:
    match = re.search(pattern, content, flags)
    return match.group(1) if match else None


def safe_json_loads(content: str) -> Any:
    try:
        return json.loads(content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None
