"""
Главное окно приложения
"""
import queue

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QDockWidget, QToolBar, QStatusBar, QFileDialog,
                              QMessageBox, QSplitter, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

from app.models.app_state import AppState, ConnectionStatus, RunStatus
from app.controllers.connection_controller import ConnectionController
from app.controllers.gcode_controller import GCodeController
from app.controllers.run_controller import RunController
from app.widgets.gcode_view import GCodeView
from app.widgets.trajectory_view import TrajectoryView
from app.widgets.console_view import ConsoleView
from app.widgets.port_panel import PortPanel
from app.widgets.jog_panel import JogPanel
from app.widgets.coordinates_panel import CoordinatesPanel
from app.ui.coordinates_viewmodel import CoordinatesViewModel
from app.ui.main_compact_view import MainCompactView
from app.ui.trajectory_dialog import TrajectoryDialog
from app.services.coordinates_provider import SerialCoordinatesProvider
from app.utils.settings import AppSettings
from app.utils.logger import get_logger
from app.services.position_tracker import PositionTracker

logger = get_logger()

# Опционально: клавиатура 4x4 на RPi GPIO (управление джогом вместо кнопок)
try:
    from app.keyboard_control import (
        is_available as keypad_available,
        KeypadScanner,
        create_jog_handler,
    )
except ImportError:
    keypad_available = lambda: False
    KeypadScanner = None  # type: ignore
    create_jog_handler = None  # type: ignore


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация
        self.settings = AppSettings()
        self.app_state = AppState()
        
        # Контроллеры (часть создадим после доков, чтобы иметь PortPanel)
        self.connection_controller = ConnectionController(self.app_state, self)
        self.gcode_controller = None
        self.run_controller = None
        
        # Виджеты
        self.gcode_view = None
        self.gcode_dock = None
        self.trajectory_view = None
        self.console_view = None
        self.port_panel = None
        self.jog_panel = None
        self.coordinates_panel = None
        self.control_dock = None
        self.coordinates_vm = None
        self.compact_view = None
        self._primary_central_widget = None
        self._compact_mode_enabled = False
        self._keypad_queue = None
        self._keypad_scanner = None
        self._keypad_timer = None
        self.position_tracker = None  # программный счётчик координат (по ok)

        self._init_ui()
        self._connect_signals()
        self._load_settings()
        self._initial_connect_done = False
        
        # Обновляем порты при старте
        self._on_refresh_ports()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Delta Robot - G-code Sender v0.1")
        self.setMinimumSize(1200, 800)
        
        # Центральная область - TrajectoryView
        self.trajectory_view = TrajectoryView()
        self._primary_central_widget = self.trajectory_view
        self.setCentralWidget(self.trajectory_view)
        
        # Создаем доки
        self._create_docks()
        
        # Создаем меню
        self._create_menus()
        
        # Создаем тулбар
        self._create_toolbar()
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        
        # Инициализируем контроллеры и программный счётчик координат
        self._init_controllers()
        self._init_position_tracker()
        self._init_compact_view()
        self._show_compact_mode()
        
        # Включаем компактный режим для консоли
        self.console_view.set_compact_mode(True, max_input_width=600)
        
        # Включаем вложенные доки и настраиваем разделение нижней области
        self.setDockNestingEnabled(True)
        self._setup_bottom_split()

        # Клавиатура 4x4 на RPi: те же команды джога, что и кнопки
        self._start_keypad_if_available()
    
    def _create_docks(self):
        """Создать доки"""
        
        # Док слева: G-code редактор (ширина ~35%)
        self.gcode_view = GCodeView()
        self.gcode_dock = QDockWidget("G-code", self)
        self.gcode_dock.setWidget(self.gcode_view)
        self.gcode_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.gcode_dock)
        
        # Док справа: Управление (сплит с PortPanel, CoordinatesPanel и JogPanel)
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(0)
        
        # Сплиттер для разделения панелей
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.port_panel = PortPanel()
        
        # Создаём CoordinatesViewModel и CoordinatesPanel
        serial_manager = self.connection_controller.get_manager()
        coordinates_provider = SerialCoordinatesProvider(serial_manager)
        self.coordinates_vm = CoordinatesViewModel(coordinates_provider, serial_manager, self)
        self.coordinates_panel = CoordinatesPanel(self.coordinates_vm)
        
        self.jog_panel = JogPanel()
        
        splitter.addWidget(self.port_panel)
        splitter.addWidget(self.coordinates_panel)
        splitter.addWidget(self.jog_panel)
        splitter.setStretchFactor(0, 1)  # PortPanel растягивается
        splitter.setStretchFactor(1, 1)  # CoordinatesPanel растягивается
        splitter.setStretchFactor(2, 2)  # JogPanel растягивается больше
        
        control_layout.addWidget(splitter)
        
        self.control_dock = QDockWidget("Управление", self)
        self.control_dock.setWidget(control_widget)
        self.control_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.control_dock)
        
        # Док снизу: Консоль (компактный режим)
        self.console_view = ConsoleView()
        self.console_dock = QDockWidget("Консоль", self)
        self.console_dock.setWidget(self.console_view)
        self.console_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.console_dock.setMinimumHeight(160)
        self.console_dock.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)
        
        # Устанавливаем пропорции
        self.resizeDocks([self.gcode_dock, self.control_dock], [350, 300], Qt.Orientation.Horizontal)
        self.resizeDocks([self.console_dock], [200], Qt.Orientation.Vertical)
    
    def _setup_bottom_split(self):
        """Создать пустой правый док и разделить нижнюю область пополам."""
        # Пустой правый док-разделитель
        self.bottom_spacer = QDockWidget("", self)
        self.bottom_spacer.setObjectName("BottomSpacerDock")
        self.bottom_spacer.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.bottom_spacer.setTitleBarWidget(QWidget(self.bottom_spacer))
        self.bottom_spacer.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.bottom_spacer.setWidget(QWidget())
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_spacer)
        
        # Делим нижнюю область горизонтально: консоль слева, спейсер справа
        if hasattr(self, 'console_dock') and self.console_dock is not None:
            self.splitDockWidget(self.console_dock, self.bottom_spacer, Qt.Orientation.Horizontal)
        
        # Устанавливаем стартовые пропорции после показа окна
        QTimer.singleShot(0, self._resize_bottom_area)
    
    def _resize_bottom_area(self):
        if getattr(self, 'console_dock', None) and getattr(self, 'bottom_spacer', None):
            self.resizeDocks([self.console_dock, self.bottom_spacer],
                             [int(self.width() * 0.5), int(self.width() * 0.5)],
                             Qt.Orientation.Horizontal)

    def _start_keypad_if_available(self):
        """Запуск сканирования клавиатуры 4x4 на RPi GPIO; команды как от кнопок джога."""
        if not keypad_available() or KeypadScanner is None or create_jog_handler is None:
            return
        try:
            self._keypad_queue = queue.Queue()

            def send_command(cmd: str) -> None:
                self.run_controller.send_immediate(cmd, wait_ok=False)

            jog_handler = create_jog_handler(
                send_command=send_command,
                get_step=lambda: self.app_state.jog_step,
                get_feed=lambda: self.app_state.jog_feedrate,
                set_step=self.app_state.set_jog_step,
                step_delta=0.5,
            )

            def on_key(key: str) -> None:
                self._keypad_queue.put(key)

            self._keypad_scanner = KeypadScanner(on_key=on_key)
            self._keypad_scanner.start()

            def process_keypad_queue() -> None:
                if self._keypad_queue is None:
                    return
                try:
                    while True:
                        key = self._keypad_queue.get_nowait()
                        if key == "*":
                            if self._compact_mode_enabled and self.compact_view is not None:
                                self.compact_view.toggle_console_visibility()
                        else:
                            jog_handler(key)
                except queue.Empty:
                    pass

            self._keypad_timer = QTimer(self)
            self._keypad_timer.timeout.connect(process_keypad_queue)
            self._keypad_timer.start(100)
            logger.info("Клавиатура 4x4 (GPIO) включена: 1–6 оси, 7/8 шаг")
        except Exception as e:
            logger.warning("Клавиатура 4x4 не запущена: %s", e)

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._resize_bottom_area)
    
    def _create_menus(self):
        """Создать меню"""
        
        # Файл
        file_menu = self.menuBar().addMenu("Файл")
        
        open_action = QAction("Открыть G-code…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Подключение
        connection_menu = self.menuBar().addMenu("Подключение")
        
        refresh_ports_action = QAction("Обновить порты", self)
        refresh_ports_action.setShortcut("F5")
        refresh_ports_action.triggered.connect(self._on_refresh_ports)
        connection_menu.addAction(refresh_ports_action)
        
        connection_menu.addSeparator()
        
        self.connect_action = QAction("Подключить", self)
        self.connect_action.setShortcut("Ctrl+C")
        self.connect_action.triggered.connect(self._on_connect)
        connection_menu.addAction(self.connect_action)
        
        self.disconnect_action = QAction("Отключить", self)
        self.disconnect_action.setShortcut("Ctrl+D")
        self.disconnect_action.setEnabled(False)
        self.disconnect_action.triggered.connect(self._on_disconnect)
        connection_menu.addAction(self.disconnect_action)
        
        # Пуск
        run_menu = self.menuBar().addMenu("Пуск")
        
        self.start_action = QAction("Старт", self)
        self.start_action.setShortcut("F9")
        self.start_action.setEnabled(False)
        self.start_action.triggered.connect(self._on_start)
        run_menu.addAction(self.start_action)
        
        self.pause_action = QAction("Пауза/Продолжить", self)
        self.pause_action.setShortcut("F8")
        self.pause_action.setEnabled(False)
        self.pause_action.triggered.connect(self._on_pause)
        run_menu.addAction(self.pause_action)
        
        run_menu.addSeparator()
        
        self.stop_action = QAction("Стоп", self)
        self.stop_action.setShortcut("F10")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self._on_stop)
        run_menu.addAction(self.stop_action)
        
        run_menu.addSeparator()
        
        self.send_line_by_line_action = QAction("Отправить (построчно)", self)
        self.send_line_by_line_action.setShortcut("F11")
        self.send_line_by_line_action.setEnabled(False)
        self.send_line_by_line_action.triggered.connect(self._on_send_line_by_line)
        run_menu.addAction(self.send_line_by_line_action)
        
        # Вид
        view_menu = self.menuBar().addMenu("Вид")
        
        trajectory_action = QAction("Траектория", self)
        trajectory_action.setShortcut("Ctrl+T")
        trajectory_action.triggered.connect(self._on_show_trajectory)
        view_menu.addAction(trajectory_action)
        
        view_menu.addSeparator()
        
        theme_action = QAction("Светлая тема", self)
        theme_action.setCheckable(True)
        theme_action.setChecked(True)
        theme_action.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(theme_action)
        
        reset_layout_action = QAction("Сбросить компоновку", self)
        reset_layout_action.triggered.connect(self._on_reset_layout)
        view_menu.addAction(reset_layout_action)
        
        view_menu.addSeparator()
        reset_coords_action = QAction("Обнулить координаты (после Homing)", self)
        reset_coords_action.triggered.connect(self._on_reset_coordinates)
        view_menu.addAction(reset_coords_action)
        
        window_menu = self.menuBar().addMenu("Окно")
        self.compact_mode_action = QAction("Компактный режим", self)
        self.compact_mode_action.setCheckable(True)
        self.compact_mode_action.triggered.connect(self._on_toggle_compact_mode)
        window_menu.addAction(self.compact_mode_action)
    
    def _create_toolbar(self):
        """Создать тулбар"""
        
        self.toolbar = QToolBar("Основная панель", self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Убеждаемся, что текст кнопок виден
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Добавляем основные действия
        open_action = QAction("Открыть", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        self.toolbar.addAction(open_action)
        
        trajectory_toolbar_action = QAction("Траектория", self)
        trajectory_toolbar_action.setShortcut("Ctrl+T")
        trajectory_toolbar_action.triggered.connect(self._on_show_trajectory)
        self.toolbar.addAction(trajectory_toolbar_action)
        
        self.toolbar.addSeparator()
        
        self.toolbar.connect_action = QAction("Подключить", self)
        self.toolbar.connect_action.triggered.connect(self._on_connect)
        self.toolbar.addAction(self.toolbar.connect_action)
        
        self.toolbar.disconnect_action = QAction("Отключить", self)
        self.toolbar.disconnect_action.setEnabled(False)
        self.toolbar.disconnect_action.triggered.connect(self._on_disconnect)
        self.toolbar.addAction(self.toolbar.disconnect_action)
        
        self.toolbar.addSeparator()
        
        self.toolbar.start_action = QAction("Старт", self)
        self.toolbar.start_action.setEnabled(False)
        self.toolbar.start_action.triggered.connect(self._on_start)
        self.toolbar.addAction(self.toolbar.start_action)
        
        self.toolbar.pause_action = QAction("Пауза", self)
        self.toolbar.pause_action.setEnabled(False)
        self.toolbar.pause_action.triggered.connect(self._on_pause)
        self.toolbar.addAction(self.toolbar.pause_action)
        
        self.toolbar.stop_action = QAction("Стоп", self)
        self.toolbar.stop_action.setEnabled(False)
        self.toolbar.stop_action.triggered.connect(self._on_stop)
        self.toolbar.addAction(self.toolbar.stop_action)
        
        self.toolbar.addSeparator()
        
        self.toolbar.send_line_by_line_action = QAction("Отправить (построчно)", self)
        self.toolbar.send_line_by_line_action.setEnabled(False)
        self.toolbar.send_line_by_line_action.triggered.connect(self._on_send_line_by_line)
        self.toolbar.addAction(self.toolbar.send_line_by_line_action)
    
    def _init_controllers(self):
        """Инициализировать контроллеры"""
        # Теперь, когда PortPanel и ConsoleView созданы, прикрепим их к контроллеру подключения
        self.connection_controller.attach_port_panel(self.port_panel, self.console_view)
        # Создаём остальные контроллеры, которые зависят от менеджера соединения
        self.gcode_controller = GCodeController(self.app_state, self)
        self.run_controller = RunController(
            self.app_state,
            self.connection_controller.get_manager(),
            self
        )

    def _init_position_tracker(self):
        """Программный счётчик координат: обновление только по ответу ok."""
        manager = self.connection_controller.get_manager()
        self.position_tracker = PositionTracker(self)
        manager.line_sent.connect(self.position_tracker.on_line_sent)
        manager.ok_received.connect(self.position_tracker.on_ok_received)
        self.position_tracker.position_updated.connect(self._on_tracker_position_updated)
        logger.info("PositionTracker: координаты по приращениям (обновление по ok)")

    def _on_tracker_position_updated(self, x: float, y: float, z: float):
        """Обновить отображение координат из программного счётчика."""
        if self.coordinates_vm is None:
            return
        self.coordinates_vm.machine_x = x
        self.coordinates_vm.machine_y = y
        self.coordinates_vm.machine_z = z

    def _init_compact_view(self):
        """Создать компактный вид, если он ещё не создан."""
        if self.compact_view is not None:
            return
        serial_manager = self.connection_controller.get_manager()
        self.compact_view = MainCompactView(
            app_state=self.app_state,
            coordinates_vm=self.coordinates_vm,
            run_controller=self.run_controller,
            gcode_controller=self.gcode_controller,
            connection_controller=self.connection_controller,
            serial_manager=serial_manager,
            parent=self,
        )
    
    def _set_legacy_docks_visible(self, visible: bool):
        """Показать или скрыть доки старого дизайна."""
        for dock in (self.gcode_dock, self.control_dock):
            if dock is not None:
                dock.setVisible(visible)
    
    def _show_compact_mode(self):
        """Переключить центральный виджет на компактный режим."""
        self._init_compact_view()
        if not self.compact_view:
            return
        if self._compact_mode_enabled:
            return
        previous_central = self.takeCentralWidget()
        if previous_central and previous_central is not self.compact_view:
            self._primary_central_widget = previous_central
            previous_central.hide()
        self.setCentralWidget(self.compact_view)
        self.compact_view.show()
        self._set_legacy_docks_visible(False)
        self._compact_mode_enabled = True
        if hasattr(self, "compact_mode_action"):
            self.compact_mode_action.setChecked(True)
    
    def _show_primary_view(self):
        """Вернуть исходный центральный вид."""
        if not self._primary_central_widget:
            return
        current_central = self.takeCentralWidget()
        if current_central and current_central is not self._primary_central_widget:
            self.compact_view = current_central
            current_central.hide()
        self.setCentralWidget(self._primary_central_widget)
        self._primary_central_widget.show()
        self._set_legacy_docks_visible(True)
        self._compact_mode_enabled = False
        if hasattr(self, "compact_mode_action"):
            self.compact_mode_action.setChecked(False)
    
    def _connect_signals(self):
        """Подключить все сигналы между контроллерами и виджетами"""
        logger.info("Подключение сигналов...")
        
        # === PortPanel -> ConnectionController ===
        self.port_panel.connect_clicked.connect(self._on_connect)
        self.port_panel.disconnect_clicked.connect(self._on_disconnect)
        self.port_panel.refresh_clicked.connect(self._on_refresh_ports)
        
        # === JogPanel -> RunController ===
        self.jog_panel.jog_command.connect(self._on_jog_command)
        
        # === ConsoleView -> RunController ===
        self.console_view.command_to_send.connect(self._on_console_command)
        
        # === ConnectionController -> PortPanel ===
        # Подписываемся на обновление портов для авто-выбора и первичного подключения
        self.connection_controller.ports_changed.connect(self._on_ports_changed)
        self.connection_controller.connected.connect(self._on_connected)
        self.connection_controller.disconnected.connect(self._on_disconnected)
        self.connection_controller.error_occurred.connect(self._on_connection_error)
        
        # === GCodeController -> Views ===
        self.gcode_controller.gcode_loaded.connect(self._on_gcode_loaded)
        self.gcode_controller.trajectory_updated.connect(self._on_trajectory_updated)
        
        # === SerialManager -> ConsoleView ===
        manager = self.connection_controller.get_manager()
        manager.line_sent.connect(self.console_view.add_sent_command)
        manager.line_received.connect(self._on_line_received)
        manager.error.connect(self.console_view.add_error)
        
        # === RunController -> Views ===
        self.run_controller.started.connect(self._on_run_started)
        self.run_controller.paused.connect(self._on_run_paused)
        self.run_controller.resumed.connect(self._on_run_resumed)
        self.run_controller.stopped.connect(self._on_run_stopped)
        self.run_controller.completed.connect(self._on_run_completed)
        self.run_controller.progress.connect(self._on_run_progress)
        self.run_controller.line_highlighted.connect(self._on_line_highlighted)
        
        # === AppState -> Views ===
        self.app_state.connection_status_changed.connect(self._on_connection_status_changed)
        self.app_state.run_status_changed.connect(self._on_run_status_changed)
        self.app_state.current_line_changed.connect(self._on_current_line_changed)
        
        # === CoordinatesViewModel -> Auto-refresh ===
        # Автообновление координат при подключении/отключении
        self.connection_controller.connected.connect(self._on_coordinates_connected)
        self.connection_controller.disconnected.connect(self._on_coordinates_disconnected)
        
        logger.info("Сигналы подключены")
    
    # === Обработчики действий от виджетов ===
    
    def _on_refresh_ports(self):
        """Обновить список портов"""
        logger.info("Обновление портов...")
        self.console_view.add_info("Обновление списка портов...")
        self.connection_controller.refresh_ports()
    
    def _on_connect(self):
        """Подключиться к выбранному порту (упрощённая модель)"""
        port = self.port_panel.get_selected_port()
        if not port:
            QMessageBox.warning(self, "Внимание", "Выберите COM-порт")
            return
        
        logger.info(f"Подключение (упрощённо) к {port}...")
        self.console_view.add_info(f"Подключено (упрощённо): {port}")
        self.settings.save_last_port(port)
        # Не вызываем реальное подключение - это делается лениво при первой отправке
    
    def _on_disconnect(self):
        """Отключиться от порта (упрощённая модель)"""
        logger.info("Отключение...")
        self.console_view.add_info("Отключено")
        # Вызываем отключение через контроллер
        self.connection_controller._on_disconnect_clicked()
    
    def _on_open_file(self):
        """Открыть файл G-code и загрузить его"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть G-code файл",
            "",
            "G-code файлы (*.gcode *.nc);;Все файлы (*.*)"
        )
        
        if filepath:
            logger.info(f"Загрузка файла: {filepath}")
            self.console_view.add_info(f"Загрузка файла: {filepath}")
            
        if self.gcode_controller.load_gcode_from_file(filepath):
            self.app_state.set_gcode_file_path(filepath)
            self.start_action.setEnabled(True)
            self.send_line_by_line_action.setEnabled(True)
            self.toolbar.start_action.setEnabled(True)
            self.toolbar.send_line_by_line_action.setEnabled(True)
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить G-code файл")
    
    def _on_start(self):
        """Начать выполнение G-code"""
        logger.info("Старт выполнения...")
        self.console_view.add_info("Начато выполнение G-code")
        self.run_controller.start()
    
    def _on_pause(self):
        """Пауза/продолжить выполнение"""
        if self.app_state.run_status == RunStatus.RUNNING:
            logger.info("Пауза...")
            self.console_view.add_info("Пауза")
            self.run_controller.pause()
        elif self.app_state.run_status == RunStatus.PAUSED:
            logger.info("Продолжить...")
            self.console_view.add_info("Продолжить")
            self.run_controller.resume()
    
    def _on_stop(self):
        """Остановить выполнение"""
        logger.info("Стоп выполнения...")
        self.console_view.add_info("Остановлено выполнение")
        self.run_controller.stop()
    
    def _on_send_line_by_line(self):
        """Отправить G-code построчно из редактора"""
        if not self.port_panel.get_selected_port():
            QMessageBox.warning(self, "Внимание", "Сначала выберите COM-порт")
            return
        
        if not self.gcode_view.get_text().strip():
            QMessageBox.warning(self, "Внимание", "G-code редактор пуст")
            return
        
        logger.info("Начало построчной отправки из редактора...")
        self.console_view.add_info("Начало построчной отправки G-code из редактора")
        self.run_controller.start_from_editor(self.gcode_view)
    
    def _on_jog_command(self, command: str):
        """Обработка jog команды"""
        logger.info(f"Jog команда: {command}")
        self.console_view.add_sent_command(command)
        self.run_controller.send_immediate(command, wait_ok=True)
    
    def _on_console_command(self, command: str):
        """Отправить команду из консоли"""
        if not self.port_panel.get_selected_port():
            self.console_view.add_error("Выберите COM-порт для отправки команд")
            return
        
        logger.info(f"Консольная команда: {command}")
        self.console_view.add_sent_command(command)
        self.run_controller.send_immediate(command, wait_ok=True)
    
    # === Обработчики сигналов от контроллеров ===
    
    def _on_line_received(self, line: str):
        """Обработка полученной строки"""
        self.console_view.add_received_response(line)
    
    def _on_ports_changed(self, ports: list):
        """Обновление списка портов"""
        port_strings = [str(p) for p in ports]
        self.port_panel.set_ports(port_strings)
        
        # Автовыбор последнего порта
        last_port = self.settings.load_last_port()
        if last_port:
            for i in range(self.port_panel.port_combo.count()):
                if last_port in self.port_panel.port_combo.itemText(i):
                    self.port_panel.port_combo.setCurrentIndex(i)
                    # Первичное подключение один раз при старте
                    if not self._initial_connect_done:
                        try:
                            self.connection_controller.get_manager().connect(last_port)
                            self._initial_connect_done = True
                        except Exception:
                            pass
                    break
        
        self.console_view.add_info(f"Найдено портов: {len(ports)}")
    
    def _on_connected(self, port_name: str):
        """Подключено"""
        self.port_panel.set_connection_state(True)
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(True)
        self.toolbar.connect_action.setEnabled(False)
        self.toolbar.disconnect_action.setEnabled(True)
        self.jog_panel.set_enabled(True)
        self.status_bar.showMessage(f"Подключено: {port_name}")
        self.console_view.add_info(f"Подключено к {port_name}")
    
    def _on_disconnected(self):
        """Отключено"""
        self.port_panel.set_connection_state(False)
        self.connect_action.setEnabled(True)
        self.disconnect_action.setEnabled(False)
        self.toolbar.connect_action.setEnabled(True)
        self.toolbar.disconnect_action.setEnabled(False)
        self.jog_panel.set_enabled(False)
        self.status_bar.showMessage("Отключено")
        self.console_view.add_info("Отключено")
    
    def _on_connection_error(self, error: str):
        """Ошибка подключения"""
        self.console_view.add_error(error)
        QMessageBox.warning(self, "Ошибка", f"Ошибка подключения:\n{error}")
    
    def _on_connection_status_changed(self, status: ConnectionStatus):
        """Изменение статуса подключения"""
        self.status_bar.showMessage(f"Статус: {status.value}")
    
    def _on_gcode_loaded(self, lines: list):
        """G-code загружен"""
        self.gcode_view.set_text('\n'.join(lines))
        self.console_view.add_info(f"G-code загружен: {len(lines)} строк")
    
    def _on_trajectory_updated(self, points: list):
        """Обновление траектории"""
        self.app_state.set_trajectory_points(points)
        self.trajectory_view.set_path(points)
        self.console_view.add_info(f"Траектория построена: {len(points)} точек")
    
    def _on_run_started(self):
        """Начало выполнения"""
        self.start_action.setEnabled(False)
        self.pause_action.setEnabled(True)
        self.stop_action.setEnabled(True)
        self.send_line_by_line_action.setEnabled(False)
        self.toolbar.start_action.setEnabled(False)
        self.toolbar.pause_action.setEnabled(True)
        self.toolbar.stop_action.setEnabled(True)
        self.toolbar.send_line_by_line_action.setEnabled(False)
        self.pause_action.setText("Пауза")
        self.status_bar.showMessage("Выполнение...")
    
    def _on_run_paused(self):
        """Пауза выполнения"""
        self.pause_action.setText("Продолжить")
        self.status_bar.showMessage("Пауза")
    
    def _on_run_resumed(self):
        """Продолжение выполнения"""
        self.pause_action.setText("Пауза")
        self.status_bar.showMessage("Выполнение...")
    
    def _on_run_stopped(self):
        """Остановка выполнения"""
        self.start_action.setEnabled(True)
        self.pause_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        self.send_line_by_line_action.setEnabled(True)
        self.toolbar.start_action.setEnabled(True)
        self.toolbar.pause_action.setEnabled(False)
        self.toolbar.stop_action.setEnabled(False)
        self.toolbar.send_line_by_line_action.setEnabled(True)
        self.pause_action.setText("Пауза")
        self.status_bar.showMessage("Остановлено")
    
    def _on_run_completed(self):
        """Завершение выполнения"""
        self.start_action.setEnabled(True)
        self.pause_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        self.send_line_by_line_action.setEnabled(True)
        self.toolbar.start_action.setEnabled(True)
        self.toolbar.pause_action.setEnabled(False)
        self.toolbar.stop_action.setEnabled(False)
        self.toolbar.send_line_by_line_action.setEnabled(True)
        self.status_bar.showMessage("Завершено")
        self.console_view.add_info("G-code выполнен полностью")
        QMessageBox.information(self, "Готово", "Выполнение G-code завершено")
    
    def _on_run_progress(self, current: int, total: int):
        """Прогресс выполнения"""
        percent = (current / total * 100) if total > 0 else 0
        self.status_bar.showMessage(f"Выполнение: {current}/{total} ({percent:.1f}%)")
    
    def _on_run_status_changed(self, status: RunStatus):
        """Изменение статуса выполнения"""
        self.start_action.setEnabled(status == RunStatus.IDLE)
        self.pause_action.setEnabled(status in [RunStatus.RUNNING, RunStatus.PAUSED])
        self.stop_action.setEnabled(status in [RunStatus.RUNNING, RunStatus.PAUSED])
        self.send_line_by_line_action.setEnabled(status == RunStatus.IDLE)
    
    def _on_current_line_changed(self, line_index: int):
        """Изменение текущей строки"""
        # TODO: подсветка строки в GCodeView
        pass
    
    def _on_coordinates_connected(self, port_name: str):
        """При подключении: координаты ведёт программный счётчик (PositionTracker), M114 не используем."""
        if self.coordinates_vm and self.position_tracker:
            self.coordinates_vm.set_auto_refresh_enabled(False)
            logger.info("Координаты по программному счётчику (обновление по ok)")
    
    def _on_coordinates_disconnected(self):
        """Обработка отключения для остановки автообновления координат"""
        if self.coordinates_vm:
            self.coordinates_vm.set_auto_refresh_enabled(False)
            logger.info("Автообновление координат выключено")
    
    def _on_line_highlighted(self, line_index: int):
        """Подсветка строки в G-code редакторе"""
        self.gcode_view.highlight_line(line_index)
    
    def _on_show_trajectory(self):
        """Открыть диалог с проекциями траектории"""
        # Получаем точки траектории из AppState
        trajectory_points_2d = self.app_state.trajectory_points
        
        if not trajectory_points_2d:
            QMessageBox.information(self, "Информация", "Траектория не загружена. Загрузите G-code файл.")
            return
        
        # Преобразуем 2D точки (x, y) в 3D (x, y, z=0)
        trajectory_points_3d = []
        for point in trajectory_points_2d:
            if len(point) >= 2:
                x, y = point[0], point[1]
                z = point[2] if len(point) >= 3 else 0.0
                trajectory_points_3d.append((x, y, z))
        
        # Создаем и показываем диалог
        dialog = TrajectoryDialog(trajectory_points_3d, self)
        dialog.exec()
    
    def _on_toggle_theme(self, checked: bool):
        """Переключить тему"""
        logger.info(f"Переключение темы: {'Светлая' if checked else 'Тёмная'}")
        self.console_view.add_info(f"Тема: {'Светлая' if checked else 'Тёмная'}")
        # TODO: реализовать переключение тем
    
    def _on_reset_layout(self):
        """Сбросить компоновку"""
        logger.info("Сброс компоновки окон")
        self.console_view.add_info("Компоновка окна сброшена")
        # TODO: восстановить дефолтную компоновку доков

    def _on_reset_coordinates(self):
        """Обнулить программные координаты (вызывать после процедуры homing)."""
        if self.position_tracker is None:
            return
        self.position_tracker.reset_coordinates()
        self.console_view.add_info("Координаты обнулены (X=0 Y=0 Z=0) после Homing")
    
    def _on_toggle_compact_mode(self, checked: bool):
        """Переключить компактный режим."""
        if checked:
            self._show_compact_mode()
        else:
            self._show_primary_view()
    
    def _load_settings(self):
        """Загрузить настройки"""
        logger.info("Загрузка настроек...")
        
        # Геометрия окна
        geometry = self.settings.load_geometry()
        if geometry:
            self.restoreGeometry(geometry)
            logger.debug("Геометрия восстановлена")
        
        # Состояние окна (доки)
        state = self.settings.load_state()
        if state:
            self.restoreState(state)
            logger.debug("Состояние доков восстановлено")
        
        # Jog параметры
        jog_step = self.settings.load_jog_step()
        self.app_state.set_jog_step(jog_step)
        self.jog_panel.set_step(jog_step)
        
        jog_feedrate = self.settings.load_jog_feedrate()
        self.app_state.set_jog_feedrate(jog_feedrate)
        
        logger.info("Настройки загружены")
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        logger.info("Закрытие приложения...")
        
        # Останавливаем выполнение если запущено
        if self.app_state.run_status != RunStatus.IDLE:
            self.run_controller.stop()
        
        # Отключаемся если подключено
        if self.connection_controller.is_connected:
            self.connection_controller.disconnect_from_port()
        
        # Сохраняем настройки
        geometry = self.saveGeometry()
        state = self.saveState()
        
        self.settings.save_geometry(geometry)
        self.settings.save_state(state)
        
        # Сохраняем jog параметры
        self.settings.save_jog_step(self.app_state.jog_step)
        self.settings.save_jog_feedrate(self.app_state.jog_feedrate)
        
        self.settings.sync()
        
        logger.info("Окно закрыто, настройки сохранены")
        event.accept()

