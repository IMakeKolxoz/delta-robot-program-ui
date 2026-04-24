import sys
import signal
import tkinter as tk

from app.ui.main_window_tk import MainWindowTk
from app.utils.logger import get_logger

logger = get_logger()


def setup_signal_handlers(root: tk.Tk):
    """Настроить обработчики сигналов для graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        root.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Главная функция"""
    logger.info("=" * 50)
    logger.info("Запуск приложения Delta Robot - G-code Sender")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 50)
    
    try:
        root = tk.Tk()
        
        # Настраиваем обработчики сигналов
        setup_signal_handlers(root)
        
        # Создаем главное окно
        logger.info("Создание главного окна...")
        MainWindowTk(root)
        
        logger.info("Приложение готово к работе")
        logger.info("Нажмите Ctrl+C для выхода")
        
        # Запускаем цикл обработки событий
        root.mainloop()
        exit_code = 0
        
        logger.info(f"Завершение работы приложения (код: {exit_code})")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Прервано пользователем (Ctrl+C)")
        return 0
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

