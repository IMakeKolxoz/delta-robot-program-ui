"""
ViewModel для отображения координат дельта-робота
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, QTimer, QThread
from typing import Optional, Tuple
from app.services.coordinates_provider import ICoordinatesProvider
from app.services.serial_manager import SerialManager
from app.utils.logger import get_logger

logger = get_logger()


class CoordinatesViewModel(QObject):
    """
    ViewModel для координат дельта-робота
    
    Свойства:
    - MachineX, MachineY, MachineZ - абсолютные координаты (machine)
    - WorkX, WorkY, WorkZ - относительные координаты (рабочие)
    - IsUpdating - индикатор опроса
    """
    
    # Сигналы для обновления свойств
    machine_x_changed = pyqtSignal(float)
    machine_y_changed = pyqtSignal(float)
    machine_z_changed = pyqtSignal(float)
    work_x_changed = pyqtSignal(float)
    work_y_changed = pyqtSignal(float)
    work_z_changed = pyqtSignal(float)
    is_updating_changed = pyqtSignal(bool)
    
    def __init__(self, coordinates_provider: ICoordinatesProvider, serial_manager: Optional[SerialManager] = None, parent=None):
        """
        Инициализация ViewModel
        
        Args:
            coordinates_provider: Провайдер координат
            serial_manager: Менеджер COM-порта (для прямой отправки команд)
            parent: Родительский объект
        """
        super().__init__(parent)
        self._coordinates_provider = coordinates_provider
        self._serial_manager = serial_manager
        
        # Инициализация свойств
        self._machine_x = 0.0
        self._machine_y = 0.0
        self._machine_z = 0.0
        self._work_x = 0.0
        self._work_y = 0.0
        self._work_z = 0.0
        self._is_updating = False
        
        # Для ожидания ответа
        self._pending_response = False
        self._response_timeout_timer = QTimer(self)
        self._response_timeout_timer.setSingleShot(True)
        self._response_timeout_timer.timeout.connect(self._on_response_timeout)
        self._response_timeout_timer.setInterval(1000)  # 1 секунда таймаут
        
        # Подключаемся к сигналам SerialManager для получения ответов
        if self._serial_manager:
            self._serial_manager.line_received.connect(self._on_line_received)
            self._serial_manager.error.connect(self._on_serial_error)
        
        # Таймер для автообновления (DispatcherTimer аналог)
        # Каждые 2 секунды вызывает RefreshCoordinatesCommand автоматически, если соединение активно
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.check_connection_and_refresh)
        self._auto_refresh_timer.setInterval(2000)  # 2 секунды
        self._auto_refresh_enabled = False
        
        logger.info("CoordinatesViewModel инициализирован")
    
    # === Свойства Machine координат ===
    
    @pyqtProperty(float, notify=machine_x_changed)
    def machine_x(self) -> float:
        """Абсолютная координата X (machine)"""
        return self._machine_x
    
    @machine_x.setter
    def machine_x(self, value: float):
        if self._machine_x != value:
            self._machine_x = value
            self.machine_x_changed.emit(value)
    
    @pyqtProperty(float, notify=machine_y_changed)
    def machine_y(self) -> float:
        """Абсолютная координата Y (machine)"""
        return self._machine_y
    
    @machine_y.setter
    def machine_y(self, value: float):
        if self._machine_y != value:
            self._machine_y = value
            self.machine_y_changed.emit(value)
    
    @pyqtProperty(float, notify=machine_z_changed)
    def machine_z(self) -> float:
        """Абсолютная координата Z (machine)"""
        return self._machine_z
    
    @machine_z.setter
    def machine_z(self, value: float):
        if self._machine_z != value:
            self._machine_z = value
            self.machine_z_changed.emit(value)
    
    # === Свойства Work координат ===
    
    @pyqtProperty(float, notify=work_x_changed)
    def work_x(self) -> float:
        """Относительная координата X (work)"""
        return self._work_x
    
    @work_x.setter
    def work_x(self, value: float):
        if self._work_x != value:
            self._work_x = value
            self.work_x_changed.emit(value)
    
    @pyqtProperty(float, notify=work_y_changed)
    def work_y(self) -> float:
        """Относительная координата Y (work)"""
        return self._work_y
    
    @work_y.setter
    def work_y(self, value: float):
        if self._work_y != value:
            self._work_y = value
            self.work_y_changed.emit(value)
    
    @pyqtProperty(float, notify=work_z_changed)
    def work_z(self) -> float:
        """Относительная координата Z (work)"""
        return self._work_z
    
    @work_z.setter
    def work_z(self, value: float):
        if self._work_z != value:
            self._work_z = value
            self.work_z_changed.emit(value)
    
    # === Свойство IsUpdating ===
    
    @pyqtProperty(bool, notify=is_updating_changed)
    def is_updating(self) -> bool:
        """Индикатор опроса координат"""
        return self._is_updating
    
    @is_updating.setter
    def is_updating(self, value: bool):
        if self._is_updating != value:
            self._is_updating = value
            self.is_updating_changed.emit(value)
    
    # === Команда обновления координат ===
    
    def refresh_coordinates(self):
        """
        Команда обновления координат (RefreshCoordinatesCommand)
        
        Запрашивает координаты у контроллера через COM-порт.
        Отправляет команду через ISerialPort.WriteLineAsync() (SerialManager.send_immediate),
        ждёт ответный пакет до 1 секунды через ReadLineAsync() (сигнал line_received),
        разбирает координаты и обновляет свойства VM.
        
        Если подключение не активно, использует заглушку.
        """
        if self._is_updating:
            logger.debug("Обновление координат уже выполняется, пропускаем")
            return
        
        # Проверяем подключение
        if not self._serial_manager or not self._serial_manager.is_connected:
            logger.debug("COM-порт не подключен, используем заглушку")
            # Используем заглушку провайдера
            self.is_updating = True
            self._update_from_provider_stub()
            return
        
        logger.debug("Запрос обновления координат")
        self.is_updating = True
        self._pending_response = True
        
        try:
            # TODO: вставить команду запроса координат
            # Отправляем команду через ISerialPort.WriteLineAsync() (SerialManager.send_immediate)
            # Пока используем заглушку команды - замените на реальную команду запроса координат
            command = "M114"  # Заглушка - обычно это команда получения координат в Grbl/Marlin
            
            # Отправляем команду через SerialManager (аналог WriteLineAsync)
            self._serial_manager.send_immediate(command, wait_ok=False)
            
            # Запускаем таймер ожидания ответа (до 1 секунды, через ReadLineAsync/line_received)
            self._response_timeout_timer.start()
            
        except Exception as e:
            logger.error(f"Ошибка отправки команды запроса координат: {e}")
            self.is_updating = False
            self._pending_response = False
    
    def _on_line_received(self, line: str):
        """
        Обработка полученной строки от SerialManager
        
        Args:
            line: Полученная строка
        """
        if not self._pending_response:
            return
        
        # Останавливаем таймер
        self._response_timeout_timer.stop()
        self._pending_response = False
        
        try:
            # Парсим координаты из ответа
            # TODO: реализовать парсинг ответа контроллера
            # Пока используем заглушку - имитируем X0 Y0 Z0
            coordinates = self._parse_coordinates(line)
            
            machine_x, machine_y, machine_z, work_x, work_y, work_z = coordinates
            
            # Обновляем свойства
            self.machine_x = machine_x
            self.machine_y = machine_y
            self.machine_z = machine_z
            self.work_x = work_x
            self.work_y = work_y
            self.work_z = work_z
            
            logger.debug(f"Координаты обновлены: Machine({machine_x:.2f}, {machine_y:.2f}, {machine_z:.2f}), "
                        f"Work({work_x:.2f}, {work_y:.2f}, {work_z:.2f})")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга координат: {e}")
        finally:
            self.is_updating = False
    
    def _on_serial_error(self, error: str):
        """
        Обработка ошибки SerialManager
        
        Args:
            error: Сообщение об ошибке
        """
        if self._pending_response:
            logger.error(f"Ошибка при запросе координат: {error}")
            self._response_timeout_timer.stop()
            self._pending_response = False
            self.is_updating = False
    
    def _on_response_timeout(self):
        """Обработка таймаута ожидания ответа"""
        if self._pending_response:
            logger.warning("Таймаут ожидания ответа координат (1 секунда)")
            self._pending_response = False
            self.is_updating = False
    
    def _parse_coordinates(self, line: str) -> Tuple[float, float, float, float, float, float]:
        """
        Парсинг координат из ответа контроллера
        
        Парсер-заглушка: пока просто имитирует X0 Y0 Z0.
        В будущем здесь будет реализован реальный парсинг ответа контроллера.
        
        Args:
            line: Строка ответа от контроллера (получена через ReadLineAsync/line_received)
        
        Returns:
            Кортеж (MachineX, MachineY, MachineZ, WorkX, WorkY, WorkZ)
        """
        # TODO: реализовать реальный парсинг ответа контроллера
        # Пока возвращаем заглушку - имитируем X0 Y0 Z0
        logger.debug(f"Парсинг координат из строки: {line}")
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def _update_from_provider_stub(self):
        """Обновление координат из заглушки провайдера (для тестирования)"""
        try:
            # Используем синхронный вызов провайдера (заглушка)
            coordinates = self._coordinates_provider.get_coordinates()
            
            machine_x, machine_y, machine_z, work_x, work_y, work_z = coordinates
            
            self.machine_x = machine_x
            self.machine_y = machine_y
            self.machine_z = machine_z
            self.work_x = work_x
            self.work_y = work_y
            self.work_z = work_z
            
            logger.debug("Координаты обновлены из провайдера")
            self.is_updating = False
        except Exception as e:
            logger.error(f"Ошибка обновления координат из провайдера: {e}")
            self.is_updating = False
    
    # === Управление автообновлением ===
    
    def start_auto_refresh(self):
        """Начать автоматическое обновление координат"""
        if not self._auto_refresh_enabled:
            self._auto_refresh_enabled = True
            # Проверяем, что подключение активно
            if self._serial_manager and self._serial_manager.is_connected:
                self._auto_refresh_timer.start()
                logger.info("Автообновление координат запущено")
            else:
                logger.debug("Автообновление координат не запущено: нет подключения")
    
    def stop_auto_refresh(self):
        """Остановить автоматическое обновление координат"""
        if self._auto_refresh_enabled:
            self._auto_refresh_enabled = False
            self._auto_refresh_timer.stop()
            logger.info("Автообновление координат остановлено")
    
    def set_auto_refresh_enabled(self, enabled: bool):
        """
        Установить состояние автообновления
        
        Автообновление работает только если подключение активно.
        Таймер-обновление (DispatcherTimer) каждые 2 секунды вызывает RefreshCoordinatesCommand
        автоматически, если соединение активно.
        
        Args:
            enabled: True для включения автообновления (только если подключено)
        """
        if enabled:
            # Проверяем подключение перед запуском
            if self._serial_manager and self._serial_manager.is_connected:
                self.start_auto_refresh()
            else:
                logger.debug("Автообновление координат не запущено: нет подключения")
        else:
            self.stop_auto_refresh()
    
    def check_connection_and_refresh(self):
        """
        Проверить подключение и обновить координаты (вызывается таймером)
        
        Автоматически вызывается каждые 2 секунды, если соединение активно.
        """
        if self._serial_manager and self._serial_manager.is_connected:
            self.refresh_coordinates()
        else:
            # Если соединение потеряно, останавливаем автообновление
            if self._auto_refresh_enabled:
                self.stop_auto_refresh()

