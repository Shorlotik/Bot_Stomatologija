"""
Обработчики команды /start и главного меню.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards.main import get_main_menu_keyboard, get_back_to_main_keyboard
from utils.formatters import format_welcome_message, format_contact_info
from utils.logger import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    try:
        from keyboards.main import get_main_menu_with_history_keyboard
        
        welcome_text = format_welcome_message()
        keyboard = get_main_menu_with_history_keyboard()
        
        await message.answer(
            welcome_text,
            reply_markup=keyboard
        )
        logger.info(f"Пользователь {message.from_user.id} запустил бота")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery):
    """Обработчик возврата в главное меню."""
    try:
        from keyboards.main import get_main_menu_with_history_keyboard
        
        welcome_text = format_welcome_message()
        keyboard = get_main_menu_with_history_keyboard()
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике back_to_main: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "menu_contacts")
async def callback_menu_contacts(callback: CallbackQuery):
    """Обработчик просмотра контактов."""
    try:
        contact_text = format_contact_info()
        keyboard = get_back_to_main_keyboard()
        
        await callback.message.edit_text(
            contact_text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике menu_contacts: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


def register_start_handlers(dp):
    """Регистрирует обработчики команды /start."""
    dp.include_router(router)

