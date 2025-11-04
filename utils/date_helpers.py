"""
Модуль для работы с датами и временем.
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz

from config import config


def get_timezone():
    """Возвращает объект часового пояса из конфигурации."""
    try:
        return pytz.timezone(config.TIMEZONE)
    except pytz.exceptions.UnknownTimeZoneError:
        # Если часовой пояс не распознан, используем UTC+3 (Беларусь)
        return pytz.timezone('Europe/Minsk')


def now() -> datetime:
    """Возвращает текущее время с учётом часового пояса."""
    return datetime.now(get_timezone())


def format_date(date: datetime, format_type: str = "full") -> str:
    """
    Форматирует дату для отображения.
    
    Args:
        date: Дата для форматирования
        format_type: Тип формата ("full", "short", "date_only")
        
    Returns:
        str: Отформатированная дата
    """
    tz = get_timezone()
    
    # Если дата не имеет timezone, добавляем его
    if date.tzinfo is None:
        date = tz.localize(date)
    else:
        date = date.astimezone(tz)
    
    if format_type == "full":
        # Полный формат: "15 января 2024, 14:30"
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return f"{date.day} {months[date.month - 1]} {date.year}, {date.strftime('%H:%M')}"
    
    elif format_type == "short":
        # Короткий формат: "15.01.2024 14:30"
        return date.strftime("%d.%m.%Y %H:%M")
    
    elif format_type == "date_only":
        # Только дата: "15 января 2024"
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return f"{date.day} {months[date.month - 1]} {date.year}"
    
    else:
        return date.strftime("%d.%m.%Y %H:%M")


def get_tomorrow() -> datetime:
    """Возвращает дату завтрашнего дня в полночь."""
    tz = get_timezone()
    tomorrow = now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return tomorrow


def get_date_range_days(start_date: datetime, end_date: datetime) -> list[datetime]:
    """
    Возвращает список всех дат в диапазоне.
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
        
    Returns:
        list[datetime]: Список дат в диапазоне
    """
    dates = []
    current = start_date
    
    tz = get_timezone()
    if current.tzinfo is None:
        current = tz.localize(current)
    if end_date.tzinfo is None:
        end_date = tz.localize(end_date)
    
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    return dates


def is_workday(date: datetime, day_of_week: Optional[int] = None) -> bool:
    """
    Проверяет, является ли дата рабочим днём (не воскресенье).
    
    Args:
        date: Дата для проверки
        day_of_week: День недели (0=понедельник, 6=воскресенье), если None берётся из date
        
    Returns:
        bool: True если рабочий день, False иначе
    """
    if day_of_week is None:
        day_of_week = date.weekday()
    
    # Воскресенье = 6
    return day_of_week != 6

