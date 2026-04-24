"""
Панель отображения координат дельта-робота
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton, 
                              QLabel, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from app.ui.coordinates_viewmodel import CoordinatesViewModel


class CoordinatesPanel(QWidget):
    """
    Панель отображения координат дельта-робота
    
    Отображает:
    - Machine координаты (X, Y, Z) - абсолютные
    - Work координаты (X, Y, Z) - относительные
    - Кнопка обновления
    - Индикатор обновления
    """
    
    def __init__(self, view_model: CoordinatesViewModel, parent=None):
        """
        Инициализация панели координат
        
        Args:
            view_model: ViewModel координат
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.view_model = view_model
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        label = QLabel("Координаты")
        label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(label)
        
        # Таблица координат 2×3
        grid = QGridLayout()
        grid.setSpacing(5)
        
        # Заголовки
        grid.addWidget(QLabel(""), 0, 0)  # Пустая ячейка
        grid.addWidget(QLabel("X"), 0, 1)
        grid.addWidget(QLabel("Y"), 0, 2)
        grid.addWidget(QLabel("Z"), 0, 3)
        
        # Machine координаты
        machine_label = QLabel("Machine:")
        machine_label.setStyleSheet("font-weight: bold;")
        grid.addWidget(machine_label, 1, 0)
        
        self.machine_x_label = QLabel("0.00")
        self.machine_x_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.machine_x_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.machine_x_label, 1, 1)
        
        self.machine_y_label = QLabel("0.00")
        self.machine_y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.machine_y_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.machine_y_label, 1, 2)
        
        self.machine_z_label = QLabel("0.00")
        self.machine_z_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.machine_z_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.machine_z_label, 1, 3)
        
        # Work координаты
        work_label = QLabel("Work:")
        work_label.setStyleSheet("font-weight: bold;")
        grid.addWidget(work_label, 2, 0)
        
        self.work_x_label = QLabel("0.00")
        self.work_x_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.work_x_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.work_x_label, 2, 1)
        
        self.work_y_label = QLabel("0.00")
        self.work_y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.work_y_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.work_y_label, 2, 2)
        
        self.work_z_label = QLabel("0.00")
        self.work_z_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.work_z_label.setStyleSheet("padding: 2px 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        grid.addWidget(self.work_z_label, 2, 3)
        
        layout.addLayout(grid)
        layout.addSpacing(10)
        
        # Кнопка обновления и индикатор
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.view_model.refresh_coordinates)
        button_layout.addWidget(self.refresh_btn)
        
        self.updating_label = QLabel("")
        self.updating_label.setStyleSheet("color: #666; font-size: 10pt;")
        button_layout.addWidget(self.updating_label)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Подключить сигналы ViewModel к UI"""
        # Подписываемся на изменения координат
        self.view_model.machine_x_changed.connect(self._on_machine_x_changed)
        self.view_model.machine_y_changed.connect(self._on_machine_y_changed)
        self.view_model.machine_z_changed.connect(self._on_machine_z_changed)
        self.view_model.work_x_changed.connect(self._on_work_x_changed)
        self.view_model.work_y_changed.connect(self._on_work_y_changed)
        self.view_model.work_z_changed.connect(self._on_work_z_changed)
        self.view_model.is_updating_changed.connect(self._on_is_updating_changed)
        
        # Инициализируем значения
        self._update_all_coordinates()
        self._on_is_updating_changed(self.view_model.is_updating)
    
    def _on_machine_x_changed(self, value: float):
        """Обновление Machine X"""
        self.machine_x_label.setText(f"{value:.2f}")
    
    def _on_machine_y_changed(self, value: float):
        """Обновление Machine Y"""
        self.machine_y_label.setText(f"{value:.2f}")
    
    def _on_machine_z_changed(self, value: float):
        """Обновление Machine Z"""
        self.machine_z_label.setText(f"{value:.2f}")
    
    def _on_work_x_changed(self, value: float):
        """Обновление Work X"""
        self.work_x_label.setText(f"{value:.2f}")
    
    def _on_work_y_changed(self, value: float):
        """Обновление Work Y"""
        self.work_y_label.setText(f"{value:.2f}")
    
    def _on_work_z_changed(self, value: float):
        """Обновление Work Z"""
        self.work_z_label.setText(f"{value:.2f}")
    
    def _on_is_updating_changed(self, is_updating: bool):
        """Обновление индикатора обновления"""
        if is_updating:
            self.updating_label.setText("⏳")
            self.refresh_btn.setEnabled(False)
        else:
            self.updating_label.setText("")
            self.refresh_btn.setEnabled(True)
    
    def _update_all_coordinates(self):
        """Обновить все координаты из ViewModel"""
        self.machine_x_label.setText(f"{self.view_model.machine_x:.2f}")
        self.machine_y_label.setText(f"{self.view_model.machine_y:.2f}")
        self.machine_z_label.setText(f"{self.view_model.machine_z:.2f}")
        self.work_x_label.setText(f"{self.view_model.work_x:.2f}")
        self.work_y_label.setText(f"{self.view_model.work_y:.2f}")
        self.work_z_label.setText(f"{self.view_model.work_z:.2f}")

