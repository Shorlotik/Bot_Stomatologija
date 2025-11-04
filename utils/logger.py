"""
Модуль для настройки логирования приложения.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from config import config

# Создаём директорию для логов, если её нет
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger() -> logging.Logger:
    """
    Настраивает и возвращает логгер приложения.
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger("stomatolog_bot")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    # Очищаем существующие handlers
    logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler для файла
    log_file = LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Создаём глобальный логгер
logger = setup_logger()

