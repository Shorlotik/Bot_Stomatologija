"""
Клавиатуры главного меню и навигации.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт главное меню с выбором направления работы.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура главного меню
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🦷 Стоматология", callback_data="menu_dentistry")
        ],
        [
            InlineKeyboardButton(text="💊 Нутрициология", callback_data="menu_nutrition")
        ],
        [
            InlineKeyboardButton(text="📋 Контакты", callback_data="menu_contacts")
        ]
    ])
    return keyboard


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт кнопку возврата в главное меню.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
        ]
    ])
    return keyboard


def get_main_menu_with_history_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт главное меню с дополнительной кнопкой истории записей.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура главного меню с историей
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🦷 Стоматология", callback_data="menu_dentistry")
        ],
        [
            InlineKeyboardButton(text="💊 Нутрициология", callback_data="menu_nutrition")
        ],
        [
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ],
        [
            InlineKeyboardButton(text="📋 Контакты", callback_data="menu_contacts")
        ]
    ])
    return keyboard

