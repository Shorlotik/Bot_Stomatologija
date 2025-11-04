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


def register_common_handlers(dp):
    """Регистрирует общие обработчики."""
    dp.include_router(router)

