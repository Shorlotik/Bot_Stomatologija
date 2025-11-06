"""
Клавиатуры для процесса записи на приём.
"""
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

from utils.date_helpers import now, get_timezone


def get_calendar_keyboard(selected_date: datetime = None, month_offset: int = 0) -> InlineKeyboardMarkup:
    """
    Создаёт календарную клавиатуру для выбора даты.
    
    Args:
        selected_date: Текущая выбранная дата (если есть)
        month_offset: Смещение месяца (0 = текущий месяц)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура календаря
    """
    tz = get_timezone()
    today = now()
    
    # Вычисляем дату начала месяца с учётом смещения
    target_date = (today + timedelta(days=32 * month_offset)).replace(day=1)
    year = target_date.year
    month = target_date.month
    
    # Первый день месяца
    first_day = target_date.replace(day=1)
    # Последний день месяца
    if month == 12:
        last_day = target_date.replace(year=year+1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = target_date.replace(month=month+1, day=1) - timedelta(days=1)
    
    # День недели первого дня (0=понедельник, 6=воскресенье)
    start_weekday = first_day.weekday()
    
    # Создаём сетку календаря
    keyboard = []
    
    # Заголовок с месяцем и годом
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    header_buttons = []
    if month_offset > 0:
        header_buttons.append(InlineKeyboardButton(
            text="◀️", callback_data=f"calendar_prev_{month_offset-1}"
        ))
    header_buttons.append(InlineKeyboardButton(
        text=f"{month_names[month-1]} {year}",
        callback_data="calendar_info"
    ))
    if month_offset < 2:  # Показываем только на 2 месяца вперёд
        header_buttons.append(InlineKeyboardButton(
            text="▶️", callback_data=f"calendar_next_{month_offset+1}"
        ))
    keyboard.append(header_buttons)
    
    # Дни недели
    keyboard.append([
        InlineKeyboardButton(text="Пн", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Вт", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Ср", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Чт", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Пт", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Сб", callback_data="calendar_day_label"),
        InlineKeyboardButton(text="Вс", callback_data="calendar_day_label"),
    ])
    
    # Дни месяца
    current_date = first_day - timedelta(days=start_weekday)
    weeks = []
    week = []
    
    while current_date <= last_day or len(week) < 7:
        if len(week) == 7:
            weeks.append(week)
            week = []
        
        if current_date < first_day:
            # Пустая клетка до начала месяца
            week.append(InlineKeyboardButton(text=" ", callback_data="calendar_empty"))
        elif current_date > last_day:
            # Пустая клетка после конца месяца
            week.append(InlineKeyboardButton(text=" ", callback_data="calendar_empty"))
        else:
            # Дата в месяце
            day = current_date.day
            is_today = current_date.date() == today.date()
            is_past = current_date.date() < today.date()
            
            prefix = "•" if is_today else ""
            
            if is_past:
                # Прошедшие даты неактивны
                week.append(InlineKeyboardButton(
                    text=f"{prefix}{day}" if prefix else str(day),
                    callback_data="calendar_past"
                ))
            else:
                # Будущие даты кликабельны
                date_str = current_date.strftime("%Y-%m-%d")
                week.append(InlineKeyboardButton(
                    text=f"{prefix}{day}" if prefix else str(day),
                    callback_data=f"calendar_select_{date_str}"
                ))
        
        current_date += timedelta(days=1)
    
    if week:
        while len(week) < 7:
            week.append(InlineKeyboardButton(text=" ", callback_data="calendar_empty"))
        weeks.append(week)
    
    keyboard.extend(weeks)
    
    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="booking_back_to_phone"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_time_slots_keyboard(time_slots: List[str], selected_time: str = None) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с временными слотами.
    
    Args:
        time_slots: Список доступных временных слотов в формате "HH:MM"
        selected_time: Выбранное время (если есть)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с временными слотами
    """
    keyboard = []
    row = []
    
    for i, time_slot in enumerate(time_slots):
        # Группируем по 2 кнопки в ряд
        if i > 0 and i % 2 == 0:
            keyboard.append(row)
            row = []
        
        prefix = "✅ " if time_slot == selected_time else ""
        # Заменяем двоеточие на дефис для callback_data (Telegram не принимает двоеточие)
        time_callback = time_slot.replace(":", "-")
        row.append(InlineKeyboardButton(
            text=f"{prefix}{time_slot}",
            callback_data=f"time_select_{time_callback}"
        ))
    
    if row:
        keyboard.append(row)
    
    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="booking_back_to_date"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру подтверждения записи.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура подтверждения
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="booking_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="booking_back_to_time"),
            InlineKeyboardButton(text="✏️ Изменить данные", callback_data="booking_edit")
        ]
    ])
    return keyboard

