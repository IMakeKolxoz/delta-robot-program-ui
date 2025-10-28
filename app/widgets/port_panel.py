"""
Панель выбора COM-порта и управления подключением
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, 
                              QPushButton, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal


class PortPanel(QWidget):
    """
    Панель выбора COM-порта и управления подключением
    
    Элементы:
    - ComboBox с доступными портами
    - Кнопка "Обновить"
    - Кнопки "Подключить" / "Отключить"
    - Метка статуса подключения
    """
    
    # Сигналы
    port_selected = pyqtSignal(str)  # Выбранный порт
    connect_clicked = pyqtSignal()
    disconnect_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        label = QLabel("Подключение")
        label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(label)
        
        # Выбор порта
        port_label = QLabel("COM-порт:")
        layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.setEditable(False)
        self.port_combo.currentTextChanged.connect(self._on_port_changed)
        layout.addWidget(self.port_combo)
        
        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить порты")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.refresh_btn)
        
        layout.addSpacing(10)
        
        # Кнопки управления
        self.connect_btn = QPushButton("Подключить")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Отключить")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.disconnect_clicked.emit)
        layout.addWidget(self.disconnect_btn)
        
        layout.addSpacing(10)
        
        # Метка статуса
        self.status_label = QLabel("Статус: Отключено")
        self.status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_port_changed(self, text: str):
        """Обработка изменения выбранного порта"""
        if text:
            # Извлекаем имя порта (до " - ")
            port_name = text.split(" - ")[0] if " - " in text else text
            self.port_selected.emit(port_name)
    
    def _on_connect_clicked(self):
        """Обработка нажатия кнопки подключения"""
        port = self.get_selected_port()
        if port:
            self.port_selected.emit(port)
            self.connect_clicked.emit()
        else:
            self.status_label.setText("Статус: Выберите порт")
    
    def set_ports(self, ports: list):
        """
        Установить список доступных портов
        
        Args:
            ports: Список строк с описанием портов
        """
        self.port_combo.clear()
        self.port_combo.addItems(ports)
    
    def get_selected_port(self) -> str:
        """
        Получить выбранный порт
        
        Returns:
            Имя порта (например, "COM3")
        """
        text = self.port_combo.currentText()
        if text and " - " in text:
            return text.split(" - ")[0]
        return text
    
    def set_connection_state(self, connected: bool):
        """
        Установить состояние подключения
        
        Args:
            connected: True если подключено
        """
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        
        if connected:
            self.port_combo.setEnabled(False)
            self.status_label.setText("Статус: Подключено")
            self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        else:
            self.port_combo.setEnabled(True)
            self.status_label.setText("Статус: Отключено")
            self.status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")

