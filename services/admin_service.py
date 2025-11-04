"""
Сервис для бизнес-логики админ-панели.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import (
    Appointment, AppointmentStatus, Order, OrderStatus,
    Holiday, Vacation, VacationType, ScheduleChange
)
from services.calendar import get_calendar_service
from services.notifications import send_appointment_cancellation
from utils.logger import logger
from utils.schedule import get_schedule_for_day


def get_appointments_for_date(
    db: Session,
    date: datetime,
    status: Optional[AppointmentStatus] = None
) -> List[Appointment]:
    """
    Получает записи на указанную дату.
    
    Args:
        db: Сессия базы данных
        date: Дата для поиска
        status: Фильтр по статусу (опционально)
        
    Returns:
        List[Appointment]: Список записей
    """
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999)
    
    query = db.query(Appointment).filter(
        Appointment.appointment_date >= date_start,
        Appointment.appointment_date <= date_end
    )
    
    if status:
        query = query.filter(Appointment.status == status)
    
    return query.order_by(Appointment.appointment_date.asc()).all()


def get_conflicting_appointments_for_schedule_change(
    db: Session,
    day_of_week: int,
    new_start_time: str,
    new_end_time: str
) -> List[Appointment]:
    """
    Находит записи, которые конфликтуют с новым расписанием.
    
    Args:
        db: Сессия базы данных
        day_of_week: День недели (0-6)
        new_start_time: Новое время начала (HH:MM)
        new_end_time: Новое время окончания (HH:MM)
        
    Returns:
        List[Appointment]: Список конфликтующих записей
    """
    # Получаем все активные записи на будущие даты
    today = datetime.now()
    appointments = db.query(Appointment).filter(
        Appointment.appointment_date >= today,
        Appointment.status == AppointmentStatus.ACTIVE
    ).all()
    
    conflicting = []
    new_start_hour, new_start_minute = map(int, new_start_time.split(':'))
    new_end_hour, new_end_minute = map(int, new_end_time.split(':'))
    new_start_total = new_start_hour * 60 + new_start_minute
    new_end_total = new_end_hour * 60 + new_end_minute
    
    for appointment in appointments:
        if appointment.appointment_date.weekday() == day_of_week:
            appt_hour = appointment.appointment_date.hour
            appt_minute = appointment.appointment_date.minute
            appt_total = appt_hour * 60 + appt_minute
            
            # Проверяем, попадает ли запись в новое расписание
            if not (new_start_total <= appt_total < new_end_total):
                conflicting.append(appointment)
    
    return conflicting


def process_vacation_conflicts(
    db: Session,
    vacation: Vacation,
    bot: Optional[object] = None
) -> int:
    """
    Обрабатывает конфликтующие записи при установке отпуска/больничного.
    
    Args:
        db: Сессия базы данных
        vacation: Период отпуска/больничного
        bot: Экземпляр бота для отправки уведомлений (опционально)
        
    Returns:
        int: Количество отменённых записей
    """
    try:
        # Находим конфликтующие записи
        conflicting = db.query(Appointment).filter(
            Appointment.appointment_date >= vacation.start_date,
            Appointment.appointment_date <= vacation.end_date,
            Appointment.status == AppointmentStatus.ACTIVE
        ).all()
        
        calendar_service = get_calendar_service()
        cancelled_count = 0
        
        reason = "Отпуск врача" if vacation.vacation_type == VacationType.VACATION else "Больничный врача"
        
        for appointment in conflicting:
            appointment.status = AppointmentStatus.CANCELLED
            
            # Удаляем из календаря
            if appointment.google_calendar_event_id:
                try:
                    calendar_service.delete_event(appointment.google_calendar_event_id)
                except Exception as e:
                    logger.error(f"Ошибка при удалении события: {e}")
            
            # Отправляем уведомление клиенту
            # Примечание: bot должен быть передан и быть async-совместимым
            # В реальном использовании вызывается из async-контекста
            if appointment.telegram_user_id and bot:
                try:
                    import asyncio
                    if asyncio.iscoroutinefunction(send_appointment_cancellation):
                        # Если вызывается из async контекста, используем await
                        pass  # Обработка будет в handlers/admin.py
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления: {e}")
            
            cancelled_count += 1
        
        db.commit()
        logger.info(f"Обработано {cancelled_count} конфликтующих записей для отпуска/больничного")
        
        return cancelled_count
        
    except Exception as e:
        logger.error(f"Ошибка при обработке конфликтов отпуска: {e}")
        db.rollback()
        return 0


def get_current_schedule_for_day(
    db: Session,
    day_of_week: int
) -> Optional[tuple[str, str]]:
    """
    Получает текущее расписание для дня недели.
    
    Args:
        db: Сессия базы данных
        day_of_week: День недели (0-6)
        
    Returns:
        Optional[tuple[str, str]]: Кортеж (время_начала, время_окончания) или None
    """
    from datetime import datetime
    today = datetime.now()
    
    # Получаем расписание через утилиту
    return get_schedule_for_day(db, today, False)

