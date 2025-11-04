"""
Модуль конфигурации для загрузки и валидации переменных окружения.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Config:
    """Класс для управления конфигурацией приложения."""
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Google Calendar API
    GOOGLE_CALENDAR_EMAIL: str = os.getenv("GOOGLE_CALENDAR_EMAIL", "tgstamotolognsp@gmail.com")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")
    
    # Admin Panel
    ADMIN_TELEGRAM_ID: Optional[int] = None
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    
    # Settings
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Minsk")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> None:
        """Проверяет наличие всех обязательных переменных окружения."""
        missing_vars = []
        
        if not cls.BOT_TOKEN:
            missing_vars.append("BOT_TOKEN")
        
        if not cls.GOOGLE_CLIENT_ID:
            missing_vars.append("GOOGLE_CLIENT_ID")
        
        if not cls.GOOGLE_CLIENT_SECRET:
            missing_vars.append("GOOGLE_CLIENT_SECRET")
        
        # GOOGLE_REFRESH_TOKEN теперь опционален - можно использовать token.json
        # Если нет токенов, бот будет работать без синхронизации с календарем
        
        if not cls.GOOGLE_CALENDAR_ID:
            missing_vars.append("GOOGLE_CALENDAR_ID")
        
        if missing_vars:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}. "
                f"Пожалуйста, проверьте файл .env или используйте .env.example как шаблон."
            )
        
        # Преобразуем ADMIN_TELEGRAM_ID в int, если указан
        admin_id = os.getenv("ADMIN_TELEGRAM_ID")
        if admin_id:
            try:
                cls.ADMIN_TELEGRAM_ID = int(admin_id)
            except ValueError:
                raise ValueError(f"ADMIN_TELEGRAM_ID должен быть числом, получено: {admin_id}")


# Создаём экземпляр конфигурации
config = Config()

