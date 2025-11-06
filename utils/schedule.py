"""
Модуль для работы с расписанием и проверки доступности времени.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Appointment, AppointmentStatus, Holiday, Vacation, ScheduleChange, VacationType
from utils.date_helpers import now, get_timezone
from utils.logger import logger


# Базовое расписание работы стоматолога
BASE_SCHEDULE = {
    0: None,  # Понедельник - выходной
    1: ("13:00", "19:00"),  # Вторник
    2: ("13:00", "19:00"),  # Среда
    3: ("13:00", "19:00"),  # Четверг
    4: ("09:00", "15:00"),  # Пятница
    5: ("09:00", "15:00"),  # Суббота
    6: None,  # Воскресенье - выходной
}

# Расписание БРТ (только понедельник)
# Фиксированные времена для БРТ
BRT_TIME_SLOTS = ["13:00", "14:30", "16:00", "17:30"]
BRT_SCHEDULE = {
    0: ("13:00", "17:30"),  # Понедельник
}

# Продолжительность услуг в минутах (по умолчанию)
DEFAULT_SERVICE_DURATION = 60  # 1 час


def get_schedule_for_day(db: Session, date: datetime, is_brt: bool = False) -> Optional[tuple[str, str]]:
    """
    Получает расписание работы для конкретного дня с учётом изменений.
    
    Args:
        db: Сессия базы данных
        date: Дата для проверки
        is_brt: True если это запись на БРТ
        
    Returns:
        Optional[tuple[str, str]]: Кортеж (время_начала, время_окончания) или None если выходной
    """
    day_of_week = date.weekday()
    
    # Для БРТ - только понедельник
    if is_brt:
        if day_of_week != 0:  # Не понедельник
            return None
        return BRT_SCHEDULE.get(0)
    
    # Проверяем изменения расписания в БД
    schedule_change = db.query(ScheduleChange).filter(
        ScheduleChange.day_of_week == day_of_week,
        ScheduleChange.effective_from <= date,
        (ScheduleChange.effective_to.is_(None) | (ScheduleChange.effective_to >= date))
    ).order_by(ScheduleChange.effective_from.desc()).first()
    
    if schedule_change:
        return (schedule_change.start_time, schedule_change.end_time)
    
    # Используем базовое расписание
    return BASE_SCHEDULE.get(day_of_week)


def is_date_available(db: Session, date: datetime) -> bool:
    """
    Проверяет, доступна ли дата для записи (не праздник, не отпуск).
    
    Args:
        db: Сессия базы данных
        date: Дата для проверки
        
    Returns:
        bool: True если дата доступна, False иначе
    """
    date_only = date.date()
    
    # Проверка праздничных дней
    holiday = db.query(Holiday).filter(
        Holiday.holiday_date == date_only
    ).first()
    if holiday:
        return False
    
    # Проверка отпуска/больничного
    vacation = db.query(Vacation).filter(
        Vacation.start_date <= date,
        Vacation.end_date >= date
    ).first()
    if vacation:
        return False
    
    return True


def get_occupied_slots(
    db: Session,
    date: datetime,
    service_duration: int = DEFAULT_SERVICE_DURATION
) -> List[datetime]:
    """
    Получает список занятых временных слотов на дату.
    
    Args:
        db: Сессия базы данных
        date: Дата для проверки
        service_duration: Продолжительность услуги в минутах
        
    Returns:
        List[datetime]: Список занятых временных слотов
    """
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999)
    
    appointments = db.query(Appointment).filter(
        Appointment.appointment_date >= date_start,
        Appointment.appointment_date <= date_end,
        Appointment.status == AppointmentStatus.ACTIVE
    ).all()
    
    occupied = []
    for appointment in appointments:
        # Добавляем все временные слоты, занятые этой записью
        slot_start = appointment.appointment_date
        for i in range(appointment.service_duration // 30):  # Слоты по 30 минут
            occupied.append(slot_start + timedelta(minutes=i * 30))
    
    return occupied


def calculate_time_slots(
    db: Session,
    date: datetime,
    service_duration: int = DEFAULT_SERVICE_DURATION,
    is_brt: bool = False
) -> List[str]:
    """
    Рассчитывает доступные временные слоты для записи.
    
    Args:
        db: Сессия базы данных
        date: Дата для записи
        service_duration: Продолжительность услуги в минутах
        is_brt: True если это запись на БРТ
        
    Returns:
        List[str]: Список доступных временных слотов в формате "HH:MM"
    """
    # Проверяем доступность даты
    if not is_date_available(db, date):
        return []
    
    # Для БРТ используем фиксированные времена
    if is_brt:
        # Проверяем, что это понедельник
        if date.weekday() != 0:
            return []
        
        # Получаем занятые слоты
        occupied_slots = get_occupied_slots(db, date, service_duration)
        occupied_set = {slot for slot in occupied_slots}
        
        # Проверяем доступность фиксированных времен БРТ
        available_slots = []
        for time_str in BRT_TIME_SLOTS:
            hour, minute = map(int, time_str.split(':'))
            slot_time = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Проверяем, не занят ли этот слот
            slot_occupied = False
            check_time = slot_time
            while check_time < slot_time + timedelta(minutes=service_duration):
                if check_time in occupied_set:
                    slot_occupied = True
                    break
                check_time += timedelta(minutes=30)
            
            if not slot_occupied:
                available_slots.append(time_str)
        
        return available_slots
    
    # Получаем расписание для дня
    schedule = get_schedule_for_day(db, date, is_brt)
    if not schedule:
        return []
    
    start_time_str, end_time_str = schedule
    start_hour, start_minute = map(int, start_time_str.split(':'))
    end_hour, end_minute = map(int, end_time_str.split(':'))
    
    # Создаём начало и конец рабочего дня
    work_start = date.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    work_end = date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    
    # Получаем занятые слоты
    occupied_slots = get_occupied_slots(db, date, service_duration)
    occupied_set = {slot for slot in occupied_slots}
    
    # Генерируем доступные слоты (каждые 30 минут)
    available_slots = []
    current_time = work_start
    
    while current_time + timedelta(minutes=service_duration) <= work_end:
        # Проверяем, не пересекается ли слот с занятыми
        slot_occupied = False
        check_time = current_time
        while check_time < current_time + timedelta(minutes=service_duration):
            if check_time in occupied_set:
                slot_occupied = True
                break
            check_time += timedelta(minutes=30)
        
        if not slot_occupied:
            available_slots.append(current_time.strftime("%H:%M"))
        
        current_time += timedelta(minutes=30)
    
    return available_slots


def check_appointment_limit(db: Session, telegram_user_id: int) -> bool:
    """
    Проверяет, не превышен ли лимит записей для пользователя.
    Максимум 1 активная запись на одного клиента.
    
    Args:
        db: Сессия базы данных
        telegram_user_id: Telegram ID пользователя
        
    Returns:
        bool: True если можно создать новую запись, False если лимит превышен
    """
    active_count = db.query(Appointment).filter(
        Appointment.telegram_user_id == telegram_user_id,
        Appointment.status == AppointmentStatus.ACTIVE
    ).count()
    
    return active_count < 1


def is_time_slot_available(
    db: Session,
    date: datetime,
    time_str: str,
    service_duration: int = DEFAULT_SERVICE_DURATION
) -> bool:
    """
    Проверяет, доступен ли конкретный временной слот.
    
    Args:
        db: Сессия базы данных
        date: Дата записи
        time_str: Время в формате "HH:MM"
        service_duration: Продолжительность услуги в минутах
        
    Returns:
        bool: True если слот доступен, False иначе
    """
    hour, minute = map(int, time_str.split(':'))
    appointment_datetime = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Проверяем, есть ли пересечения с существующими записями
    occupied_slots = get_occupied_slots(db, date, service_duration)
    
    # Проверяем каждый слот, который займёт наша запись
    check_time = appointment_datetime
    end_time = appointment_datetime + timedelta(minutes=service_duration)
    
    while check_time < end_time:
        if check_time in occupied_slots:
            return False
        check_time += timedelta(minutes=30)
    
    return True

