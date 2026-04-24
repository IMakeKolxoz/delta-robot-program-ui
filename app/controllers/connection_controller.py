"""
Контроллер подключения к COM-порту
"""
from PyQt6.QtCore import QObject, pyqtSignal
from app.services.serial_manager import SerialManager, PortInfo
from app.models.app_state import AppState, ConnectionStatus
from app.utils.logger import get_logger
from typing import Optional, List, Tuple

try:
    # Типы только для аннотаций, чтобы избежать циклических импортов в рантайме
    from app.widgets.port_panel import PortPanel
    from app.widgets.console_view import ConsoleView
except Exception:  # pragma: no cover
    PortPanel = None  # type: ignore
    ConsoleView = None  # type: ignore

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
        self._port_panel: Optional[PortPanel] = None
        self._console_view: Optional[ConsoleView] = None
        
        # Подключаем сигналы
        self.manager.connected.connect(self._on_manager_connected)
        self.manager.disconnected.connect(self._on_manager_disconnected)
        self.manager.error.connect(self._on_manager_error)
        self.manager.ports_updated.connect(self._on_ports_updated)
        
        logger.info("ConnectionController инициализирован")

    def attach_port_panel(self, port_panel, console_view=None):
        """Прикрепить PortPanel (и опционально ConsoleView) к контроллеру"""
        self._port_panel = port_panel
        self._console_view = console_view
        # Подписываемся на выбор порта из панели
        try:
            port_panel.portSelected.connect(self._on_port_selected_from_panel)
        except Exception:
            pass
        # Подписываемся на кнопки подключения/отключения
        try:
            port_panel.connect_clicked.connect(self._on_connect_clicked)
            port_panel.disconnect_clicked.connect(self._on_disconnect_clicked)
        except Exception:
            pass
    
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
        # Дублируем список в консоль
        if self._console_view is not None:
            self._console_view.add_info(f"Найдено портов: {len(ports)}")
            for p in ports:
                try:
                    self._console_view.add_info(str(p))
                except Exception:
                    pass

        # Обновляем PortPanel, если прикреплён
        if self._port_panel is not None:
            tuples: List[Tuple[str, str]] = []
            for p in ports:
                device = getattr(p, 'name', None) or getattr(p, 'device', None)
                description = getattr(p, 'description', '')
                if device:
                    tuples.append((device, description))
            try:
                self._port_panel.update_ports(tuples)
            except Exception:
                pass

        # Оставляем эмит для обратной совместимости с существующими обработчиками UI
        self.ports_changed.emit(ports)
    
    @property
    def is_connected(self) -> bool:
        """Проверить подключение"""
        return self.manager.is_connected
    
    def get_manager(self) -> SerialManager:
        """Получить менеджер COM-порта"""
        return self.manager

    def _on_port_selected_from_panel(self, device: str):
        """Пользователь выбрал порт в PortPanel"""
        if device:
            # Сохраняем выбранный порт
            self.app_state.set_active_port(device)
            self.manager.set_selected_port(device)
            
            # Обновляем UI
            if self._port_panel is not None:
                try:
                    self._port_panel.set_connected_state(device, True)
                except Exception:
                    pass
            
            # Логируем в консоль
            if self._console_view is not None:
                try:
                    self._console_view.add_info(f"Выбран порт: {device}. Подключение (упрощённо) активировано.")
                except Exception:
                    pass

    def _on_connect_clicked(self):
        """Обработка кнопки 'Подключить' (упрощённая модель)"""
        selected_port = self._port_panel.get_selected_port() if self._port_panel else None
        if selected_port:
            # Просто обновляем статус, не вызываем реальное подключение
            if self._port_panel is not None:
                try:
                    self._port_panel.set_connected_state(selected_port, True)
                except Exception:
                    pass
            
            if self._console_view is not None:
                try:
                    self._console_view.add_info(f"Подключено (упрощённо): {selected_port}")
                except Exception:
                    pass
        else:
            if self._console_view is not None:
                try:
                    self._console_view.add_info("Выберите порт для подключения")
                except Exception:
                    pass

    def _on_disconnect_clicked(self):
        """Обработка кнопки 'Отключить' (упрощённая модель)"""
        # Принудительно закрываем порт, если он был открыт лениво
        self.manager.force_close()
        
        # Сбрасываем выбранный порт
        self.app_state.set_active_port(None)
        self.manager.set_selected_port(None)
        
        # Обновляем UI
        if self._port_panel is not None:
            try:
                self._port_panel.set_connected_state(None)
            except Exception:
                pass
        
        # Логируем в консоль
        if self._console_view is not None:
            try:
                self._console_view.add_info("Отключено")
            except Exception:
                pass

