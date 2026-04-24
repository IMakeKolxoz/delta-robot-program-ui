"""
Контроллер выполнения G-code
"""
from PyQt6.QtCore import QObject, pyqtSignal
from app.models.app_state import AppState, RunStatus
from app.services.serial_manager import SerialManager
from app.services.gcode_parser import GCodeParser
from app.utils.logger import get_logger

logger = get_logger()


class RunController(QObject):
    """
    Контроллер управления выполнением G-code
    
    Функции:
    - Старт/пауза/стоп очереди
    - Пошаговая отправка
    - Прогресс
    - Подсветка текущей строки в GCodeView
    - Обновление курсора в TrajectoryView
    """
    
    # Сигналы для UI
    started = pyqtSignal()
    paused = pyqtSignal()
    resumed = pyqtSignal()
    stopped = pyqtSignal()
    completed = pyqtSignal()
    progress = pyqtSignal(int, int)  # Текущая строка, всего
    line_highlighted = pyqtSignal(int)  # Номер строки для подсветки
    cursor_updated = pyqtSignal(float, float)  # X, Y для курсора
    
    def __init__(self, app_state: AppState, serial_manager: SerialManager, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.manager = serial_manager
        self.parser = GCodeParser()
        
        # Подключаем сигналы
        self.manager.line_sent.connect(self._on_line_sent)
        self.manager.line_received.connect(self._on_line_received)
        self.manager.ok_received.connect(self._on_ok_received)
        self.manager.error.connect(self._on_error)
        self.manager.progress.connect(self._on_progress)
        self.manager.queue_completed.connect(self._on_queue_completed)
        
        self.current_line_index = 0
        logger.info("RunController инициализирован")
    
    def start(self):
        """
        Начать выполнение G-code
        
        Проверяет подключение и загруженность G-code,
        отправляет команды в очередь SerialManager
        """
        if self.app_state.run_status not in [RunStatus.IDLE, RunStatus.COMPLETED]:
            logger.warning("Выполнение уже запущено")
            return
        
        if not self.manager.is_connected:
            logger.error("Не подключено")
            return
        
        if not self.app_state.gcode_lines:
            logger.error("G-code не загружен")
            return
        
        # Получаем очищенные строки для отправки
        clean_lines = self.app_state.gcode_lines
        
        # Добавляем в очередь SerialManager
        self.manager.enqueue_batch(clean_lines)
        
        # Сбрасываем прогресс
        self.current_line_index = 0
        
        # Запускаем очередь
        self.manager.start_queue()
        
        # Обновляем статус
        self.app_state.set_run_status(RunStatus.RUNNING)
        self.started.emit()
        logger.info(f"Старт выполнения: {len(clean_lines)} команд")
    
    def pause(self):
        """Приостановить выполнение"""
        if self.app_state.run_status == RunStatus.RUNNING:
            self.manager.pause()
            self.app_state.set_run_status(RunStatus.PAUSED)
            self.paused.emit()
            logger.info("Пауза")
    
    def resume(self):
        """Возобновить выполнение"""
        if self.app_state.run_status == RunStatus.PAUSED:
            self.manager.resume()
            self.app_state.set_run_status(RunStatus.RUNNING)
            self.resumed.emit()
            logger.info("Продолжить")
    
    def stop(self):
        """Остановить выполнение"""
        self.manager.stop()
        self.app_state.reset_run_state()
        self.current_line_index = 0
        self.stopped.emit()
        logger.info("Стоп")
    
    def send_immediate(self, line: str, wait_ok: bool = True):
        """
        Отправить команду немедленно (вне очереди)
        
        Args:
            line: Строка G-code
            wait_ok: Ждать ответ ok
        """
        # Проверяем, выбран ли порт
        if not self.app_state.active_port:
            logger.error("Порт не выбран")
            return
        
        # Проверяем подключение через ленивое открытие
        if not self.manager.ensure_open():
            logger.error("Не удалось открыть порт")
            return
        
        logger.info(f"Немедленная отправка: {line}")
        self.manager.send_immediate(line, wait_ok)
    
    def start_from_editor(self, gcode_view):
        """
        Начать выполнение G-code из редактора
        
        Args:
            gcode_view: GCodeView виджет с текстом
        """
        if self.app_state.run_status not in [RunStatus.IDLE, RunStatus.COMPLETED]:
            logger.warning("Выполнение уже запущено")
            return
        
        # Проверяем, выбран ли порт
        if not self.app_state.active_port:
            logger.error("Порт не выбран")
            return
        
        # Проверяем подключение через ленивое открытие
        if not self.manager.ensure_open():
            logger.error("Не удалось открыть порт")
            return
        
        # Получаем строки из редактора
        raw_lines = gcode_view.get_lines()
        if not raw_lines:
            logger.error("G-code редактор пуст")
            return
        
        # Очищаем строки через парсер
        clean_lines = []
        for line in raw_lines:
            cleaned = self.parser.clean_line(line)
            if cleaned:  # Пропускаем пустые строки
                clean_lines.append(cleaned)
        
        if not clean_lines:
            logger.error("Нет команд для отправки после очистки")
            return
        
        # Очищаем очередь и добавляем новые команды
        self.manager.stop()  # Очищает очередь
        self.manager.enqueue_batch(clean_lines)
        
        # Сбрасываем прогресс
        self.current_line_index = 0
        
        # Запускаем очередь
        self.manager.start_queue()
        
        # Обновляем статус
        self.app_state.set_run_status(RunStatus.RUNNING)
        self.started.emit()
        logger.info(f"Старт построчной отправки из редактора: {len(clean_lines)} команд")
    
    def _on_line_sent(self, line: str):
        """Обработка отправки строки"""
        logger.info(f"→ {line}")
    
    def _on_line_received(self, line: str):
        """Обработка получения строки"""
        logger.info(f"← {line}")
    
    def _on_ok_received(self):
        """Обработка получения ok"""
        # Обновляем прогресс
        if self.current_line_index < len(self.app_state.gcode_lines):
            self.current_line_index += 1
            self.app_state.set_current_line(self.current_line_index)
            
            # Сигнал для подсветки строки
            self.line_highlighted.emit(self.current_line_index - 1)
            
            # TODO: обновить курсор в TrajectoryView (нужны координаты из парсера)
    
    def _on_progress(self, current: int, total: int):
        """Обработка прогресса"""
        self.progress.emit(current, total)
    
    def _on_queue_completed(self):
        """Обработка завершения очереди"""
        logger.info("Выполнение завершено")
        self.app_state.set_run_status(RunStatus.COMPLETED)
        self.completed.emit()
    
    def _on_error(self, error: str):
        """Обработка ошибки"""
        logger.error(f"Ошибка выполнения: {error}")
        self.app_state.set_run_status(RunStatus.ERROR)
        self.stop()

