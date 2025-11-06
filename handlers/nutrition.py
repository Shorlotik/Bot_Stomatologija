"""
Обработчики модуля нутрициологии.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.main import get_back_to_main_keyboard
# from keyboards.booking import get_calendar_keyboard  # Не используется, процесс записи в booking.py
from utils.formatters import format_info_message
from utils.logger import logger

router = Router()

# Услуги нутрициолога
NUTRITION_SERVICES = [
    "Консультация нутрициолога"
]

# Ссылка на сайт NSP
NSP_WEBSITE = "https://nsp.com"


@router.callback_query(F.data == "menu_nutrition")
async def callback_menu_nutrition(callback: CallbackQuery):
    """Обработчик входа в раздел нутрициологии."""
    try:
        text = "💊 **Раздел нутрициологии**\n\nВыберите действие:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться на консультацию", callback_data="nutrition_consultation")
            ],
            [
                InlineKeyboardButton(text="🔬 Записаться на БРТ", callback_data="nutrition_brt")
            ],
            [
                InlineKeyboardButton(text="📦 Заказать БАДы NSP", callback_data="nutrition_order_bads")
            ],
            [
                InlineKeyboardButton(text="💊 Услуги нутрициолога", callback_data="nutrition_services")
            ],
            [
                InlineKeyboardButton(text="🛒 Купить продукты NSP", callback_data="nutrition_buy_nsp")
            ],
            [
                InlineKeyboardButton(text="ℹ️ Информация о НПП", callback_data="nutrition_info")
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
        logger.error(f"Ошибка в обработчике menu_nutrition: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "nutrition_services")
async def callback_nutrition_services(callback: CallbackQuery):
    """Обработчик просмотра услуг нутрициолога."""
    try:
        text = "💊 **Услуги нутрициолога:**\n\n"
        text += "\n".join(f"• {service}" for service in NUTRITION_SERVICES)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться на консультацию", callback_data="nutrition_consultation"),
                InlineKeyboardButton(text="🔬 Записаться на БРТ", callback_data="nutrition_brt")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_nutrition")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике nutrition_services: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "nutrition_buy_nsp")
async def callback_nutrition_buy_nsp(callback: CallbackQuery):
    """Обработчик ссылки на покупку продуктов NSP."""
    try:
        text = (
            "🛒 **Купить продукты NSP**\n\n"
            f"Вы можете приобрести продукты NSP на официальном сайте:\n\n"
            f"🔗 {NSP_WEBSITE}\n\n"
            "Или заполните форму заказа через бота, и врач свяжется с вами."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Заказать через бота", callback_data="nutrition_order_bads")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_nutrition")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике nutrition_buy_nsp: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "nutrition_info")
async def callback_nutrition_info(callback: CallbackQuery):
    """Обработчик информации о НПП."""
    try:
        text = (
            "ℹ️ **Информация о НПП (Nature's Sunshine Products)**\n\n"
            "NSP — это компания, которая производит натуральные биологически активные добавки.\n\n"
            "Наша специалист поможет подобрать необходимые витамины и минералы "
            "для поддержания вашего здоровья."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Заказать БАДы", callback_data="nutrition_order_bads")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_nutrition")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике nutrition_info: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# Обработчик nutrition_consultation перенесен в handlers/booking.py
# для единообразного процесса записи (выбор услуги -> ФИО -> телефон -> дата -> время)


@router.callback_query(F.data == "nutrition_brt")
async def callback_nutrition_brt(callback: CallbackQuery):
    """Обработчик начала процесса записи на БРТ."""
    try:
        text = (
            "🔬 **Запись на сеанс БРТ**\n\n"
            "БРТ (Биорезонансная терапия) доступна только по понедельникам с 11:00 до 15:00.\n\n"
            "Продолжительность сеанса: 30 минут.\n\n"
            "Выберите дату (доступны только понедельники):"
        )
        keyboard = get_calendar_keyboard()
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
        # TODO: Здесь будет сохранение состояния для процесса записи на БРТ
    except Exception as e:
        logger.error(f"Ошибка в обработчике nutrition_brt: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "nutrition_order_bads")
async def callback_nutrition_order_bads(callback: CallbackQuery):
    """Обработчик начала процесса заказа БАДов."""
    try:
        text = (
            "📦 **Заказ БАДов NSP**\n\n"
            "Пожалуйста, введите ваши данные для заказа.\n\n"
            "Введите ФИО:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="menu_nutrition")
            ]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
        # TODO: Здесь будет сохранение состояния для процесса заказа
    except Exception as e:
        logger.error(f"Ошибка в обработчике nutrition_order_bads: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


def register_nutrition_handlers(dp):
    """Регистрирует обработчики модуля нутрициологии."""
    dp.include_router(router)

