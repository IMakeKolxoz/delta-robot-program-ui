import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Параметры кармана
length = 110  # длина кармана
width = 70    # ширина кармана
corner_radius = 15  # радиус скругления углов
center_x, center_y = 250, 330

# Расчет координат углов кармана (с учётом скруглений)
x0 = center_x - length/2
y0 = center_y - width/2

# Создаем фигуру
fig, ax = plt.subplots(figsize=(8, 6))

# Контур кармана с закругленными углами
pocket = patches.FancyBboxPatch(
    (x0, y0), length, width,
    boxstyle=patches.BoxStyle("Round", rounding_size=corner_radius),
    linewidth=2, edgecolor='blue', facecolor='none'
)
ax.add_patch(pocket)

# Добавим линии проходов (пример: спиральная стратегия — просто горизонтальные линии с шагом 10 мм)
step_xy = 10
current_width = width - 2*corner_radius
y_start = y0 + corner_radius
while current_width > 0:
    ax.plot([x0 + corner_radius, x0 + length - corner_radius], [y_start, y_start], 'r--')
    y_start += step_xy
    current_width -= step_xy

# Центр кармана
ax.plot(center_x, center_y, 'ko', label='Центр кармана')

# Настройка графика
ax.set_aspect('equal')
ax.set_xlim(center_x - length, center_x + length)
ax.set_ylim(center_y - length, center_y + length)
ax.set_title('Схема кармана POCKET1 (Top View)')
ax.set_xlabel('X, мм')
ax.set_ylabel('Y, мм')
ax.legend()
plt.grid(True)
plt.show()
