"""
Модель состояния приложения
"""
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from PySide6.QtCore import QObject, Signal


class ConnectionStatus(Enum):
    """Статус подключения к плате"""
    DISCONNECTED = "Отключено"
    CONNECTING = "Подключение..."
    CONNECTED = "Подключено"
    ERROR = "Ошибка"


class RunStatus(Enum):
    """Статус выполнения G-кода"""
    IDLE = "Ожидание"
    RUNNING = "Выполнение"
    PAUSED = "Пауза"
    COMPLETED = "Завершено"
    ERROR = "Ошибка"


@dataclass
class AppState(QObject):
    """
    Состояние приложения
    
    Хранит:
    - Статус подключения и текущий порт
    - Статус выполнения G-code и индекс строки
    - G-code строки и точки траектории
    - Параметры джога (шаг)
    """
    
    # Сигналы для реактивного обновления UI
    connection_status_changed = Signal(ConnectionStatus)
    run_status_changed = Signal(RunStatus)
    current_line_changed = Signal(int)
    gcode_lines_changed = Signal(list)
    active_port_changed = Signal(str)
    jog_step_changed = Signal(float)
    
    # === Параметры подключения ===
    connection_status: ConnectionStatus = field(default=ConnectionStatus.DISCONNECTED, init=False)
    active_port: Optional[str] = field(default=None, init=False)
    baud_rate: int = field(default=115200, init=False)
    
    # === G-code ===
    gcode_lines: List[str] = field(default_factory=list)
    gcode_file_path: Optional[str] = field(default=None, init=False)
    trajectory_points: List[tuple] = field(default_factory=list)  # Для TrajectoryView: List[Tuple[float, float]]
    current_line_index: int = field(default=0, init=False)
    run_status: RunStatus = field(default=RunStatus.IDLE, init=False)
    total_lines: int = field(default=0, init=False)
    
    # === Параметры джога ===
    jog_step: float = field(default=1.0, init=False)  # Шаг джога (мм)
    jog_feedrate: float = field(default=1000.0, init=False)  # Скорость джога (мм/мин)
    
    def __post_init__(self):
        super().__init__()
    
    def set_connection_status(self, status: ConnectionStatus):
        """Установить статус подключения"""
        if self.connection_status != status:
            self.connection_status = status
            self.connection_status_changed.emit(status)
    
    def set_run_status(self, status: RunStatus):
        """Установить статус выполнения"""
        if self.run_status != status:
            self.run_status = status
            self.run_status_changed.emit(status)
    
    def set_current_line(self, line_index: int):
        """Установить текущую строку G-кода"""
        if self.current_line_index != line_index:
            self.current_line_index = line_index
            self.current_line_changed.emit(line_index)
    
    def set_gcode_lines(self, lines: List[str]):
        """Установить список строк G-кода"""
        self.gcode_lines = lines
        self.total_lines = len(lines)
        self.current_line_index = 0
        self.gcode_lines_changed.emit(lines)
    
    def set_active_port(self, port: Optional[str]):
        """Установить активный COM-порт"""
        if self.active_port != port:
            self.active_port = port
            if port:
                self.active_port_changed.emit(port)
    
    def set_gcode_file_path(self, filepath: str):
        """Установить путь к файлу G-code"""
        self.gcode_file_path = filepath
    
    def set_trajectory_points(self, points: List):
        """Установить точки траектории"""
        self.trajectory_points = points
    
    def set_jog_step(self, step: float):
        """Установить шаг джога"""
        if self.jog_step != step:
            self.jog_step = step
            self.jog_step_changed.emit(step)
    
    def set_jog_feedrate(self, feedrate: float):
        """Установить скорость джога"""
        self.jog_feedrate = feedrate
    
    def reset_run_state(self):
        """Сбросить состояние выполнения"""
        self.set_current_line(0)
        self.set_run_status(RunStatus.IDLE)
    
    def get_current_gcode_line(self) -> Optional[str]:
        """Получить текущую строку G-кода"""
        if 0 <= self.current_line_index < len(self.gcode_lines):
            return self.gcode_lines[self.current_line_index]
        return None
    
    def has_next_line(self) -> bool:
        """Проверить наличие следующей строки"""
        return self.current_line_index < len(self.gcode_lines)
    
    def get_progress_percent(self) -> float:
        """Получить процент выполнения"""
        if self.total_lines == 0:
            return 0.0
        return (self.current_line_index / self.total_lines) * 100.0

