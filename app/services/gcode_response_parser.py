"""
Парсинг ответов контроллера Delta X.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_G93_COORDS_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)
_G93_COMMAND_RE = re.compile(r"\bG93\b", re.IGNORECASE)


def is_g93_command(command: str) -> bool:
    """Проверить, является ли команда запросом позиции G93."""
    return bool(_G93_COMMAND_RE.search(command.strip()))


def is_ok_response(line: str) -> bool:
    """Проверить, является ли строка подтверждением ok."""
    return line.strip().lower() == "ok"


def parse_g93_coordinates(line: str) -> Optional[Tuple[float, float, float]]:
    """
    Разобрать ответ G93 вида ``31,43,-291``.

    Returns:
        (x, y, z) или None, если строка не является координатами.
    """
    match = _G93_COORDS_RE.match(line.strip())
    if not match:
        return None
    try:
        return float(match.group(1)), float(match.group(2)), float(match.group(3))
    except ValueError:
        return None
