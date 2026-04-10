"""
Панель выбора COM-порта и управления подключением
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, 
                              QPushButton, QLabel)
from PySide6.QtCore import Qt, Signal


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
    port_selected = Signal(str)  # Выбранный порт (legacy)
    portSelected = Signal(str)  # Новый сигнал: передаёт device (COMx)
    connect_clicked = Signal()
    disconnect_clicked = Signal()
    refresh_clicked = Signal()
    
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
        self.port_combo.currentIndexChanged.connect(self._on_port_changed)
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
    
    def _on_port_changed(self):
        """Обработка изменения выбранного порта"""
        index = self.port_combo.currentIndex()
        if index >= 0:
            device = self.port_combo.itemData(index, Qt.ItemDataRole.UserRole)
            if not device:
                # Fallback: распарсить из текста, если нет itemData
                text = self.port_combo.itemText(index)
                device = text.split(" — ")[0] if " — " in text else text.split(" - ")[0]
            if device:
                # Эмитим оба сигнала для обратной совместимости
                self.port_selected.emit(device)
                self.portSelected.emit(device)
                # Сразу устанавливаем упрощённое состояние подключения
                self.set_connected_state(device, True)
    
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
        Установить список доступных портов (строковая версия).
        Предпочтительно использовать update_ports.
        """
        self.port_combo.clear()
        for text in ports:
            self.port_combo.addItem(text, text.split(" - ")[0] if " - " in text else text)

    def update_ports(self, ports: list[tuple[str, str]]) -> None:
        """
        Обновить список доступных портов.
        
        Args:
            ports: список кортежей (device, description)
        """
        self.port_combo.clear()
        for device, description in ports:
            display = f"{device} — {description}" if description else device
            self.port_combo.addItem(display, device)
    
    def get_selected_port(self) -> str:
        """
        Получить выбранный порт
        
        Returns:
            Имя порта (например, "COM3")
        """
        index = self.port_combo.currentIndex()
        if index < 0:
            return ""
        device = self.port_combo.itemData(index, Qt.ItemDataRole.UserRole)
        if device:
            return device
        # Fallback на текст
        text = self.port_combo.currentText()
        if " — " in text:
            return text.split(" — ")[0]
        if " - " in text:
            return text.split(" - ")[0]
        return text
    
    def set_connection_state(self, connected: bool):
        """
        Установить состояние подключения (legacy method)
        
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

    def set_connected_state(self, device: str | None, simplified: bool = True) -> None:
        """
        Установить состояние подключения (упрощённая модель)
        
        Args:
            device: Выбранный порт (COMx) или None
            simplified: True для упрощённой модели подключения
        """
        if device:
            self.status_label.setText(f"Статус: Подключено (упрощённо) — {device}")
            self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
            self.connect_btn.setEnabled(True)  # Всегда активна
            self.disconnect_btn.setEnabled(True)  # Активна если выбран порт
        else:
            self.status_label.setText("Статус: Отключено")
            self.status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
            self.connect_btn.setEnabled(True)  # Всегда активна
            self.disconnect_btn.setEnabled(False)  # Неактивна если нет порта

    def set_status_message(self, message: str):
        """Установить произвольное сообщение статуса на панели портов"""
        self.status_label.setText(message)

