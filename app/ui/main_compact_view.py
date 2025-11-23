"""
Компактный интерфейс главного экрана (800×480) для режима панели управления.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QSplitter,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QFileDialog,
    QMessageBox,
)

from app.models.app_state import AppState, RunStatus
from app.ui.coordinates_viewmodel import CoordinatesViewModel
from app.controllers.run_controller import RunController
from app.controllers.gcode_controller import GCodeController
from app.controllers.connection_controller import ConnectionController
from app.services.serial_manager import SerialManager


class MainCompactView(QWidget):
    """
    Компактный виджет управления размером 800×480 px.

    Структура:
    - Левая колонка: координаты + блок G-кода.
    - Правая колонка: COM-порт, jog-панель, параметры движения, консоль.
    """

    start_cycle_requested = pyqtSignal()
    send_line_by_line_requested = pyqtSignal()
    stop_cycle_requested = pyqtSignal()
    load_code_requested = pyqtSignal()
    goto_line_requested = pyqtSignal(int)
    connect_requested = pyqtSignal(str)
    jog_command_requested = pyqtSignal(str, float)
    jog_params_changed = pyqtSignal(dict)
    console_command_submitted = pyqtSignal(str)

    def __init__(
        self,
        app_state: Optional[AppState] = None,
        coordinates_vm: Optional[CoordinatesViewModel] = None,
        run_controller: Optional[RunController] = None,
        gcode_controller: Optional[GCodeController] = None,
        connection_controller: Optional[ConnectionController] = None,
        serial_manager: Optional[SerialManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("MainCompactView")
        self.setFixedSize(800, 480)

        self.app_state = app_state
        self.coordinates_vm: Optional[CoordinatesViewModel] = None
        self.run_controller = run_controller
        self.gcode_controller = gcode_controller
        self.connection_controller = connection_controller
        self.serial_manager: Optional[SerialManager] = serial_manager or (
            connection_controller.get_manager() if connection_controller else None
        )

        self._machine_values: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._work_values: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._to_go_values: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._ports_cache: List[str] = []
        self._coordinate_handlers: Dict[str, object] = {}

        self._ensure_jog_params_container()
        self._build_layout()
        self._connect_internal_signals()
        self._connect_app_state_signals()
        self._connect_gcode_controller_signals()
        self._connect_connection_signals()
        self._connect_serial_signals()

        if coordinates_vm:
            self.bind_coordinates(coordinates_vm)

        self._sync_initial_state()

    # --------------------------------------------------------------------- #
    # UI construction
    # --------------------------------------------------------------------- #
    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.columns_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.columns_splitter.setChildrenCollapsible(False)

        left_column = self._build_left_column()
        right_column = self._build_right_column()

        self.columns_splitter.addWidget(left_column)
        self.columns_splitter.addWidget(right_column)
        self.columns_splitter.setStretchFactor(0, 1)
        self.columns_splitter.setStretchFactor(1, 2)
        self.columns_splitter.setSizes([320, 480])

        layout.addWidget(self.columns_splitter)

    def _build_left_column(self) -> QWidget:
        container = QWidget()
        column_layout = QVBoxLayout(container)
        column_layout.setContentsMargins(4, 4, 4, 4)
        column_layout.setSpacing(4)

        self.left_splitter = QSplitter(Qt.Orientation.Vertical, container)
        self.left_splitter.setChildrenCollapsible(False)

        self.coordinates_group = self._build_coordinates_group()
        self.gcode_group = self._build_gcode_group()

        self.left_splitter.addWidget(self.coordinates_group)
        self.left_splitter.addWidget(self.gcode_group)
        self.left_splitter.setStretchFactor(0, 0)
        self.left_splitter.setStretchFactor(1, 1)

        column_layout.addWidget(self.left_splitter)
        return container

    def _build_right_column(self) -> QWidget:
        container = QWidget()
        column_layout = QVBoxLayout(container)
        column_layout.setContentsMargins(4, 4, 4, 4)
        column_layout.setSpacing(4)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical, container)
        self.right_splitter.setChildrenCollapsible(False)

        self.com_group = self._build_com_group()
        self.jog_group = self._build_jog_group()
        self.motion_group = self._build_motion_params_group()
        self.console_group = self._build_console_group()

        self.right_splitter.addWidget(self.com_group)
        self.right_splitter.addWidget(self.jog_group)
        self.right_splitter.addWidget(self.motion_group)
        self.right_splitter.addWidget(self.console_group)

        self.right_splitter.setStretchFactor(0, 0)
        self.right_splitter.setStretchFactor(1, 0)
        self.right_splitter.setStretchFactor(2, 0)
        self.right_splitter.setStretchFactor(3, 1)

        column_layout.addWidget(self.right_splitter)
        return container

    def _build_coordinates_group(self) -> QGroupBox:
        group = QGroupBox("Координаты")
        layout = QFormLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        self.machine_field = self._create_coord_field("Machine")
        self.absolute_field = self._create_coord_field("Absolute")
        self.to_go_field = self._create_coord_field("ToGo")

        layout.addRow(QLabel("Машинные"), self.machine_field)
        layout.addRow(QLabel("Абсолютные"), self.absolute_field)
        layout.addRow(QLabel("To Go"), self.to_go_field)

        group.setLayout(layout)
        return group

    def _build_gcode_group(self) -> QGroupBox:
        group = QGroupBox("G-код")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Сетка кнопок 2x2
        button_grid = QGridLayout()
        button_grid.setSpacing(6)

        self.start_cycle_btn = QPushButton("Старт\nцикла")
        self.start_cycle_btn.setObjectName("StartCycleButton")
        self.line_by_line_btn = QPushButton("Построчная\nотправка")
        self.line_by_line_btn.setObjectName("LineByLineButton")
        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setObjectName("StopButton")
        self.load_code_btn = QPushButton("Загрузить\nкод")
        self.load_code_btn.setObjectName("LoadCodeButton")

        # Располагаем кнопки в сетке 2x2
        button_grid.addWidget(self.start_cycle_btn, 0, 0)  # Первая строка, первый столбец
        button_grid.addWidget(self.line_by_line_btn, 0, 1)  # Первая строка, второй столбец
        button_grid.addWidget(self.stop_btn, 1, 0)  # Вторая строка, первый столбец
        button_grid.addWidget(self.load_code_btn, 1, 1)  # Вторая строка, второй столбец

        # Элементы "Перейти к N" в отдельной строке
        goto_row = QHBoxLayout()
        goto_row.setSpacing(4)
        self.goto_label = QLabel("Перейти к N")
        self.goto_line_input = QLineEdit()
        self.goto_line_input.setPlaceholderText("N")
        self.goto_line_input.setMaximumWidth(60)
        self.goto_btn = QPushButton("OK")
        
        goto_row.addWidget(self.goto_label)
        goto_row.addWidget(self.goto_line_input)
        goto_row.addWidget(self.goto_btn)
        goto_row.addStretch(1)

        self.gcode_editor = QPlainTextEdit()
        self.gcode_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        layout.addLayout(button_grid)
        layout.addLayout(goto_row)
        layout.addWidget(self.gcode_editor)
        group.setLayout(layout)
        return group

    def _build_com_group(self) -> QGroupBox:
        group = QGroupBox("COM-порт")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(4)

        self.port_combo = QComboBox()
        self.refresh_ports_btn = QPushButton("Обновить")
        self.connect_btn = QPushButton("Подключиться")

        row.addWidget(self.port_combo, 1)
        row.addWidget(self.refresh_ports_btn)
        row.addWidget(self.connect_btn)

        layout.addLayout(row)
        group.setLayout(layout)
        return group

    def _build_jog_group(self) -> QGroupBox:
        group = QGroupBox("Jog Panel")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        buttons = {
            (0, 1): ("Y+", "Y", 1.0),
            (2, 1): ("Y-", "Y", -1.0),
            (1, 0): ("X-", "X", -1.0),
            (1, 2): ("X+", "X", 1.0),
            (0, 3): ("Z+", "Z", 1.0),
            (2, 3): ("Z-", "Z", -1.0),
        }

        self.jog_buttons: Dict[str, QPushButton] = {}
        for (row, col), (label, axis, direction) in buttons.items():
            btn = QPushButton(label)
            btn.setProperty("axis", axis)
            btn.setProperty("direction", direction)
            btn.setProperty("class", "compact-jog-button")
            btn.clicked.connect(self._on_jog_button_clicked)
            grid.addWidget(btn, row, col)
            self.jog_buttons[label] = btn

        group.setLayout(grid)
        return group

    def _build_motion_params_group(self) -> QGroupBox:
        group = QGroupBox("Параметры движения")
        layout = QFormLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.feed_field = self._create_numeric_field()
        self.spindle_field = self._create_numeric_field()
        self.step_field = self._create_numeric_field()
        self.jog_speed_field = self._create_numeric_field()

        layout.addRow(QLabel("Подача (F)"), self.feed_field)
        layout.addRow(QLabel("Шпиндель (S)"), self.spindle_field)
        layout.addRow(QLabel("Шаг джога"), self.step_field)
        layout.addRow(QLabel("Скорость джога"), self.jog_speed_field)

        group.setLayout(layout)
        return group

    def _build_console_group(self) -> QGroupBox:
        group = QGroupBox("Консоль")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.console_history = QPlainTextEdit()
        self.console_history.setReadOnly(True)
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText("Введите команду…")
        self.console_send_btn = QPushButton("Отправить")

        input_row = QHBoxLayout()
        input_row.setSpacing(4)
        input_row.addWidget(self.console_input, 1)
        input_row.addWidget(self.console_send_btn)

        layout.addWidget(self.console_history, 1)
        layout.addLayout(input_row)
        group.setLayout(layout)
        return group

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _create_coord_field(self, object_name: str) -> QLineEdit:
        field = QLineEdit("0.000 / 0.000 / 0.000")
        field.setObjectName(f"{object_name}Field")
        field.setReadOnly(True)
        return field

    def _create_numeric_field(self) -> QLineEdit:
        field = QLineEdit()
        field.setAlignment(Qt.AlignmentFlag.AlignRight)
        return field

    def _ensure_jog_params_container(self) -> None:
        if self.app_state is None:
            return
        if not hasattr(self.app_state, "jog_params"):
            self.app_state.jog_params = {
                "feed": getattr(self.app_state, "jog_feedrate", 1000.0),
                "spindle": 0.0,
                "step": getattr(self.app_state, "jog_step", 1.0),
                "speed": getattr(self.app_state, "jog_feedrate", 1000.0),
            }

    def _connect_internal_signals(self) -> None:
        self.start_cycle_btn.clicked.connect(self._on_start_cycle_clicked)
        self.line_by_line_btn.clicked.connect(self._on_line_by_line_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.load_code_btn.clicked.connect(self._on_load_code_clicked)
        self.goto_btn.clicked.connect(self._on_goto_line_clicked)
        self.goto_line_input.returnPressed.connect(self._on_goto_line_clicked)

        self.refresh_ports_btn.clicked.connect(self._on_refresh_ports_clicked)
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.feed_field.editingFinished.connect(self._on_motion_params_changed)
        self.spindle_field.editingFinished.connect(self._on_motion_params_changed)
        self.step_field.editingFinished.connect(self._on_motion_params_changed)
        self.jog_speed_field.editingFinished.connect(self._on_motion_params_changed)

        self.console_send_btn.clicked.connect(self._on_console_send)
        self.console_input.returnPressed.connect(self._on_console_send)

    def bind_coordinates(self, view_model: CoordinatesViewModel) -> None:
        """Подключить UI к экземпляру CoordinatesViewModel."""
        if self.coordinates_vm is view_model:
            return

        if self.coordinates_vm:
            self._disconnect_coordinates_vm()

        self.coordinates_vm = view_model
        if not self.coordinates_vm:
            return

        self._coordinate_handlers["machine_x"] = lambda value: self._update_machine_value(0, value)
        self._coordinate_handlers["machine_y"] = lambda value: self._update_machine_value(1, value)
        self._coordinate_handlers["machine_z"] = lambda value: self._update_machine_value(2, value)
        self._coordinate_handlers["work_x"] = lambda value: self._update_work_value(0, value)
        self._coordinate_handlers["work_y"] = lambda value: self._update_work_value(1, value)
        self._coordinate_handlers["work_z"] = lambda value: self._update_work_value(2, value)

        self.coordinates_vm.machine_x_changed.connect(self._coordinate_handlers["machine_x"])
        self.coordinates_vm.machine_y_changed.connect(self._coordinate_handlers["machine_y"])
        self.coordinates_vm.machine_z_changed.connect(self._coordinate_handlers["machine_z"])
        self.coordinates_vm.work_x_changed.connect(self._coordinate_handlers["work_x"])
        self.coordinates_vm.work_y_changed.connect(self._coordinate_handlers["work_y"])
        self.coordinates_vm.work_z_changed.connect(self._coordinate_handlers["work_z"])
        self._refresh_coordinate_fields()

    def _disconnect_coordinates_vm(self) -> None:
        """Отвязать предыдущий ViewModel."""
        if not self.coordinates_vm:
            return

        for key, handler in list(self._coordinate_handlers.items()):
            signal = getattr(self.coordinates_vm, f"{key}_changed", None)
            if signal and handler:
                try:
                    signal.disconnect(handler)
                except Exception:
                    pass
        self._coordinate_handlers.clear()

    def _connect_app_state_signals(self) -> None:
        if not self.app_state:
            return
        self.app_state.gcode_lines_changed.connect(self._on_gcode_lines_changed)
        self.app_state.run_status_changed.connect(self._on_run_status_changed)
        self.app_state.current_line_changed.connect(self._on_current_line_changed)
        self.app_state.jog_step_changed.connect(self._on_jog_step_changed)

    def _connect_connection_signals(self) -> None:
        if not self.connection_controller:
            return
        self.connection_controller.ports_changed.connect(self._on_ports_changed)
        self.connection_controller.connected.connect(self._on_port_connected)
        self.connection_controller.disconnected.connect(self._on_port_disconnected)
        manager = getattr(self.connection_controller, "get_manager", lambda: None)()
        if manager:
            manager.ports_updated.connect(self._on_ports_updated)

    def _connect_gcode_controller_signals(self) -> None:
        if not self.gcode_controller:
            return
        self.gcode_controller.gcode_loaded.connect(self._on_gcode_lines_changed)

    def _connect_serial_signals(self) -> None:
        if not self.serial_manager:
            return
        self.serial_manager.line_sent.connect(lambda line: self._append_console(f"→ {line}"))
        self.serial_manager.line_received.connect(lambda line: self._append_console(f"← {line}"))
        self.serial_manager.error.connect(lambda error: self._append_console(f"Ошибка: {error}"))

    def _sync_initial_state(self) -> None:
        if self.app_state:
            self._on_gcode_lines_changed(self.app_state.gcode_lines)
            self._on_run_status_changed(self.app_state.run_status)
            self._on_jog_step_changed(self.app_state.jog_step)
            params = getattr(self.app_state, "jog_params", {})
            self._apply_motion_params(params)

    # --------------------------------------------------------------------- #
    # Coordinates handling
    # --------------------------------------------------------------------- #
    def _update_machine_value(self, index: int, value: float) -> None:
        values = list(self._machine_values)
        values[index] = value
        self._machine_values = tuple(values)
        self._refresh_coordinate_fields()

    def _update_work_value(self, index: int, value: float) -> None:
        values = list(self._work_values)
        values[index] = value
        self._work_values = tuple(values)
        self._refresh_coordinate_fields()

    def set_to_go_values(self, values: Sequence[float]) -> None:
        """Публичный метод для подключения внешних вычислений To Go."""
        padded = list(values[:3]) + [0.0] * (3 - len(values))
        self._to_go_values = tuple(padded[:3])
        self._refresh_coordinate_fields()

    def _refresh_coordinate_fields(self) -> None:
        self.machine_field.setText(self._format_coord_text(self._machine_values))
        self.absolute_field.setText(self._format_coord_text(self._work_values))
        self.to_go_field.setText(self._format_coord_text(self._to_go_values))

    @staticmethod
    def _format_coord_text(values: Tuple[float, float, float]) -> str:
        return f"X: {values[0]:.3f}  Y: {values[1]:.3f}  Z: {values[2]:.3f}"

    # --------------------------------------------------------------------- #
    # G-code block handlers
    # --------------------------------------------------------------------- #
    def _on_start_cycle_clicked(self) -> None:
        if self.run_controller:
            self.run_controller.start()
        else:
            self.start_cycle_requested.emit()

    def _on_line_by_line_clicked(self) -> None:
        adapter = _InlineEditorAdapter(self.gcode_editor)
        if self.run_controller:
            send_single_line = getattr(self.run_controller, "send_single_line", None)
            if callable(send_single_line):
                send_single_line(adapter)
            elif hasattr(self.run_controller, "start_from_editor"):
                self.run_controller.start_from_editor(adapter)
            else:
                self.send_line_by_line_requested.emit()
        else:
            self.send_line_by_line_requested.emit()

    def _on_stop_clicked(self) -> None:
        if self.run_controller:
            self.run_controller.stop()
        else:
            self.stop_cycle_requested.emit()

    def _on_load_code_clicked(self) -> None:
        """Открыть диалог выбора файла и загрузить G-code в редактор"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть G-code файл",
            "",
            "G-code файлы (*.gcode *.nc);;Все файлы (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # Загружаем файл через контроллер, если он есть
            if self.gcode_controller:
                if self.gcode_controller.load_gcode_from_file(filepath):
                    # Файл загружен через контроллер, он автоматически обновит AppState
                    # и через сигнал gcode_lines_changed обновится редактор
                    if self.app_state:
                        self.app_state.set_gcode_file_path(filepath)
                    self._append_console(f"Файл загружен: {filepath}")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось загрузить G-code файл")
            else:
                # Если контроллера нет, загружаем напрямую в редактор
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.gcode_editor.setPlainText(content)
                self._append_console(f"Файл загружен: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки файла:\n{str(e)}")
            self._append_console(f"Ошибка загрузки файла: {str(e)}")

    def _on_goto_line_clicked(self) -> None:
        text = self.goto_line_input.text().strip()
        if not text:
            return
        try:
            line_number = int(text)
        except ValueError:
            self._append_console(f"Некорректный номер строки: {text}")
            return
        if self.gcode_controller and hasattr(self.gcode_controller, "goto_line"):
            self.gcode_controller.goto_line(line_number)
        else:
            self.goto_line_requested.emit(line_number)

    def _on_gcode_lines_changed(self, lines: List[str]) -> None:
        self.gcode_editor.blockSignals(True)
        self.gcode_editor.setPlainText("\n".join(lines))
        self.gcode_editor.blockSignals(False)

    def _on_current_line_changed(self, line_index: int) -> None:
        cursor = self.gcode_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_index):
            cursor.movePosition(cursor.MoveOperation.Down)
        self.gcode_editor.setTextCursor(cursor)

    def _on_run_status_changed(self, status: RunStatus) -> None:
        running = status == RunStatus.RUNNING
        self.start_cycle_btn.setEnabled(not running)
        self.line_by_line_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    # --------------------------------------------------------------------- #
    # Connection block
    # --------------------------------------------------------------------- #
    def _on_refresh_ports_clicked(self) -> None:
        if self.connection_controller:
            self.connection_controller.refresh_ports()

    def _on_connect_clicked(self) -> None:
        port = self._get_selected_port()
        if not port:
            self._append_console("Порт не выбран")
            return
        if self.connection_controller:
            connect_selected = getattr(self.connection_controller, "connect_selected", None)
            if callable(connect_selected):
                connect_selected(port)
            else:
                self.connection_controller.connect_to_port(port)
            return
        self.connect_requested.emit(port)

    def _on_ports_changed(self, ports: List[object]) -> None:
        self._populate_port_combo(ports)

    def _on_ports_updated(self, ports: List[object]) -> None:
        self._populate_port_combo(ports)

    def _populate_port_combo(self, ports: List[object]) -> None:
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self._ports_cache = []
        for port_info in ports:
            device = getattr(port_info, "name", None) or getattr(port_info, "device", None)
            description = getattr(port_info, "description", "")
            if device:
                label = f"{device} ({description})" if description else device
                self.port_combo.addItem(label, device)
                self._ports_cache.append(device)
        self.port_combo.blockSignals(False)

    def _on_port_connected(self, port: str) -> None:
        self._append_console(f"Подключено: {port}")
        index = self.port_combo.findData(port)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        self.connect_btn.setEnabled(False)

    def _on_port_disconnected(self) -> None:
        self._append_console("Порт отключён")
        self.connect_btn.setEnabled(True)

    def _get_selected_port(self) -> Optional[str]:
        data = self.port_combo.currentData()
        if isinstance(data, str):
            return data
        text = self.port_combo.currentText()
        if text:
            for cached in self._ports_cache:
                if cached in text:
                    return cached
        return None

    # --------------------------------------------------------------------- #
    # Jog panel and motion params
    # --------------------------------------------------------------------- #
    def _on_jog_button_clicked(self) -> None:
        sender = self.sender()
        if not isinstance(sender, QPushButton):
            return
        axis = sender.property("axis")
        direction = float(sender.property("direction") or 0.0)
        step = self._get_jog_step()
        if axis:
            delta = direction * step
            command = self._build_jog_command(axis, delta)
            self._dispatch_jog_command(command, axis, delta)

    def _build_jog_command(self, axis: str, delta: float) -> str:
        feed = self._get_feed_rate()
        return f"G91 G0 {axis}{delta:.3f} F{feed:.3f}"

    def _dispatch_jog_command(self, command: str, axis: str, delta: float) -> None:
        if self.serial_manager:
            self.serial_manager.send_immediate(command, wait_ok=False)
            return
        if self.run_controller:
            self.run_controller.send_immediate(command, wait_ok=False)
            return
        self.jog_command_requested.emit(axis, delta)

    def _on_motion_params_changed(self) -> None:
        params = {
            "feed": self._parse_float(self.feed_field.text(), default=self._get_feed_rate()),
            "spindle": self._parse_float(self.spindle_field.text(), default=0.0),
            "step": self._parse_float(self.step_field.text(), default=self._get_jog_step()),
            "speed": self._parse_float(self.jog_speed_field.text(), default=self._get_feed_rate()),
        }
        self._apply_motion_params(params)
        self.jog_params_changed.emit(params)
        if self.app_state:
            setattr(self.app_state, "jog_params", params)
            self.app_state.set_jog_step(params["step"])
            self.app_state.set_jog_feedrate(params["speed"])

    def _apply_motion_params(self, params: Dict[str, float]) -> None:
        self.feed_field.setText(f"{params.get('feed', 0.0):.3f}")
        self.spindle_field.setText(f"{params.get('spindle', 0.0):.3f}")
        self.step_field.setText(f"{params.get('step', 0.0):.3f}")
        self.jog_speed_field.setText(f"{params.get('speed', 0.0):.3f}")

    def _get_jog_step(self) -> float:
        params = getattr(self.app_state, "jog_params", {})
        return float(params.get("step", getattr(self.app_state, "jog_step", 1.0)))

    def _get_feed_rate(self) -> float:
        params = getattr(self.app_state, "jog_params", {})
        return float(params.get("feed", getattr(self.app_state, "jog_feedrate", 1000.0)))

    def _on_jog_step_changed(self, value: float) -> None:
        params = getattr(self.app_state, "jog_params", {})
        params["step"] = value
        self.step_field.setText(f"{value:.3f}")

    @staticmethod
    def _parse_float(text: str, default: float = 0.0) -> float:
        try:
            return float(text.replace(",", "."))
        except (ValueError, AttributeError):
            return default

    # --------------------------------------------------------------------- #
    # Console block
    # --------------------------------------------------------------------- #
    def _on_console_send(self) -> None:
        command = self.console_input.text().strip()
        if not command:
            return
        if self.serial_manager:
            self.serial_manager.send_immediate(command, wait_ok=False)
        else:
            self.console_command_submitted.emit(command)
        self.console_input.clear()
        self._append_console(f"→ {command}")

    def _append_console(self, text: str) -> None:
        self.console_history.appendPlainText(text)


class _InlineEditorAdapter:
    """Минимальный адаптер для RunController.start_from_editor."""

    def __init__(self, editor: QPlainTextEdit):
        self._editor = editor

    def get_lines(self) -> List[str]:
        return self._editor.toPlainText().splitlines()
