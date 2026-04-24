"""
Менеджер COM-порта для коммуникации с Arduino через QThread
"""
import serial
from serial.tools import list_ports
from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from app.utils.logger import get_logger

logger = get_logger()


class PortInfo:
    """Информация о COM-порте"""
    def __init__(self, name: str, description: str, device: Optional[str] = None):
        self.name = name
        self.description = description
        self.device = device
    
    def __str__(self) -> str:
        return f"{self.name} - {self.description}"


class SerialWorker(QObject):
    """Рабочий объект для работы с COM-портом в отдельном потоке"""
    
    # Сигналы для обмена данными
    data_received = pyqtSignal(str)  # Получены данные от платы
    data_sent = pyqtSignal(str)  # Отправлены данные на плату
    error_occurred = pyqtSignal(str)  # Ошибка
    ok_received = pyqtSignal()  # Получено ok
    
    # Внутренние сигналы
    _connect_requested = pyqtSignal(str, int)
    _disconnect_requested = pyqtSignal()
    _send_requested = pyqtSignal(str, bool)  # команда, wait_ok
    _start_queue_requested = pyqtSignal()
    _pause_requested = pyqtSignal()
    _resume_requested = pyqtSignal()
    _stop_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.serial_port: Optional[serial.Serial] = None
        self.queue: List[str] = []
        self.current_index = 0
        self.is_running = False
        self.is_paused = False
        self._response_buffer = ""
        self._connecting = False  # Флаг подключения
        
        # Подключаем слоты
        self._connect_requested.connect(self._connect)
        self._disconnect_requested.connect(self._disconnect)
        self._send_requested.connect(self._send_command)
        self._start_queue_requested.connect(self._start_queue)
        self._pause_requested.connect(self._pause)
        self._resume_requested.connect(self._resume)
        self._stop_requested.connect(self._stop)
    
    @pyqtSlot(str, int)
    def _connect(self, port_name: str, baud_rate: int):
        """Подключиться к порту"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baud_rate,
                timeout=0.5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            logger.info(f"Подключено к {port_name}")
            self.data_sent.emit(f"Connected to {port_name}")
            
            # Сбрасываем флаг подключения при успехе
            self._connecting = False
            
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            # Сбрасываем флаг подключения при ошибке
            self._connecting = False
            self.error_occurred.emit(str(e))
    
    @pyqtSlot()
    def _disconnect(self):
        """Отключиться от порта"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = None
            # Сбрасываем флаг подключения при отключении
            self._connecting = False
            logger.info("Отключено")
        except Exception as e:
            logger.error(f"Ошибка отключения: {e}")
            # Сбрасываем флаг подключения при ошибке
            self._connecting = False
    
    @pyqtSlot(str, bool)
    def _send_command(self, command: str, wait_ok: bool = True):
        """Отправить команду"""
        if not self.serial_port or not self.serial_port.is_open:
            self.error_occurred.emit("Не подключено")
            return
        
        try:
            command_line = command.strip() + "\n"
            self.serial_port.write(command_line.encode('utf-8'))
            self.serial_port.flush()
            
            self.data_sent.emit(command)
            logger.info(f"→ {command}")
            
            if wait_ok:
                self._wait_for_ok()
            else:
                self.ok_received.emit()
                
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            self.error_occurred.emit(str(e))
    
    def _wait_for_ok(self):
        """Ожидать ответ ok"""
        # Читаем данные в цикле
        timeout_ms = 5000  # 5 секунд
        elapsed = 0
        
        while True:
            if not self.serial_port or not self.serial_port.is_open:
                break
            
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    self._response_buffer += data
                    
                    # Проверяем на наличие "ok" (без учета регистра)
                    if "ok" in self._response_buffer.lower():
                        logger.info("← ok")
                        self.data_received.emit(self._response_buffer.strip())
                        self._response_buffer = ""
                        self.ok_received.emit()
                        return
                
                # Проверка таймаута
                elapsed += 100
                if elapsed >= timeout_ms:
                    self.error_occurred.emit("Таймаут ожидания ok")
                    break
                
                QThread.msleep(100)  # 100мс задержка
                
            except Exception as e:
                logger.error(f"Ошибка чтения: {e}")
                self.error_occurred.emit(str(e))
                break
    
    @pyqtSlot()
    def _start_queue(self):
        """Начать отправку очереди"""
        if not self.queue:
            logger.warning("Очередь пуста")
            return
        
        self.is_running = True
        self.is_paused = False
        self.current_index = 0
        self._send_next_in_queue()
    
    @pyqtSlot()
    def _pause(self):
        """Пауза отправки очереди"""
        self.is_paused = True
    
    @pyqtSlot()
    def _resume(self):
        """Возобновить отправку очереди"""
        self.is_paused = False
        self._send_next_in_queue()
    
    @pyqtSlot()
    def _stop(self):
        """Остановить отправку очереди"""
        self.is_running = False
        self.is_paused = False
        self.queue = []
        self.current_index = 0
    
    def _send_next_in_queue(self):
        """Отправить следующую команду из очереди"""
        if not self.is_running or self.is_paused:
            return
        
        if self.current_index >= len(self.queue):
            logger.info("Очередь завершена")
            self.is_running = False
            self.queue = []
            self.current_index = 0
            return
        
        command = self.queue[self.current_index]
        self._send_command(command, wait_ok=True)
        self.current_index += 1
    
    def set_queue(self, commands: List[str]):
        """Установить очередь команд"""
        self.queue = commands.copy()


class SerialManager(QObject):
    """
    Менеджер COM-порта для коммуникации с Arduino
    
    Использует QThread для неблокирующей работы с портом
    """
    
    # Сигналы для UI
    connected = pyqtSignal(str)  # Порт подключен
    disconnected = pyqtSignal()
    ports_updated = pyqtSignal(list)  # Список портов обновлен
    line_sent = pyqtSignal(str)  # Отправлена строка
    line_received = pyqtSignal(str)  # Получена строка
    ok_received = pyqtSignal()  # Получено ok
    error = pyqtSignal(str)  # Ошибка
    progress = pyqtSignal(int, int)  # Текущая строка, всего строк
    queue_completed = pyqtSignal()  # Очередь завершена
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем thread и worker
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)
        
        # Подключаем сигналы worker -> manager
        self.worker.data_sent.connect(self._on_data_sent)
        self.worker.data_received.connect(self._on_data_received)
        self.worker.ok_received.connect(self._on_ok_received)
        self.worker.error_occurred.connect(self._on_error)
        
        # Переопределяем ok_received для продолжения очереди
        self.worker.ok_received.connect(self._on_queue_continue)
        
        # Запускаем thread
        self.thread.start()
        
        # Состояние
        self._connected_port: Optional[str] = None
        self._selected_port: Optional[str] = None  # Выбранный пользователем порт
    
    @property
    def is_connected(self) -> bool:
        """Проверить подключение"""
        return self._connected_port is not None
    
    def set_selected_port(self, device: str) -> None:
        """
        Установить выбранный порт (без открытия)
        
        Args:
            device: Имя порта (например, "COM3")
        """
        self._selected_port = device
        logger.info(f"Выбран порт: {device}")
    
    def ensure_open(self, baud: int = 115200) -> bool:
        """
        Проверка: открыт ли порт. Без автоматического подключения.
        """
        if self._connected_port:
            return True
        self.error.emit("Не подключено")
        return False
    
    def force_close(self) -> None:
        """Принудительно закрыть порт"""
        if self._connected_port:
            logger.info(f"Принудительное закрытие порта {self._connected_port}")
            self.worker._disconnect_requested.emit()
            self._connected_port = None
            self.disconnected.emit()
    
    def list_ports(self) -> List[PortInfo]:
        """
        Получить список доступных COM-портов
        
        Returns:
            Список PortInfo
        """
        ports = []
        for port in list_ports.comports():
            # Эвристика для Arduino Mega - ищем "Arduino" в описании
            info = PortInfo(port.device, port.description)
            ports.append(info)
        
        # Эмитируем сигнал обновления
        self.ports_updated.emit(ports)
        return ports
    
    def connect(self, port_name: str, baud: int = 115200):
        """
        Подключиться к COM-порту (legacy method)
        
        Args:
            port_name: Имя порта (например, "COM3")
            baud: Скорость (по умолчанию 115200)
        """
        if self._connected_port:
            self.error.emit("Уже подключено")
            return
        
        logger.info(f"Подключение к {port_name}...")
        self._selected_port = port_name
        self.worker._connect_requested.emit(port_name, baud)
    
    def disconnect(self):
        """Отключиться от COM-порта"""
        if not self._connected_port:
            return
        
        logger.info("Отключение...")
        self.worker._disconnect_requested.emit()
        self._connected_port = None
        self.disconnected.emit()
    
    def enqueue(self, line: str):
        """
        Добавить строку в очередь
        
        Args:
            line: Строка G-code
        """
        self.worker.queue.append(line)
    
    def enqueue_batch(self, lines: List[str]):
        """
        Добавить несколько строк в очередь
        
        Args:
            lines: Список строк G-code
        """
        self.worker.queue.extend(lines)
    
    def start_queue(self):
        """Начать отправку очереди"""
        # Проверяем подключение только если порт не открыт
        if not self._connected_port and not self.ensure_open():
            return
        
        if not self.worker.queue:
            self.error.emit("Очередь пуста")
            return
        
        logger.info(f"Начало отправки очереди: {len(self.worker.queue)} команд")
        self.worker._start_queue_requested.emit()
    
    def pause(self):
        """Пауза отправки очереди"""
        self.worker._pause_requested.emit()
    
    def resume(self):
        """Возобновить отправку очереди"""
        self.worker._resume_requested.emit()
    
    def stop(self):
        """Остановить отправку очереди"""
        self.worker._stop_requested.emit()
    
    def send_immediate(self, line: str, wait_ok: bool = True):
        """
        Отправить команду немедленно (вне очереди)
        
        Args:
            line: Строка G-code
            wait_ok: Ждать ответ ok
        """
        # Проверяем подключение только если порт не открыт
        if not self._connected_port and not self.ensure_open():
            return
        
        self.worker._send_requested.emit(line, wait_ok)
    
    def _on_data_sent(self, data: str):
        """Обработка отправленных данных"""
        # Детектируем успешное подключение по сервисному сообщению
        if data.startswith("Connected to "):
            if not self._connected_port and self._selected_port:
                self._connected_port = self._selected_port
                logger.info(f"Порт открыт: {self._connected_port}")
                self.connected.emit(self._connected_port)
        self.line_sent.emit(data)
    
    def _on_data_received(self, data: str):
        """Обработка полученных данных"""
        self.line_received.emit(data)
    
    def _on_ok_received(self):
        """Обработка получения ok"""
        self.ok_received.emit()
    
    def _on_error(self, error: str):
        """Обработка ошибки"""
        logger.error(f"SerialManager error: {error}")
        # Сбрасываем флаг подключения при ошибке
        if hasattr(self.worker, '_connecting'):
            self.worker._connecting = False
        self.error.emit(error)
    
    def _on_queue_continue(self):
        """Продолжить очередь после получения ok"""
        if not self.worker.is_running or self.worker.is_paused:
            return
        
        if self.worker.current_index < len(self.worker.queue):
            self.progress.emit(self.worker.current_index, len(self.worker.queue))
            self.worker._send_next_in_queue()
        else:
            # Очередь завершена
            self.queue_completed.emit()
    
    def cleanup(self):
        """Очистка ресурсов при закрытии"""
        if self._connected_port:
            self.disconnect()
        
        self.thread.quit()
        self.thread.wait()

