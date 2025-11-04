"""
Модуль для валидации данных.
"""
import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """
    Проверяет корректность номера телефона.
    Принимает номера в формате +375... или без +.
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        bool: True если номер корректен, False иначе
    """
    # Удаляем все пробелы, дефисы и скобки
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Паттерны для белорусских номеров
    patterns = [
        r'^\+375\d{9}$',  # +375291234567
        r'^375\d{9}$',    # 375291234567
        r'^80\d{9}$',     # 80291234567
    ]
    
    return any(re.match(pattern, phone_clean) for pattern in patterns)


def format_phone(phone: str) -> Optional[str]:
    """
    Форматирует номер телефона в стандартный вид +375XXXXXXXXX.
    
    Args:
        phone: Исходный номер телефона
        
    Returns:
        Optional[str]: Отформатированный номер или None если номер некорректен
    """
    if not validate_phone(phone):
        return None
    
    # Удаляем все пробелы, дефисы и скобки
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Преобразуем в формат +375XXXXXXXXX
    if phone_clean.startswith('80'):
        phone_clean = '+375' + phone_clean[2:]
    elif phone_clean.startswith('375'):
        phone_clean = '+' + phone_clean
    elif not phone_clean.startswith('+375'):
        return None
    
    return phone_clean


def validate_full_name(full_name: str) -> bool:
    """
    Проверяет корректность ФИО.
    Должно содержать минимум 2 слова (имя и фамилию).
    
    Args:
        full_name: ФИО для проверки
        
    Returns:
        bool: True если ФИО корректно, False иначе
    """
    if not full_name or not full_name.strip():
        return False
    
    words = full_name.strip().split()
    if len(words) < 2:
        return False
    
    # Проверяем, что каждое слово содержит только буквы и дефисы
    name_pattern = r'^[А-ЯЁа-яёA-Za-z\-\s]+$'
    return all(re.match(name_pattern, word) for word in words)


def get_phone_validation_error() -> str:
    """Возвращает сообщение об ошибке валидации телефона."""
    return (
        "❌ Некорректный номер телефона.\n\n"
        "Пожалуйста, введите номер в одном из форматов:\n"
        "• +375291234567\n"
        "• 375291234567\n"
        "• 80291234567"
    )


def get_name_validation_error() -> str:
    """Возвращает сообщение об ошибке валидации ФИО."""
    return (
        "❌ Некорректное ФИО.\n\n"
        "Пожалуйста, введите полное имя (минимум имя и фамилия).\n"
        "Например: Иванов Иван"
    )

