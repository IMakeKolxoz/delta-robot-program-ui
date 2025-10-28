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
    
    def set_text(self, text: str) -> None:
        """
        Установить текст G-code
        
        Args:
            text: Полный текст для отображения
        """
        self.setPlainText(text)
    
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

