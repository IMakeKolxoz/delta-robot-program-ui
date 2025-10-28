"""
Виджет консоли для отображения обмена данными и отправки команд
"""
from PyQt6.QtWidgets import (QPlainTextEdit, QVBoxLayout, QHBoxLayout, 
                              QWidget, QLabel, QPushButton, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime


class ConsoleView(QWidget):
    """
    Консоль для мониторинга обмена данными
    
    Состоит из:
    - QPlainTextEdit (read-only) для отображения сообщений
    - QLineEdit + кнопка "Отправить" для разовой команды
    """
    
    # Сигналы
    command_to_send = pyqtSignal(str)  # Отправить команду
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок с кнопкой очистки
        header_layout = QHBoxLayout()
        label = QLabel("Консоль обмена")
        label.setStyleSheet("font-weight: bold;")
        
        clear_btn = QPushButton("Очистить")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.clear)
        
        header_layout.addWidget(label)
        header_layout.addStretch()
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Текстовая область (read-only)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(1000)  # Ограничение на количество строк
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # Поле ввода команды + кнопка
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Введите команду (например: G28 X0 Y0 Z0) и нажмите Enter или кнопку...")
        self.command_input.returnPressed.connect(self._send_command)
        input_layout.addWidget(self.command_input)
        
        send_btn = QPushButton("Отправить")
        send_btn.setMaximumWidth(100)
        send_btn.clicked.connect(self._send_command)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
    
    def _send_command(self):
        """Отправить команду из поля ввода"""
        command = self.command_input.text().strip()
        if command:
            self.command_to_send.emit(command)
            self.command_input.clear()
    
    def add_message(self, message: str, message_type: str = "info"):
        """
        Добавить сообщение в консоль
        
        Args:
            message: Текст сообщения
            message_type: Тип сообщения (info, sent, received, error)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Цвет в зависимости от типа
        color_map = {
            "info": "#ecf0f1",
            "sent": "#4ec9b0",
            "received": "#ce9178",
            "error": "#f48771"
        }
        color = color_map.get(message_type, "#ecf0f1")
        
        formatted = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        self.text_edit.appendHtml(formatted)
        
        # Автопрокрутка вниз
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
    
    def add_sent_command(self, command: str):
        """Добавить отправленную команду"""
        self.add_message(f"→ {command}", "sent")
    
    def add_received_response(self, response: str):
        """Добавить полученный ответ"""
        self.add_message(f"← {response}", "received")
    
    def add_error(self, error: str):
        """Добавить ошибку"""
        self.add_message(f"ERROR: {error}", "error")
    
    def add_info(self, info: str):
        """Добавить информационное сообщение"""
        self.add_message(info, "info")
    
    def clear(self):
        """Очистить консоль"""
        self.text_edit.clear()

