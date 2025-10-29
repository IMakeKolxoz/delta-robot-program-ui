"""
Виджет для отображения и редактирования G-code с номерами строк
"""
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import List


class GCodeView(QPlainTextEdit):
    """Редактируемый редактор G-code с номерами строк"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setPlaceholderText("Загрузите G-code файл...")
        self.setFont(QFont("Consolas", 9))
        
        # Настройка моноширинного шрифта для номера строк
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(40)
        
        # Принудительно устанавливаем стили для чёрного текста
        self.setStyleSheet("""
            GCodeView {
                background-color: #fafafa;
                color: #111;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 9pt;
                line-height: 1.2;
            }
        """)
    
    def set_text(self, text: str) -> None:
        """
        Установить текст G-code
        
        Args:
            text: Полный текст для отображения
        """
        self.setPlainText(text)
        # Убеждаемся, что текст отображается чёрным цветом
        self.setStyleSheet("""
            GCodeView {
                background-color: #fafafa;
                color: #111;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 9pt;
                line-height: 1.2;
            }
        """)
    
    def get_lines(self) -> List[str]:
        """
        Получить список строк G-code
        
        Returns:
            Список строк G-code
        """
        text = self.toPlainText()
        return text.split('\n')
    
    def load_file(self, filepath: str) -> bool:
        """
        Загрузить G-code из файла
        
        Args:
            filepath: Путь к файлу .gcode или .nc
            
        Returns:
            True если успешно загружен, False при ошибке
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.set_text(content)
            return True
        except Exception as e:
            print(f"Ошибка загрузки файла {filepath}: {e}")
            return False
    
    def get_text(self) -> str:
        """
        Получить весь текст
        
        Returns:
            Содержимое редактора как строка
        """
        return self.toPlainText()
    
    def highlight_line(self, line_index: int):
        """
        Подсветить строку по индексу
        
        Args:
            line_index: Индекс строки (0-based)
        """
        if line_index < 0:
            return
        
        # Получаем текст и разбиваем на строки
        lines = self.toPlainText().split('\n')
        if line_index >= len(lines):
            return
        
        # Вычисляем позицию начала строки
        char_position = 0
        for i in range(line_index):
            char_position += len(lines[i]) + 1  # +1 для символа новой строки
        
        # Устанавливаем курсор в начало строки
        cursor = self.textCursor()
        cursor.setPosition(char_position)
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
        
        # Выделяем строку
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
        # Применяем стиль подсветки
        self.setExtraSelections([self._create_line_selection(line_index)])
    
    def _create_line_selection(self, line_index: int):
        """Создать выделение для подсветки строки"""
        from PyQt6.QtWidgets import QTextEdit
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QTextCharFormat, QColor
        
        selection = QTextEdit.ExtraSelection()
        
        # Стиль подсветки
        format = QTextCharFormat()
        format.setBackground(QColor(255, 255, 0, 50))  # Светло-жёлтый фон
        format.setProperty(QTextCharFormat.Property.BackgroundColor, QColor(255, 255, 0, 50))
        
        selection.format = format
        
        # Получаем позицию строки
        lines = self.toPlainText().split('\n')
        if line_index >= len(lines):
            return selection
        
        char_position = 0
        for i in range(line_index):
            char_position += len(lines[i]) + 1
        
        # Устанавливаем выделение
        cursor = self.textCursor()
        cursor.setPosition(char_position)
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
        
        selection.cursor = cursor
        return selection

