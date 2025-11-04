"""
Клавиатуры админ-панели.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from typing import Optional


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Создаёт главное меню админ-панели."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Управление записями", callback_data="admin_appointments")
        ],
        [
            InlineKeyboardButton(text="📦 Заказы БАДов", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton(text="📅 Расписание", callback_data="admin_schedule")
        ],
        [
            InlineKeyboardButton(text="📝 Праздничные дни", callback_data="admin_holidays")
        ],
        [
            InlineKeyboardButton(text="🏖️ Отпуск/Больничный", callback_data="admin_vacations")
        ],
        [
            InlineKeyboardButton(text="➕ Создать запись", callback_data="admin_create_appointment")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
        ]
    ])
    return keyboard


def get_appointments_list_keyboard(
    appointments: list,
    page: int = 0,
    per_page: int = 5
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру со списком записей."""
    keyboard_buttons = []
    
    # Кнопки для записей на текущей странице
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    for appointment in appointments[start_idx:end_idx]:
        date_str = appointment.appointment_date.strftime("%d.%m %H:%M")
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{date_str} - {appointment.full_name}",
                callback_data=f"admin_appointment_{appointment.id}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад", callback_data=f"admin_appointments_page_{page-1}"
        ))
    if end_idx < len(appointments):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️", callback_data=f"admin_appointments_page_{page+1}"
        ))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_appointment_actions_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру действий с записью."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_edit_appointment_{appointment_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_cancel_appointment_{appointment_id}")
        ],
        [
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"admin_complete_appointment_{appointment_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_appointments")
        ]
    ])
    return keyboard


def get_orders_list_keyboard(orders: list, page: int = 0) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру со списком заказов."""
    keyboard_buttons = []
    
    per_page = 5
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    for order in orders[start_idx:end_idx]:
        status_emoji = "✅" if order.status.value == "processed" else "⏳"
        date_str = order.created_at.strftime("%d.%m")
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {date_str} - {order.full_name}",
                callback_data=f"admin_order_{order.id}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад", callback_data=f"admin_orders_page_{page-1}"
        ))
    if end_idx < len(orders):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️", callback_data=f"admin_orders_page_{page+1}"
        ))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру действий с заказом."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отметить обработанным", callback_data=f"admin_process_order_{order_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_orders")
        ]
    ])
    return keyboard


def get_schedule_management_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру управления расписанием."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Изменить расписание", callback_data="admin_change_schedule")
        ],
        [
            InlineKeyboardButton(text="📋 Посмотреть расписание", callback_data="admin_view_schedule")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard


def get_holidays_management_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру управления праздничными днями."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить праздничный день", callback_data="admin_add_holiday")
        ],
        [
            InlineKeyboardButton(text="📋 Список праздников", callback_data="admin_list_holidays")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard


def get_vacations_management_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру управления отпуском и больничным."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏖️ Установить отпуск", callback_data="admin_set_vacation")
        ],
        [
            InlineKeyboardButton(text="🏥 Установить больничный", callback_data="admin_set_sick_leave")
        ],
        [
            InlineKeyboardButton(text="📋 Список периодов", callback_data="admin_list_vacations")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard


def get_confirm_keyboard(action: str, item_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру подтверждения действия."""
    callback_data = f"admin_confirm_{action}"
    if item_id:
        callback_data += f"_{item_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=callback_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")
        ]
    ])
    return keyboard

