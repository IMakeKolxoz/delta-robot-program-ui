"""
Контроллер управления G-code
"""
from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
from app.models.app_state import AppState
from app.services.gcode_parser import GCodeParser, GCodeParseResult
from app.utils.logger import get_logger

logger = get_logger()


class GCodeController(QObject):
    """
    Контроллер управления G-code файлами и визуализацией
    
    Функции:
    - Загрузка файла
    - Парсинг через GCodeParser
    - Обновление GCodeView и TrajectoryView
    """
    
    # Сигналы для UI
    gcode_loaded = pyqtSignal(list)  # clean_lines для отправки
    trajectory_updated = pyqtSignal(list)  # points_xy для визуализации
    
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.parser = GCodeParser()
        self.parse_result: GCodeParseResult = None
    
    def load_gcode_from_file(self, filepath: str) -> bool:
        """
        Загрузить G-code из файла
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            True если успешно
        """
        try:
            logger.info(f"Загрузка файла: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Убираем \n и пустые строки
            lines = [line.rstrip() for line in lines]
            
            # Парсим G-code
            self.parse_result = self.parser.parse(lines)
            
            # Обновляем состояние
            self.app_state.set_gcode_lines(self.parse_result.clean_lines)
            
            # Эмитируем сигналы
            self.gcode_loaded.emit(self.parse_result.clean_lines)
            self.trajectory_updated.emit(self.parse_result.points_xy)
            
            logger.info(f"Загружено строк: {len(self.parse_result.clean_lines)}, точек: {len(self.parse_result.points_xy)}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            return False
    
    def get_trajectory_points(self) -> List:
        """
        Получить точки траектории для визуализации
        
        Returns:
            Список точек (x, y)
        """
        if self.parse_result:
            return self.parse_result.points_xy
        return []
    
    def get_gcode_lines(self) -> List[str]:
        """
        Получить список строк G-code (очищенных)
        
        Returns:
            Список строк для отправки
        """
        if self.parse_result:
            return self.parse_result.clean_lines
        return []
    
    def get_clean_lines(self) -> List[str]:
        """Получить очищенные строки для отправки"""
        return self.get_gcode_lines()

