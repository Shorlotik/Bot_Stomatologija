"""
Общие обработчики (help, контакты, навигация).
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards.main import get_back_to_main_keyboard
from utils.formatters import format_contact_info, format_info_message
from utils.logger import logger

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    try:
        help_text = format_info_message(
            "Используйте меню бота для навигации.\n\n"
            "Доступные команды:\n"
            "/start - Главное меню\n"
            "/help - Справка\n"
            "/contacts - Контакты"
        )
        
        await message.answer(help_text)
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")


@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Обработчик команды /contacts."""
    try:
        contact_text = format_contact_info()
        keyboard = get_back_to_main_keyboard()
        
        await message.answer(
            contact_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка в обработчике /contacts: {e}")


@router.message(F.text)
async def handle_unhandled_message(message: Message):
    """Обработчик необработанных текстовых сообщений."""
    try:
        # Проверяем, не находится ли пользователь в процессе записи/заказа
        # Если да, то этот обработчик не должен срабатывать
        # (обработчики FSM имеют приоритет)
        
        help_text = format_info_message(
            "👋 Для работы с ботом используйте кнопки меню.\n\n"
            "Нажмите /start, чтобы открыть главное меню."
        )
        
        from keyboards.main import get_main_menu_keyboard
        keyboard = get_main_menu_keyboard()
        
        await message.answer(
            help_text,
            reply_markup=keyboard
        )
        logger.info(f"Пользователь {message.from_user.id} отправил необработанное сообщение: {message.text[:50]}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике необработанных сообщений: {e}")


def register_common_handlers(dp):
    """Регистрирует общие обработчики."""
    dp.include_router(router)

