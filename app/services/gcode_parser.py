"""
Парсер G-code для извлечения траекторий и очистки команд
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass
import re
from app.utils.logger import get_logger

logger = get_logger()


@dataclass
class GCodeParseResult:
    """
    Результат парсинга G-code
    
    Attributes:
        clean_lines: Очищенные строки для отправки
        points_xy: Массив 2D точек (x, y) для визуализации
    """
    clean_lines: List[str]
    points_xy: List[Tuple[float, float]]


class GCodeParser:
    """
    Простой парсер G-code
    
    Функционал:
    - Удаление комментариев ; и (...)
    - Извлечение координат X, Y для G0/G1
    - Поддержка G90/G91 (абсолютные/относительные координаты)
    - Генерация точек для 2D визуализации
    """
    
    def __init__(self):
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.is_relative = False  # G90/G91 режим
        self.current_feedrate: Optional[float] = None
    
    def clean_line(self, line: str) -> str:
        """
        Очистить строку от комментариев и лишних пробелов
        
        Args:
            line: Исходная строка G-code
            
        Returns:
            Очищенная строка
        """
        # Удаляем комментарии в скобках (...)
        line = re.sub(r'\([^)]*\)', '', line)
        
        # Удаляем комментарии после ;
        if ';' in line:
            line = line.split(';')[0]
        
        # Тримминг и удаление лишних пробелов
        line = ' '.join(line.split())
        return line.strip()
    
    def extract_float(self, line: str, letter: str) -> Optional[float]:
        """
        Извлечь значение после буквы
        
        Args:
            line: Строка (например, "G0 X10.5 Y20")
            letter: Буква (например, "X")
            
        Returns:
            Значение или None
        """
        pattern = rf'{letter}(-?\d+\.?\d*)'
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
    
    def parse(self, lines: List[str]) -> GCodeParseResult:
        """
        Распарсить G-code
        
        Args:
            lines: Список строк G-code
            
        Returns:
            GCodeParseResult с clean_lines и points_xy
        """
        clean_lines = []
        points_xy = []
        
        # Сброс состояния
        self.current_x = 0.0
        self.current_y = 0.0
        self.is_relative = False
        
        for line in lines:
            # Пропускаем пустые строки и чистые комментарии
            if not line or line.strip().startswith(';') or line.strip().startswith('('):
                continue
            
            # Очищаем строку
            cleaned = self.clean_line(line)
            if not cleaned:
                continue
            
            # Обработка команд
            self._process_line(cleaned, clean_lines, points_xy)
        
        logger.info(f"Спарсено: {len(clean_lines)} строк, {len(points_xy)} точек")
        
        return GCodeParseResult(
            clean_lines=clean_lines,
            points_xy=points_xy
        )
    
    def _process_line(self, line: str, clean_lines: List[str], points_xy: List[Tuple[float, float]]):
        """
        Обработать одну строку
        
        Args:
            line: Очищенная строка
            clean_lines: Список для добавления чистых строк
            points_xy: Список для добавления точек
        """
        upper_line = line.upper()
        
        # Определяем режим G90/G91
        if 'G90' in upper_line:
            self.is_relative = False
            clean_lines.append(line)
            return
        
        if 'G91' in upper_line:
            self.is_relative = True
            clean_lines.append(line)
            return
        
        # Обработка G0/G1 (линейные перемещения)
        if 'G0' in upper_line or 'G1' in upper_line:
            x = self.extract_float(line, 'X')
            y = self.extract_float(line, 'Y')
            z = self.extract_float(line, 'Z')
            f = self.extract_float(line, 'F')
            
            # Обновляем координаты
            if x is not None:
                if self.is_relative:
                    self.current_x += x
                else:
                    self.current_x = x
            
            if y is not None:
                if self.is_relative:
                    self.current_y += y
                else:
                    self.current_y = y
            
            if z is not None:
                if self.is_relative:
                    self.current_z += z
                else:
                    self.current_z = z
            
            if f is not None:
                self.current_feedrate = f
            
            # Добавляем точку для визуализации (XY)
            points_xy.append((self.current_x, self.current_y))
            clean_lines.append(line)
            return
        
        # Обработка G2/G3 (дуги) - пока игнорируем, добавляем TODO
        if 'G2' in upper_line or 'G3' in upper_line:
            # TODO: интерполировать дуги на сегменты
            x = self.extract_float(line, 'X')
            y = self.extract_float(line, 'Y')
            
            if x is not None and y is not None:
                # Для прототипа просто добавляем конечную точку дуги
                if self.is_relative:
                    self.current_x += x
                    self.current_y += y
                else:
                    self.current_x = x
                    self.current_y = y
                points_xy.append((self.current_x, self.current_y))
            
            clean_lines.append(line)
            return
        
        # Все остальные команды (M-codes, другие G-codes) - просто добавляем
        clean_lines.append(line)
    
    def extract_trajectory_2d(self, lines: List[str]) -> List[Tuple[float, float]]:
        """
        Извлечь 2D траекторию (X, Y) из G-code
        
        Args:
            lines: Список строк G-code
            
        Returns:
            Список точек (x, y)
        """
        result = self.parse(lines)
        return result.points_xy

