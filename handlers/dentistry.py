"""
Обработчики модуля стоматологии.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.main import get_back_to_main_keyboard
from keyboards.booking import get_calendar_keyboard
from utils.formatters import format_schedule, format_info_message
from utils.logger import logger

router = Router()

# Расписание работы стоматолога
DENTISTRY_SCHEDULE = {
    "Понедельник": "выходной",
    "Вторник": "10:00 - 18:00",
    "Среда": "10:00 - 18:00",
    "Четверг": "13:00 - 19:00",
    "Пятница": "13:00 - 19:00",
    "Суббота": "9:00 - 15:00",
    "Воскресенье": "выходной"
}

# Список стоматологических услуг (можно расширить)
DENTISTRY_SERVICES = [
    "Консультация",
    "Лечение кариеса",
    "Лечение пульпита",
    "Профессиональная чистка зубов",
    "Отбеливание зубов",
    "Протезирование",
    "Имплантация",
    "Другое"
]


@router.callback_query(F.data == "menu_dentistry")
async def callback_menu_dentistry(callback: CallbackQuery):
    """Обработчик входа в раздел стоматологии."""
    try:
        text = "🦷 **Раздел стоматологии**\n\nВыберите действие:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться на приём", callback_data="dentistry_book")
            ],
            [
                InlineKeyboardButton(text="📋 Услуги", callback_data="dentistry_services"),
                InlineKeyboardButton(text="🕐 Расписание", callback_data="dentistry_schedule")
            ],
            [
                InlineKeyboardButton(text="📞 Контакты", callback_data="dentistry_contacts")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике menu_dentistry: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "dentistry_schedule")
async def callback_dentistry_schedule(callback: CallbackQuery):
    """Обработчик просмотра расписания стоматолога."""
    try:
        schedule_text = format_schedule(DENTISTRY_SCHEDULE)
        keyboard = get_back_to_main_keyboard()
        
        await callback.message.edit_text(
            schedule_text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике dentistry_schedule: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "dentistry_services")
async def callback_dentistry_services(callback: CallbackQuery):
    """Обработчик просмотра услуг стоматологии."""
    try:
        text = "🦷 **Стоматологические услуги:**\n\n"
        text += "\n".join(f"• {service}" for service in DENTISTRY_SERVICES)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться", callback_data="dentistry_book")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_dentistry")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике dentistry_services: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "dentistry_contacts")
async def callback_dentistry_contacts(callback: CallbackQuery):
    """Обработчик контактов в разделе стоматологии."""
    try:
        from utils.formatters import format_contact_info
        
        contact_text = format_contact_info()
        keyboard = get_back_to_main_keyboard()
        
        await callback.message.edit_text(
            contact_text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике dentistry_contacts: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# Обработчик dentistry_book перенесен в handlers/booking.py
# чтобы обеспечить правильный порядок шагов (имя -> телефон -> дата -> время -> услуга)


def register_dentistry_handlers(dp):
    """Регистрирует обработчики модуля стоматологии."""
    dp.include_router(router)

