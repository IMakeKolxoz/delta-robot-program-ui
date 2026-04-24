"""
Диалог отображения траектории в проекциях XY, YZ, XZ
"""
from typing import List, Tuple
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class TrajectoryDialog(QDialog):
    """Диалог с тремя проекциями траектории: XY, YZ, XZ"""
    
    def __init__(self, trajectory_points_3d: List[Tuple[float, float, float]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Траектория - Проекции")
        self.setMinimumSize(900, 600)
        
        self.trajectory_points_3d: List[Tuple[float, float, float]] = trajectory_points_3d or []
        
        self._init_ui()
        if self.trajectory_points_3d:
            self._update_all_projections()
    
    def _init_ui(self):
        """Инициализация UI с тремя графиками"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title = QLabel("Проекции траектории")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Сетка из трех графиков
        graphs_layout = QHBoxLayout()
        
        # Проекция XY
        self.xy_widget = self._create_plot_widget("XY", "X (мм)", "Y (мм)")
        graphs_layout.addWidget(self.xy_widget)
        
        # Проекция YZ
        self.yz_widget = self._create_plot_widget("YZ", "Y (мм)", "Z (мм)")
        graphs_layout.addWidget(self.yz_widget)
        
        # Проекция XZ
        self.xz_widget = self._create_plot_widget("XZ", "X (мм)", "Z (мм)")
        graphs_layout.addWidget(self.xz_widget)
        
        layout.addLayout(graphs_layout)
        
        # Кнопка закрытия
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def _create_plot_widget(self, title: str, x_label: str, y_label: str) -> pg.PlotWidget:
        """Создать виджет графика для проекции"""
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('white')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setLabel('left', y_label, color='#34495e')
        plot_widget.setLabel('bottom', x_label, color='#34495e')
        plot_widget.setTitle(title, color='#2c3e50', size='12pt')
        
        # Цвет осей
        plot_widget.getAxis('left').setPen(pg.mkPen(color='#95a5a6'))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#95a5a6'))
        
        # Траектория (синяя линия)
        plot_item = plot_widget.plot([], [], 
                                    pen=pg.mkPen(color='#3498db', width=2))
        plot_widget.plot_item = plot_item
        
        return plot_widget
    
    def set_trajectory_points(self, points_3d: List[Tuple[float, float, float]]):
        """Установить точки траектории (x, y, z)"""
        self.trajectory_points_3d = points_3d
        self._update_all_projections()
    
    def _update_all_projections(self):
        """Обновить все три проекции"""
        if not self.trajectory_points_3d:
            self._clear_all_projections()
            return
        
        # Извлекаем координаты
        xs = [p[0] for p in self.trajectory_points_3d if len(p) >= 1]
        ys = [p[1] for p in self.trajectory_points_3d if len(p) >= 2]
        zs = [p[2] if len(p) >= 3 else 0.0 for p in self.trajectory_points_3d]
        
        # Проекция XY
        self.xy_widget.plot_item.setData(xs, ys, pen=pg.mkPen(color='#3498db', width=2))
        if xs and ys:
            self._auto_scale(self.xy_widget, xs, ys)
        
        # Проекция YZ
        self.yz_widget.plot_item.setData(ys, zs, pen=pg.mkPen(color='#3498db', width=2))
        if ys and zs:
            self._auto_scale(self.yz_widget, ys, zs)
        
        # Проекция XZ
        self.xz_widget.plot_item.setData(xs, zs, pen=pg.mkPen(color='#3498db', width=2))
        if xs and zs:
            self._auto_scale(self.xz_widget, xs, zs)
    
    def _auto_scale(self, plot_widget: pg.PlotWidget, x_data: List[float], y_data: List[float]):
        """Автомасштабирование графика"""
        if not x_data or not y_data:
            return
        x_min, x_max = min(x_data), max(x_data)
        y_min, y_max = min(y_data), max(y_data)
        margin_x = (x_max - x_min) * 0.1 if x_max != x_min else 1.0
        margin_y = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
        plot_widget.setXRange(x_min - margin_x, x_max + margin_x)
        plot_widget.setYRange(y_min - margin_y, y_max + margin_y)
    
    def _clear_all_projections(self):
        """Очистить все проекции"""
        self.xy_widget.plot_item.setData([], [])
        self.yz_widget.plot_item.setData([], [])
        self.xz_widget.plot_item.setData([], [])

