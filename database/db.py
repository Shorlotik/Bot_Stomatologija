"""
Модуль для работы с базой данных.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import config
from utils.logger import logger

# Создаём движок базы данных
if config.DATABASE_URL.startswith("sqlite"):
    # Для SQLite используем специальные настройки
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # Для PostgreSQL и других БД
    engine = create_engine(
        config.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

# Создаём фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Создаёт и возвращает сессию базы данных.
    Используется как dependency для получения сессии в обработчиках.
    
    Yields:
        Session: Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализирует базу данных, создавая все таблицы.
    """
    from database.models import Base
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

