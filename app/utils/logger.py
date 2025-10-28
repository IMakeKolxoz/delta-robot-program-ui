"""
Настройка логирования через loguru

Формат:
- Файл logs/app.log: полный формат с временем, уровнем, функцией, номером строки
- Консоль: упрощенный формат для удобного чтения
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logging():
    """
    Настроить логирование
    
    Настройки:
    - Файл logs/app.log с ротацией (10 MB, 10 дней)
    - Консоль с цветной подсветкой
    - Формат с временем, уровнем, функцией, сообщением
    """
    
    # Создаем директорию logs если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Удаляем стандартные handlers
    logger.remove()
    
    # === Логирование в файл ===
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",  # DEBUG и выше
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        enqueue=True,  # Асинхронное логирование
        backtrace=True,  # Подробный traceback
        diagnose=True  # Контекст переменных
    )
    
    # === Логирование в консоль ===
    logger.add(
        sys.stderr,
        level="INFO",  # INFO и выше
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{name}</cyan> | {message}",
        colorize=True
    )
    
    logger.info("Логирование настроено")


def get_logger():
    """
    Получить настроенный логгер
    
    Returns:
        Logger instance из loguru
    """
    return logger


# Настраиваем логирование при импорте
setup_logging()


# Примеры использования в коде:
"""
from app.utils.logger import get_logger

logger = get_logger()

# Логирование с разными уровнями
logger.debug("Отладочное сообщение")
logger.info("Информация: подключение к COM3")
logger.warning("Предупреждение: порт не найден")
logger.error("Ошибка: не удалось подключиться")
logger.critical("Критическая ошибка: нехватка памяти")

# С контекстом
logger.info(f"Отправка команды: {command}")

# Перехват исключений
try:
    # код
except Exception as e:
    logger.exception("Ошибка при выполнении")
"""

