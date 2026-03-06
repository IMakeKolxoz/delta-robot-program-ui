"""
Управление матричной клавиатурой 4x4 через GPIO на Raspberry Pi.

Клавиши 1–8 вызывают те же действия, что и кнопки джога в интерфейсе:
  1 → +X   2 → -X   3 → +Y   4 → -Y   5 → +Z   6 → -Z   7 → шаг+   8 → шаг-

Используется RPi.GPIO. На платформах без GPIO (не RPi) модуль не активируется.
Arduino и протокол G-code не изменяются — команды отправляются через тот же SerialManager.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

# RPi.GPIO доступен только на Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO = None  # type: ignore
    GPIO_AVAILABLE = False


# Стандартная раскладка 4x4 (строки x столбцы)
# Подключение: 4 пина строк (OUT), 4 пина столбцов (IN, pull-up)
DEFAULT_ROW_PINS = [5, 6, 13, 19]   # BCM, строки (выходы)
DEFAULT_COL_PINS = [12, 16, 20, 21]  # BCM, столбцы (входы)

# Символы клавиш по позиции [row][col]
KEYPAD_MATRIX = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]

# Маппинг клавиш на действия джога (те же, что были у кнопок интерфейса)
# Ключ — символ клавиши, значение — (axis, direction) или ("step_inc",) / ("step_dec",)
JOG_KEY_MAP = {
    "1": ("X", 1.0),   # +X
    "2": ("X", -1.0),  # -X
    "3": ("Y", 1.0),   # +Y
    "4": ("Y", -1.0),  # -Y
    "5": ("Z", 1.0),   # +Z
    "6": ("Z", -1.0),  # -Z
    "7": ("step_inc",),
    "8": ("step_dec",),
}


def _build_jog_command(axis: str, delta: float, feed: float) -> str:
    """Собрать G-code команду джога (как в JogPanel / MainCompactView)."""
    sign = "+" if delta >= 0 else ""
    return f"G91 G0 {axis}{sign}{abs(delta):.3f} F{feed:.0f}"


class KeypadScanner(threading.Thread):
    """
    Поток сканирования матричной клавиатуры 4x4.
    При нажатии клавиши вызывает callback с символом клавиши.
    """

    def __init__(
        self,
        on_key: Callable[[str], None],
        row_pins: Optional[list[int]] = None,
        col_pins: Optional[list[int]] = None,
        debounce_sec: float = 0.15,
    ):
        super().__init__(daemon=True)
        self._on_key = on_key
        self._row_pins = row_pins or DEFAULT_ROW_PINS
        self._col_pins = col_pins or DEFAULT_COL_PINS
        self._debounce = debounce_sec
        self._stop = threading.Event()

    def run(self) -> None:
        if not GPIO_AVAILABLE or GPIO is None:
            return
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for p in self._row_pins:
                GPIO.setup(p, GPIO.OUT)
            for p in self._col_pins:
                GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            while not self._stop.is_set():
                key_pressed = None
                for ri, row_pin in enumerate(self._row_pins):
                    for r in range(4):
                        GPIO.output(self._row_pins[r], GPIO.LOW if r == ri else GPIO.HIGH)
                    for ci, col_pin in enumerate(self._col_pins):
                        if GPIO.input(col_pin) == GPIO.LOW:
                            key_pressed = KEYPAD_MATRIX[ri][ci]
                            break
                    if key_pressed is not None:
                        break
                if key_pressed is not None:
                    self._on_key(key_pressed)
                    time.sleep(self._debounce)
                time.sleep(0.02)
        except Exception:
            pass
        finally:
            if GPIO_AVAILABLE and GPIO is not None:
                try:
                    GPIO.cleanup()
                except Exception:
                    pass

    def stop(self) -> None:
        self._stop.set()


def create_jog_handler(
    send_command: Callable[[str], None],
    get_step: Callable[[], float],
    get_feed: Callable[[], float],
    set_step: Optional[Callable[[float], None]] = None,
    step_delta: float = 0.5,
) -> Callable[[str], None]:
    """
    Создать обработчик нажатий клавиш, который вызывает те же действия, что и кнопки джога.

    - send_command(gcode) — отправка G-code (то же, что RunController.send_immediate).
    - get_step / get_feed — текущие шаг и feedrate (из AppState или виджета).
    - set_step(step) — опционально, для клавиш 7/8 (увеличить/уменьшить шаг).
    - step_delta — на сколько менять шаг по 7/8.
    """

    def on_key(key: str) -> None:
        action = JOG_KEY_MAP.get(key)
        if not action:
            return
        if action[0] == "step_inc":
            if set_step is not None:
                new_step = max(0.1, get_step() + step_delta)
                set_step(new_step)
            return
        if action[0] == "step_dec":
            if set_step is not None:
                new_step = max(0.1, get_step() - step_delta)
                set_step(new_step)
            return
        axis, direction = action[0], action[1]
        step = get_step()
        feed = get_feed()
        delta = direction * step
        command = _build_jog_command(axis, delta, feed)
        send_command(command)

    return on_key


def is_available() -> bool:
    """Проверить, доступна ли работа с GPIO (Raspberry Pi)."""
    return GPIO_AVAILABLE
