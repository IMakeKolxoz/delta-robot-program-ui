"""
Панель ручного управления (jog) с полями шага и скорости
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton, 
                              QLabel, QLineEdit, QDoubleSpinBox, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal


class JogPanel(QWidget):
    """
    Панель ручного управления осями
    
    Элементы:
    - Поле шага (мм)
    - Кнопки X±, Y±, Z±
    - Поле feedrate (F, мм/мин)
    - Поле для произвольной команды
    """
    
    # Сигналы
    jog_command = pyqtSignal(str)  # Сгенерированная G-code команда
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        # Устанавливаем объектное имя для QSS-таргетинга
        self.setObjectName("JogPanel")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        label = QLabel("Ручное управление (Jog)")
        label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(label)
        
        # Шаг перемещения
        self.step_label = QLabel("Шаг (мм):")
        self.step_label.setObjectName("JogStepLabel")
        layout.addWidget(self.step_label)
        
        self.step_spinbox = QDoubleSpinBox()
        self.step_spinbox.setObjectName("JogStepInput")
        self.step_spinbox.setDecimals(1)
        self.step_spinbox.setRange(0.1, 100.0)
        self.step_spinbox.setValue(1.0)
        self.step_spinbox.setSingleStep(0.5)
        layout.addWidget(self.step_spinbox)
        
        layout.addSpacing(10)
        
        # Feedrate
        self.feedrate_label = QLabel("Feedrate (мм/мин):")
        self.feedrate_label.setObjectName("JogFeedrateLabel")
        layout.addWidget(self.feedrate_label)
        
        self.feedrate_spinbox = QDoubleSpinBox()
        self.feedrate_spinbox.setObjectName("JogFeedrateInput")
        self.feedrate_spinbox.setDecimals(0)
        self.feedrate_spinbox.setRange(10, 10000)
        self.feedrate_spinbox.setValue(1000)
        self.feedrate_spinbox.setSingleStep(100)
        layout.addWidget(self.feedrate_spinbox)
        
        layout.addSpacing(10)
        
        # Кнопки управления осями
        grid = QGridLayout()
        
        # X
        self.btn_x_neg = QPushButton("X-")
        self.btn_x_neg.clicked.connect(lambda: self._on_jog("X", -self.step_spinbox.value()))
        grid.addWidget(self.btn_x_neg, 0, 0)
        
        self.btn_x_pos = QPushButton("X+")
        self.btn_x_pos.clicked.connect(lambda: self._on_jog("X", self.step_spinbox.value()))
        grid.addWidget(self.btn_x_pos, 0, 1)
        
        # Y
        self.btn_y_neg = QPushButton("Y-")
        self.btn_y_neg.clicked.connect(lambda: self._on_jog("Y", -self.step_spinbox.value()))
        grid.addWidget(self.btn_y_neg, 1, 0)
        
        self.btn_y_pos = QPushButton("Y+")
        self.btn_y_pos.clicked.connect(lambda: self._on_jog("Y", self.step_spinbox.value()))
        grid.addWidget(self.btn_y_pos, 1, 1)
        
        # Z
        self.btn_z_neg = QPushButton("Z-")
        self.btn_z_neg.clicked.connect(lambda: self._on_jog("Z", -self.step_spinbox.value()))
        grid.addWidget(self.btn_z_neg, 2, 0)
        
        self.btn_z_pos = QPushButton("Z+")
        self.btn_z_pos.clicked.connect(lambda: self._on_jog("Z", self.step_spinbox.value()))
        grid.addWidget(self.btn_z_pos, 2, 1)
        
        layout.addLayout(grid)
        layout.addSpacing(10)
        
        # Ручная команда
        custom_label = QLabel("Произвольная команда:")
        layout.addWidget(custom_label)
        
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setObjectName("JogCommandInput")
        self.command_input.setPlaceholderText("Например: G28 X0 Y0 Z0")
        self.command_input.returnPressed.connect(self._on_send_command)
        input_layout.addWidget(self.command_input)
        
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self._on_send_command)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_jog(self, axis: str, step: float):
        """
        Обработка нажатия кнопки jog
        
        Генерирует G-code команду: G91 G0 X±step F<feedrate>
        
        Args:
            axis: Ось (X, Y, Z)
            step: Шаг перемещения (мм)
        """
        sign = "+" if step > 0 else ""
        feedrate = self.feedrate_spinbox.value()
        # G91 - относительное перемещение, G0 - быстрая подача
        command = f"G91 G0 {axis}{sign}{abs(step):.2f} F{feedrate:.0f}"
        self.jog_command.emit(command)
    
    def _on_send_command(self):
        """Отправить произвольную команду"""
        command = self.command_input.text().strip()
        if command:
            self.jog_command.emit(command)
            self.command_input.clear()
    
    def get_step(self) -> float:
        """
        Получить текущий шаг
        
        Returns:
            Шаг в мм
        """
        return self.step_spinbox.value()
    
    def set_step(self, step: float):
        """
        Установить шаг
        
        Args:
            step: Шаг в мм
        """
        self.step_spinbox.setValue(step)
    
    def set_enabled(self, enabled: bool):
        """
        Включить/выключить кнопки
        
        Args:
            enabled: True для включения
        """
        for btn in [self.btn_x_pos, self.btn_x_neg, 
                    self.btn_y_pos, self.btn_y_neg,
                    self.btn_z_pos, self.btn_z_neg]:
            btn.setEnabled(enabled)

