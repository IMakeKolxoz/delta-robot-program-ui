"""
Виджет для визуализации 2D траектории с маркером текущей позиции
"""
from typing import List, Tuple, Optional
from PyQt6.QtWidgets import QWidget
import pyqtgraph as pg


class TrajectoryView(QWidget):
    """
    Визуализация траектории 2D XY с использованием pyqtgraph
    
    Отображает траекторию и текущую позицию (курсор)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.trajectory_points: List[Tuple[float, float]] = []
        self.cursor_item: Optional[pg.ScatterPlotItem] = None
    
    def _init_ui(self):
        """Инициализация pyqtgraph виджета"""
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('white')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Y (мм)', color='#34495e')
        self.plot_widget.setLabel('bottom', 'X (мм)', color='#34495e')
        
        # Цвет оси
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color='#95a5a6'))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#95a5a6'))
        
        # Траектория (синяя линия)
        self.plot_item = self.plot_widget.plot([], [], 
                                                pen=pg.mkPen(color='#3498db', width=2))
        
        # Курсор (красная точка)
        self.cursor_item = pg.ScatterPlotItem([], [], 
                                              pen=pg.mkPen(color='#e74c3c', width=2),
                                              brush=pg.mkBrush(color='#e74c3c'),
                                              size=12,
                                              symbol='o')
        self.plot_widget.addItem(self.cursor_item)
        
        # Layout
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
    
    def set_path(self, points: List[Tuple[float, float]]) -> None:
        """
        Установить траекторию для отображения
        
        Args:
            points: Список точек (x, y)
        """
        self.trajectory_points = points
        
        if not points:
            self.plot_item.setData([], [])
            return
        
        # Извлекаем X и Y координаты
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        # Отрисовываем траекторию
        self.plot_item.setData(xs, ys, pen=pg.mkPen(color='#3498db', width=2))
        
        # Автомасштабирование с отступами
        if xs and ys:
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            margin = max((x_max - x_min), (y_max - y_min)) * 0.1
            self.plot_widget.setXRange(x_min - margin, x_max + margin)
            self.plot_widget.setYRange(y_min - margin, y_max + margin)
    
    def clear_path(self) -> None:
        """Очистить траекторию"""
        self.trajectory_points = []
        self.plot_item.setData([], [])
        if self.cursor_item:
            self.cursor_item.setData([], [])
    
    def update_cursor(self, x: float, y: float) -> None:
        """
        Обновить позицию курсора (текущая точка)
        
        Args:
            x: X координата
            y: Y координата
        """
        if self.cursor_item:
            self.cursor_item.setData([x], [y],
                                    pen=pg.mkPen(color='#e74c3c', width=2),
                                    brush=pg.mkBrush(color='#e74c3c'),
                                    size=12)

