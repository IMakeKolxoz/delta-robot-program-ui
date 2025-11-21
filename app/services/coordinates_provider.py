"""
Провайдер координат дельта-робота
"""
from typing import Tuple, Optional
from abc import ABC, abstractmethod
import asyncio
from app.services.serial_manager import SerialManager
from app.utils.logger import get_logger

logger = get_logger()


class ICoordinatesProvider(ABC):
    """
    Интерфейс для получения координат дельта-робота
    
    Интерфейс-заглушка для провайдера координат.
    Реализация через SerialCoordinatesProvider использует ISerialPort (SerialManager)
    для запроса координат у контроллера через COM-порт.
    """
    
    @abstractmethod
    async def get_coordinates_async(self, ct=None) -> Tuple[float, float, float, float, float, float]:
        """
        Получить координаты робота (асинхронный метод)
        
        Args:
            ct: CancellationToken (опционально, для будущего использования)
        
        Returns:
            Кортеж (MachineX, MachineY, MachineZ, WorkX, WorkY, WorkZ)
            
        Raises:
            NotImplementedError: Если метод не реализован в производном классе
        """
        pass


class SerialCoordinatesProvider(ICoordinatesProvider):
    """
    Провайдер координат через COM-порт
    
    Реализация ICoordinatesProvider, использует SerialManager (ISerialPort)
    для запроса координат у контроллера через COM-порт.
    
    Зарегистрирован в MainWindow и передаётся в CoordinatesViewModel через DI.
    Пока реализован как заглушка, возвращающая нули.
    В будущем здесь будет реализован реальный запрос координат через COM-порт.
    """
    
    def __init__(self, serial_manager: SerialManager):
        """
        Инициализация провайдера
        
        Args:
            serial_manager: Менеджер COM-порта (ISerialPort, SerialManager)
        """
        self.serial_manager = serial_manager
    
    async def get_coordinates_async(self, ct=None) -> Tuple[float, float, float, float, float, float]:
        """
        Получить координаты через COM-порт (асинхронно)
        
        Args:
            ct: CancellationToken (опционально)
        
        Returns:
            Кортеж (MachineX, MachineY, MachineZ, WorkX, WorkY, WorkZ)
        """
        # TODO: вставить команду запроса координат
        # Пока возвращаем нули как заглушку
        logger.debug("Запрос координат (заглушка)")
        await asyncio.sleep(0)  # Неблокирующая задержка для async
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def get_coordinates(self) -> Tuple[float, float, float, float, float, float]:
        """
        Получить координаты (синхронный метод-заглушка для обратной совместимости)
        
        Returns:
            Кортеж (MachineX, MachineY, MachineZ, WorkX, WorkY, WorkZ)
        """
        # TODO: вставить команду запроса координат
        # Пока возвращаем нули как заглушку
        logger.debug("Запрос координат (заглушка, sync)")
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

