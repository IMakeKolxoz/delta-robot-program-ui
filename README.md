# Delta Robot - G-code Sender

Прототип десктоп-приложения для управления роботом с дельта-кинематикой через Arduino Mega.

## Возможности

- Загрузка и редактирование G-code
- 2D визуализация траектории (XY)
- Подключение к COM-порту (Arduino Mega)
- Построчная отправка G-code с ожиданием ответа `ok`
- Ручное управление (jog) по осям X, Y, Z
- Консоль обмена данными
- Очередь команд с паузой/продолжением/остановкой

## Требования

- Python 3.11+
- Windows 10/11
- Arduino Mega (опционально, для тестирования)

## Установка для Windows

### 1. Создайте виртуальное окружение:
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Архитектура

```
app/
├── controllers/    # Контроллеры бизнес-логики
│   ├── connection_controller.py
│   ├── gcode_controller.py
│   └── run_controller.py
├── models/         # Модели данных
│   └── app_state.py
├── services/       # Сервисы (COM, парсинг)
│   ├── serial_manager.py
│   └── gcode_parser.py
├── ui/            # Главное окно и стили
│   ├── main_window.py
│   └── styles.qss
├── utils/         # Утилиты (логгер, настройки)
│   ├── logger.py
│   └── settings.py
└── widgets/       # UI виджеты
    ├── gcode_view.py
    ├── trajectory_view.py
    ├── console_view.py
    ├── port_panel.py
    └── jog_panel.py
```

## Зависимости

- **PySide6** >= 6.7 - GUI фреймворк
- **pyserial** >= 3.5 - COM порт
- **pyqtgraph** >= 0.13 - 2D визуализация
- **loguru** >= 0.7 - логирование

## Лицензия

MIT

