"""
Контроллер подключения к COM-порту
"""
from PyQt6.QtCore import QObject, pyqtSignal
from app.services.serial_manager import SerialManager, PortInfo
from app.models.app_state import AppState, ConnectionStatus
from app.utils.logger import get_logger

logger = get_logger()


class ConnectionController(QObject):
    """
    Контроллер управления подключением к COM-порту
    
    Функции:
    - Обновление списка портов
    - Подключение/отключение
    - Обработка сигналов статуса
    - Обновление PortPanel
    """
    
    # Сигналы для UI
    ports_changed = pyqtSignal(list)  # Список PortInfo
    connected = pyqtSignal(str)  # Имя порта
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.manager = SerialManager(parent=self)
        
        # Подключаем сигналы
        self.manager.connected.connect(self._on_manager_connected)
        self.manager.disconnected.connect(self._on_manager_disconnected)
        self.manager.error.connect(self._on_manager_error)
        self.manager.ports_updated.connect(self._on_ports_updated)
        
        logger.info("ConnectionController инициализирован")
    
    def refresh_ports(self):
        """Обновить список доступных портов"""
        logger.info("Обновление списка портов...")
        self.manager.list_ports()
    
    def connect_to_port(self, port_name: str, baud_rate: int = 115200):
        """
        Подключиться к COM-порту
        
        Args:
            port_name: Имя порта (например, "COM3")
            baud_rate: Скорость (по умолчанию 115200)
        """
        if self.manager.is_connected:
            logger.warning("Уже подключено")
            return
        
        logger.info(f"Подключение к {port_name}...")
        self.app_state.set_connection_status(ConnectionStatus.CONNECTING)
        self.manager.connect(port_name, baud_rate)
    
    def disconnect_from_port(self):
        """Отключиться от COM-порта"""
        if not self.manager.is_connected:
            return
        
        logger.info("Отключение...")
        self.manager.disconnect()
    
    def _on_manager_connected(self, port_name: str):
        """Обработка подключения"""
        logger.info(f"Подключено к {port_name}")
        self.app_state.set_connection_status(ConnectionStatus.CONNECTED)
        self.app_state.set_active_port(port_name)
        self.connected.emit(port_name)
    
    def _on_manager_disconnected(self):
        """Обработка отключения"""
        logger.info("Отключено")
        self.app_state.set_connection_status(ConnectionStatus.DISCONNECTED)
        self.app_state.set_active_port(None)
        self.disconnected.emit()
    
    def _on_manager_error(self, error: str):
        """Обработка ошибки"""
        logger.error(f"Ошибка подключения: {error}")
        self.app_state.set_connection_status(ConnectionStatus.ERROR)
        self.error_occurred.emit(error)
    
    def _on_ports_updated(self, ports: list):
        """Обработка обновления списка портов"""
        logger.info(f"Получено портов: {len(ports)}")
        self.ports_changed.emit(ports)
    
    @property
    def is_connected(self) -> bool:
        """Проверить подключение"""
        return self.manager.is_connected
    
    def get_manager(self) -> SerialManager:
        """Получить менеджер COM-порта"""
        return self.manager

