"""
Модуль для миграций базы данных.
"""
from database.db import init_db
from utils.logger import logger


def run_migrations():
    """
    Выполняет миграции базы данных (создание таблиц).
    """
    try:
        logger.info("Начало миграций базы данных...")
        init_db()
        logger.info("Миграции успешно выполнены")
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграций: {e}")
        raise


if __name__ == "__main__":
    run_migrations()

