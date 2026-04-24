import sys
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.utils.logger import get_logger

logger = get_logger()


def load_styles(app: QApplication):
    """Загрузить стили из QSS файла"""
    styles_path = Path("app/ui/styles.qss")
    if styles_path.exists():
        try:
            with open(styles_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            logger.info(f"Стили загружены: {styles_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки стилей: {e}")
    else:
        logger.warning(f"Файл стилей не найден: {styles_path}")


def setup_signal_handlers():
    """Настроить обработчики сигналов для graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        QApplication.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Главная функция"""
    logger.info("=" * 50)
    logger.info("Запуск приложения Delta Robot - G-code Sender")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Рабочая директория: {Path.cwd()}")
    logger.info("=" * 50)
    
    try:
        # Создаем приложение
        app = QApplication(sys.argv)
        app.setApplicationName("Delta Robot")
        app.setApplicationVersion("0.1.0")
        
        # Настраиваем обработчики сигналов
        setup_signal_handlers()
        
        # Загружаем стили
        load_styles(app)
        
        # Создаем главное окно
        logger.info("Создание главного окна...")
        window = MainWindow()
        window.show()
        
        logger.info("Приложение готово к работе")
        logger.info("Нажмите Ctrl+C для выхода")
        
        # Запускаем цикл обработки событий
        exit_code = app.exec()
        
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

