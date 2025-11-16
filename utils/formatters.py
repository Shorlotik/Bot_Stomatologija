"""
Модуль для форматирования сообщений бота.
Использует Markdown и эмодзи для красивого отображения.
"""
from typing import Optional


def format_bold(text: str) -> str:
    """Оборачивает текст в жирный шрифт Markdown."""
    return f"**{text}**"


def format_italic(text: str) -> str:
    """Оборачивает текст в курсив Markdown."""
    return f"_{text}_"


def format_list(items: list[str], numbered: bool = False) -> str:
    """Форматирует список элементов."""
    if numbered:
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    else:
        return "\n".join(f"• {item}" for item in items)


def format_appointment_info(
    full_name: str,
    appointment_date: str,
    service_type: str,
    phone: Optional[str] = None,
    comment: Optional[str] = None
) -> str:
    """Форматирует информацию о записи на приём."""
    text = f"📅 {format_bold('Запись на приём')}\n\n"
    text += f"👤 {format_bold('Клиент:')} {full_name}\n"
    if phone:
        text += f"📞 {format_bold('Телефон:')} {phone}\n"
    text += f"🕐 {format_bold('Дата и время:')} {appointment_date}\n"
    text += f"🦷 {format_bold('Тип услуги:')} {service_type}\n"
    if comment:
        text += f"\n📝 {format_bold('Комментарий:')}\n{comment}"
    
    return text


def format_schedule(
    schedule_dict: dict[str, str]
) -> str:
    """Форматирует расписание работы."""
    text = f"🕐 {format_bold('Расписание работы')}\n\n"
    
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    for day in days_order:
        if day in schedule_dict:
            text += f"• {day}: {schedule_dict[day]}\n"
    
    return text


def format_contact_info() -> str:
    """Форматирует контактную информацию врача."""
    text = f"📋 {format_bold('Контактная информация')}\n\n"
    text += f"👩‍⚕️ {format_bold('Врач:')} Прокопчик Людмила Николаевна\n"
    text += f"💼 {format_bold('Специализация:')} Стоматолог, Биолог, Нутрициолог\n"
    text += f"📞 {format_bold('Телефон:')} +375333647345\n"
    text += f"📧 {format_bold('Email:')} tgstamotolognsp@gmail.com\n"
    text += f"📍 {format_bold('Адрес:')} г. Пружаны, ул. Юбилейная 12а-2\n"
    text += f"\n✨ {format_italic('Ваша улыбка - моя работа')}"
    
    return text


def format_order_info(
    full_name: str,
    phone: str,
    products: str,
    comment: Optional[str] = None
) -> str:
    """Форматирует информацию о заказе БАДов."""
    text = f"💊 {format_bold('Заказ БАДов NSP')}\n\n"
    text += f"👤 {format_bold('Клиент:')} {full_name}\n"
    text += f"📞 {format_bold('Телефон:')} {phone}\n"
    text += f"📦 {format_bold('Желаемые продукты:')}\n{products}\n"
    if comment:
        text += f"\n📝 {format_bold('Комментарий:')}\n{comment}"
    
    return text


def format_welcome_message() -> str:
    """Форматирует приветственное сообщение."""
    text = f"👋 {format_bold('Добро пожаловать!')}\n\n"
    text += "Я бот для записи на приём к Прокопчик Людмиле Николаевне.\n\n"
    text += "Вы можете:\n"
    text += "• 🦷 Записаться на стоматологические услуги\n"
    text += "• 💊 Получить консультацию нутрициолога\n"
    text += "• 🔬 Записаться на сеанс БРТ\n"
    text += "• 📦 Заказать БАДы NSP\n\n"
    text += "Выберите направление:"
    
    return text


def format_success_message(message: str) -> str:
    """Добавляет эмодзи успеха к сообщению."""
    return f"✅ {message}"


def format_error_message(message: str) -> str:
    """Добавляет эмодзи ошибки к сообщению."""
    return f"❌ {message}"


def format_info_message(message: str) -> str:
    """Добавляет эмодзи информации к сообщению."""
    return f"ℹ️ {message}"


def format_warning_message(message: str) -> str:
    """Добавляет эмодзи предупреждения к сообщению."""
    return f"⚠️ {message}"

