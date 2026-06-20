"""
Программный счётчик координат станка (отслеживание по приращениям).

Координаты обновляются только после получения "ok" от контроллера.
Разбираются команды G0/G1; G90 — абсолютные, G91 — относительные координаты.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from app.utils.logger import get_logger

logger = get_logger()


def _extract_float(line: str, letter: str) -> Optional[float]:
    """Извлечь значение после буквы в строке G-code."""
    pattern = rf"{letter}(-?\d+\.?\d*)"
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _is_movement_command(line: str) -> bool:
    """Проверить, является ли строка командой движения G0/G1."""
    upper = line.upper().strip()
    return "G0 " in upper or "G0\n" in upper or upper == "G0" or \
           "G1 " in upper or "G1\n" in upper or upper == "G1"


class PositionTracker(QObject):
    """
    Состояние координат станка по приращениям.

    - При отправке команды движения (G0/G1) приращения добавляются в очередь.
    - Координаты обновляются только после получения "ok".
    - reset_coordinates() обнуляет позицию (вызывать после homing).
    """

    position_updated = pyqtSignal(float, float, float)  # x, y, z

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_position: Dict[str, float] = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        }
        self.pending_moves: List[Dict[str, float]] = []
        self._is_relative = False  # G91 — относительный режим

    def get_position(self) -> Tuple[float, float, float]:
        """Текущая позиция (x, y, z)."""
        return (
            self.current_position["x"],
            self.current_position["y"],
            self.current_position["z"],
        )

    def set_position(self, x: float, y: float, z: float) -> None:
        """Установить абсолютную позицию (например, из ответа G93)."""
        self.current_position["x"] = x
        self.current_position["y"] = y
        self.current_position["z"] = z
        self.pending_moves.clear()
        self._emit_position()
        logger.info("Позиция обновлена из контроллера: X=%.3f Y=%.3f Z=%.3f", x, y, z)

    def reset_coordinates(self) -> None:
        """
        Установить координаты в ноль (вызывать после процедуры homing).
        """
        self.current_position["x"] = 0.0
        self.current_position["y"] = 0.0
        self.current_position["z"] = 0.0
        self.pending_moves.clear()
        self._emit_position()
        logger.info("Координаты сброшены (X=0 Y=0 Z=0) после homing")

    def on_line_sent(self, line: str) -> None:
        """
        Вызывать при отправке каждой строки G-code.
        Для G0/G1 добавляет приращение в очередь.
        """
        line = line.strip()
        if not line:
            return

        upper = line.upper()

        if "G90" in upper:
            self._is_relative = False
            return
        if "G91" in upper:
            self._is_relative = True
            return

        if not _is_movement_command(line):
            return

        dx, dy, dz = self._parse_movement_deltas(line)
        if dx is None and dy is None and dz is None:
            return

        self.pending_moves.append({
            "dx": dx if dx is not None else 0.0,
            "dy": dy if dy is not None else 0.0,
            "dz": dz if dz is not None else 0.0,
        })

    def _effective_position(self) -> Tuple[float, float, float]:
        """Позиция с учётом всех ещё не применённых приращений из очереди."""
        ex = self.current_position["x"]
        ey = self.current_position["y"]
        ez = self.current_position["z"]
        for m in self.pending_moves:
            ex += m["dx"]
            ey += m["dy"]
            ez += m["dz"]
        return (ex, ey, ez)

    def _parse_movement_deltas(self, line: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Извлечь приращения (dx, dy, dz) из команды G0/G1.
        В относительном режиме (G91) — значения из строки.
        В абсолютном (G90) — разница между целевой и текущей эффективной позицией.
        """
        x = _extract_float(line, "X")
        y = _extract_float(line, "Y")
        z = _extract_float(line, "Z")

        if self._is_relative:
            return (x if x is not None else 0.0, y if y is not None else 0.0, z if z is not None else 0.0)

        ex, ey, ez = self._effective_position()
        dx = (x - ex) if x is not None else None
        dy = (y - ey) if y is not None else None
        dz = (z - ez) if z is not None else None
        return (dx, dy, dz)

    def on_ok_received(self) -> None:
        """
        Вызывать при получении "ok" от контроллера.
        Берёт первый элемент из очереди, прибавляет к текущей позиции и обновляет UI.
        """
        if not self.pending_moves:
            return

        move = self.pending_moves.pop(0)
        self.current_position["x"] += move["dx"]
        self.current_position["y"] += move["dy"]
        self.current_position["z"] += move["dz"]
        self._emit_position()

    def _emit_position(self) -> None:
        x = self.current_position["x"]
        y = self.current_position["y"]
        z = self.current_position["z"]
        self.position_updated.emit(x, y, z)
        logger.debug("Позиция: X: %.2f  Y: %.2f  Z: %.2f", x, y, z)
