"""
Обёртка над QSettings для сохранения/загрузки настроек приложения
"""
from typing import Optional
from PySide6.QtCore import QSettings, QByteArray


class AppSettings:
    """
    Менеджер настроек приложения
    
    Использует QSettings для сохранения/загрузки:
    - Последний порт
    - Геометрия и состояние окна
    - Параметры отправки команд
    - Параметры джога
    """
    
    def __init__(self, org_name: str = "DeltaRobot", app_name: str = "GCodeSender"):
        self.settings = QSettings(org_name, app_name)
    
    # === Порты и подключение ===
    
    def load_last_port(self) -> Optional[str]:
        """Загрузить последний выбранный COM-порт"""
        return self.settings.value("connection/last_port")
    
    def save_last_port(self, port: str):
        """Сохранить последний выбранный COM-порт"""
        self.settings.setValue("connection/last_port", port)
    
    # Обратная совместимость
    def get_last_port(self) -> Optional[str]:
        """Получить последний выбранный COM-порт"""
        return self.load_last_port()
    
    def set_last_port(self, port: str):
        """Сохранить последний выбранный COM-порт"""
        self.save_last_port(port)
    
    def load_baud_rate(self) -> int:
        """Загрузить скорость подключения"""
        return self.settings.value("connection/baud_rate", 115200, type=int)
    
    def save_baud_rate(self, baud: int):
        """Сохранить скорость подключения"""
        self.settings.setValue("connection/baud_rate", baud)
    
    def get_baud_rate(self) -> int:
        """Получить скорость подключения"""
        return self.load_baud_rate()
    
    def set_baud_rate(self, baud: int):
        """Установить скорость подключения"""
        self.save_baud_rate(baud)
    
    # === Геометрия окна ===
    
    def load_geometry(self) -> Optional[QByteArray]:
        """Загрузить геометрию окна"""
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            return QByteArray(geometry)
        return None
    
    def save_geometry(self, geometry: QByteArray):
        """Сохранить геометрию окна"""
        self.settings.setValue("window/geometry", geometry)
    
    def restore_geometry(self) -> Optional[QByteArray]:
        """Восстановить геометрию (alias для load_geometry)"""
        return self.load_geometry()
    
    # Обратная совместимость
    def get_window_geometry(self) -> Optional[bytes]:
        """Получить геометрию окна"""
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            return bytes(geometry)
        return None
    
    def set_window_geometry(self, geometry: bytes):
        """Сохранить геометрию окна"""
        self.settings.setValue("window/geometry", geometry)
    
    def load_state(self) -> Optional[QByteArray]:
        """Загрузить состояние окна (dock panels)"""
        state = self.settings.value("window/state")
        if state is not None:
            return QByteArray(state)
        return None
    
    def save_state(self, state: QByteArray):
        """Сохранить состояние окна"""
        self.settings.setValue("window/state", state)
    
    # Обратная совместимость
    def get_window_state(self) -> Optional[bytes]:
        """Получить состояние окна"""
        state = self.settings.value("window/state")
        if state is not None:
            return bytes(state)
        return None
    
    def set_window_state(self, state: bytes):
        """Сохранить состояние окна"""
        self.settings.setValue("window/state", state)
    
    # === Параметры отправки ===
    
    def load_timeout(self) -> int:
        """Загрузить таймаут ожидания ответа (мс)"""
        return self.settings.value("commands/timeout", 5000, type=int)
    
    def save_timeout(self, timeout: int):
        """Сохранить таймаут ожидания ответа"""
        self.settings.setValue("commands/timeout", timeout)
    
    def get_command_timeout(self) -> int:
        """Получить таймаут ожидания ответа (мс)"""
        return self.load_timeout()
    
    def set_command_timeout(self, timeout: int):
        """Установить таймаут ожидания ответа"""
        self.save_timeout(timeout)
    
    def load_max_retries(self) -> int:
        """Загрузить максимальное количество повторов"""
        return self.settings.value("commands/max_retries", 3, type=int)
    
    def save_max_retries(self, retries: int):
        """Сохранить максимальное количество повторов"""
        self.settings.setValue("commands/max_retries", retries)
    
    def get_max_retries(self) -> int:
        """Получить максимальное количество повторов"""
        return self.load_max_retries()
    
    def set_max_retries(self, retries: int):
        """Установить количество повторов"""
        self.save_max_retries(retries)
    
    # === Jog параметры ===
    
    def load_jog_step(self) -> float:
        """Загрузить шаг ручного перемещения (мм)"""
        return self.settings.value("jog/step", 1.0, type=float)
    
    def save_jog_step(self, step: float):
        """Сохранить шаг ручного перемещения"""
        self.settings.setValue("jog/step", step)
    
    def get_jog_step(self) -> float:
        """Получить шаг ручного перемещения (мм)"""
        return self.load_jog_step()
    
    def set_jog_step(self, step: float):
        """Установить шаг ручного перемещения"""
        self.save_jog_step(step)
    
    def load_jog_feedrate(self) -> float:
        """Загрузить скорость джога (мм/мин)"""
        return self.settings.value("jog/feedrate", 1000.0, type=float)
    
    def save_jog_feedrate(self, feedrate: float):
        """Сохранить скорость джога"""
        self.settings.setValue("jog/feedrate", feedrate)
    
    # === Утилиты ===
    
    def clear(self):
        """Очистить все настройки"""
        self.settings.clear()
    
    def sync(self):
        """Синхронизировать настройки"""
        self.settings.sync()

