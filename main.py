"""
Главная точка входа для Telegram-бота стоматолога и нутрициолога.
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config, Config
from database.db import init_db
from utils.logger import logger


async def main():
    """Основная функция запуска бота."""
    bot = None
    try:
        # Валидация конфигурации
        Config.validate()
        logger.info("Конфигурация успешно загружена")
        
        # Инициализация базы данных
        init_db()
        
        # Создание бота и диспетчера
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        dp = Dispatcher()
        
        # Регистрация handlers
        # Важно: common handlers регистрируются последними, чтобы не перехватывать FSM обработчики
        from handlers.start import register_start_handlers
        from handlers.dentistry import register_dentistry_handlers
        from handlers.nutrition import register_nutrition_handlers
        from handlers.booking import register_booking_handlers
        from handlers.admin import register_admin_handlers
        from handlers.common import register_common_handlers
        
        register_start_handlers(dp)
        register_dentistry_handlers(dp)
        register_nutrition_handlers(dp)
        register_booking_handlers(dp)  # FSM обработчики должны быть зарегистрированы раньше
        register_admin_handlers(dp)
        register_common_handlers(dp)  # Обработчик необработанных сообщений регистрируется последним
        
        logger.info("Бот запущен и готов к работе")
        
        # Запускаем фоновую задачу для напоминаний
        import asyncio
        from services.notifications import check_and_send_reminders
        
        async def reminder_task():
            """Фоновая задача для проверки и отправки напоминаний."""
            while True:
                try:
                    await asyncio.sleep(3600)  # Проверяем каждый час
                    await check_and_send_reminders(bot)
                except Exception as e:
                    logger.error(f"Ошибка в фоновой задаче напоминаний: {e}")
        
        # Запускаем задачу в фоне
        asyncio.create_task(reminder_task())
        
        # Запуск polling
        await dp.start_polling(bot)
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

