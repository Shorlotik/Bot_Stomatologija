"""
Модуль для отправки уведомлений пользователям.
"""
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Appointment, AppointmentStatus, Order, OrderStatus
from utils.formatters import (
    format_appointment_info, format_success_message, format_info_message,
    format_order_info
)
from utils.date_helpers import format_date, now
from utils.logger import logger
from config import config


async def send_appointment_confirmation(
    bot: Bot,
    telegram_user_id: int,
    appointment: Appointment
) -> bool:
    """
    Отправляет подтверждение записи клиенту.
    
    Args:
        bot: Экземпляр бота
        telegram_user_id: Telegram ID пользователя
        appointment: Объект записи
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        appointment_text = format_appointment_info(
            full_name=appointment.full_name,
            appointment_date=format_date(appointment.appointment_date, "full"),
            service_type=appointment.service_type,
            phone=appointment.phone,
            comment=appointment.comment if appointment.comment else None
        )
        
        text = format_success_message(
            f"Ваша запись успешно создана!\n\n{appointment_text}"
        )
        
        await bot.send_message(telegram_user_id, text)
        logger.info(f"Подтверждение записи отправлено пользователю {telegram_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке подтверждения записи: {e}")
        return False


async def send_appointment_reminder(
    bot: Bot,
    telegram_user_id: int,
    appointment: Appointment
) -> bool:
    """
    Отправляет напоминание о записи за день до приёма.
    
    Args:
        bot: Экземпляр бота
        telegram_user_id: Telegram ID пользователя
        appointment: Объект записи
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        text = format_info_message(
            f"Напоминание: у вас запись на завтра!\n\n"
            f"📅 Дата: {format_date(appointment.appointment_date, 'full')}\n"
            f"🦷 Услуга: {appointment.service_type}\n"
            f"📞 Телефон для связи: {appointment.phone}"
        )
        
        await bot.send_message(telegram_user_id, text)
        logger.info(f"Напоминание отправлено пользователю {telegram_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")
        return False


async def send_appointment_cancellation(
    bot: Bot,
    telegram_user_id: int,
    appointment: Appointment,
    reason: Optional[str] = None
) -> bool:
    """
    Отправляет уведомление об отмене записи.
    
    Args:
        bot: Экземпляр бота
        telegram_user_id: Telegram ID пользователя
        appointment: Объект записи
        reason: Причина отмены (опционально)
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        text = "❌ **Ваша запись отменена**\n\n"
        text += f"📅 Дата: {format_date(appointment.appointment_date, 'full')}\n"
        text += f"🦷 Услуга: {appointment.service_type}\n"
        
        if reason:
            text += f"\nПричина: {reason}"
        
        await bot.send_message(telegram_user_id, text)
        logger.info(f"Уведомление об отмене отправлено пользователю {telegram_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об отмене: {e}")
        return False


async def send_appointment_change(
    bot: Bot,
    telegram_user_id: int,
    appointment: Appointment,
    old_date: Optional[datetime] = None
) -> bool:
    """
    Отправляет уведомление об изменении записи.
    
    Args:
        bot: Экземпляр бота
        telegram_user_id: Telegram ID пользователя
        appointment: Объект записи
        old_date: Старая дата (опционально)
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        text = "ℹ️ **Ваша запись изменена**\n\n"
        
        if old_date:
            text += f"📅 Было: {format_date(old_date, 'full')}\n"
        
        text += f"📅 Теперь: {format_date(appointment.appointment_date, 'full')}\n"
        text += f"🦷 Услуга: {appointment.service_type}"
        
        await bot.send_message(telegram_user_id, text)
        logger.info(f"Уведомление об изменении отправлено пользователю {telegram_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об изменении: {e}")
        return False


async def send_admin_notification(
    bot: Bot,
    message: str
) -> bool:
    """
    Отправляет уведомление администратору (врачу).
    
    Args:
        bot: Экземпляр бота
        message: Текст сообщения
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        if config.ADMIN_TELEGRAM_ID:
            await bot.send_message(config.ADMIN_TELEGRAM_ID, message)
            logger.info(f"Уведомление отправлено администратору {config.ADMIN_TELEGRAM_ID}")
            return True
        else:
            logger.warning("ADMIN_TELEGRAM_ID не настроен, уведомление не отправлено")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")
        return False


async def send_new_order_notification(
    bot: Bot,
    order: Order
) -> bool:
    """
    Отправляет уведомление врачу о новом заказе БАДов.
    
    Args:
        bot: Экземпляр бота
        order: Объект заказа
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        from utils.formatters import format_order_info
        
        order_text = format_order_info(
            full_name=order.full_name,
            phone=order.phone,
            products=order.products_list,
            comment=order.comment if order.comment else None
        )
        
        text = "📦 **Новый заказ БАДов NSP**\n\n" + order_text
        
        return await send_admin_notification(bot, text)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о новом заказе: {e}")
        return False


async def send_new_appointment_notification(
    bot: Bot,
    appointment: Appointment
) -> bool:
    """
    Отправляет уведомление врачу о новой записи.
    
    Args:
        bot: Экземпляр бота
        appointment: Объект записи
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        text = (
            "📅 **Новая запись на приём**\n\n"
            f"👤 Клиент: {appointment.full_name}\n"
            f"📞 Телефон: {appointment.phone}\n"
            f"📅 Дата: {format_date(appointment.appointment_date, 'full')}\n"
            f"🦷 Услуга: {appointment.service_type}"
        )
        
        if appointment.comment:
            text += f"\n📝 Комментарий: {appointment.comment}"
        
        return await send_admin_notification(bot, text)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о новой записи: {e}")
        return False


async def check_and_send_reminders(bot: Bot):
    """
    Проверяет записи на завтра и отправляет напоминания.
    Эта функция должна вызываться периодически (например, раз в день).
    
    Args:
        bot: Экземпляр бота
    """
    try:
        from utils.date_helpers import get_tomorrow
        
        tomorrow = get_tomorrow()
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999)
        
        db = next(get_db())
        
        # Находим активные записи на завтра
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= tomorrow_start,
            Appointment.appointment_date <= tomorrow_end,
            Appointment.status == AppointmentStatus.ACTIVE
        ).all()
        
        for appointment in appointments:
            if appointment.telegram_user_id:
                await send_appointment_reminder(bot, appointment.telegram_user_id, appointment)
        
        logger.info(f"Проверка напоминаний завершена, найдено {len(appointments)} записей на завтра")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке напоминаний: {e}")

