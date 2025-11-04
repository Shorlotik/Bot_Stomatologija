"""
Сервис для бизнес-логики работы с записями на приём.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from database.models import Appointment, AppointmentStatus, User
from services.calendar import get_calendar_service
from services.notifications import send_appointment_change, send_appointment_cancellation
from utils.logger import logger
from utils.schedule import is_time_slot_available, check_appointment_limit


def create_appointment(
    db: Session,
    telegram_user_id: Optional[int],
    full_name: str,
    phone: str,
    appointment_datetime: datetime,
    service_type: str,
    service_duration: int,
    comment: Optional[str] = None,
    created_by_doctor: bool = False
) -> Optional[Appointment]:
    """
    Создаёт запись на приём.
    
    Args:
        db: Сессия базы данных
        telegram_user_id: Telegram ID пользователя (может быть None)
        full_name: ФИО клиента
        phone: Номер телефона
        appointment_datetime: Дата и время записи
        service_type: Тип услуги
        service_duration: Продолжительность в минутах
        comment: Комментарий (опционально)
        created_by_doctor: True если создано врачом
        
    Returns:
        Optional[Appointment]: Созданная запись или None в случае ошибки
    """
    try:
        # Проверяем лимит (только для клиентов с Telegram)
        if telegram_user_id and not created_by_doctor:
            if not check_appointment_limit(db, telegram_user_id):
                logger.warning(f"Пользователь {telegram_user_id} уже имеет активную запись")
                return None
        
        # Проверяем доступность времени
        time_str = appointment_datetime.strftime("%H:%M")
        if not is_time_slot_available(db, appointment_datetime, time_str, service_duration):
            logger.warning(f"Время {time_str} на {appointment_datetime.date()} недоступно")
            return None
        
        # Создаём или находим пользователя
        user = None
        if telegram_user_id:
            user = db.query(User).filter(User.telegram_id == telegram_user_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_user_id,
                    full_name=full_name,
                    phone=phone
                )
                db.add(user)
                db.flush()
            else:
                user.full_name = full_name
                user.phone = phone
        
        # Создаём запись
        appointment = Appointment(
            user_id=user.id if user else None,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            phone=phone,
            appointment_date=appointment_datetime,
            service_type=service_type,
            service_duration=service_duration,
            comment=comment,
            status=AppointmentStatus.ACTIVE,
            created_by_doctor=created_by_doctor
        )
        
        db.add(appointment)
        db.flush()
        
        # Создаём событие в календаре
        try:
            from datetime import timedelta
            calendar_service = get_calendar_service()
            end_datetime = appointment_datetime + timedelta(minutes=service_duration)
            
            event_description = (
                f"Клиент: {full_name}\n"
                f"Телефон: {phone}\n"
                f"Услуга: {service_type}"
            )
            if comment:
                event_description += f"\nКомментарий: {comment}"
            if created_by_doctor:
                event_description += "\nСоздано врачом"
            
            event_id = calendar_service.create_event(
                summary=f"{service_type} - {full_name}",
                start_datetime=appointment_datetime,
                end_datetime=end_datetime,
                description=event_description
            )
            
            if event_id:
                appointment.google_calendar_event_id = event_id
        except Exception as e:
            logger.error(f"Ошибка при создании события в календаре: {e}")
        
        db.commit()
        logger.info(f"Запись создана: ID {appointment.id}")
        
        return appointment
        
    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        db.rollback()
        return None


def update_appointment(
    db: Session,
    appointment_id: int,
    new_datetime: Optional[datetime] = None,
    new_service_type: Optional[str] = None,
    new_service_duration: Optional[int] = None,
    new_status: Optional[AppointmentStatus] = None
) -> bool:
    """
    Обновляет запись на приём.
    
    Args:
        db: Сессия базы данных
        appointment_id: ID записи
        new_datetime: Новое дата и время (опционально)
        new_service_type: Новый тип услуги (опционально)
        new_service_duration: Новая продолжительность (опционально)
        new_status: Новый статус (опционально)
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            return False
        
        old_datetime = appointment.appointment_date
        
        # Обновляем поля
        if new_datetime:
            appointment.appointment_date = new_datetime
        if new_service_type:
            appointment.service_type = new_service_type
        if new_service_duration:
            appointment.service_duration = new_service_duration
        if new_status:
            appointment.status = new_status
        
        # Обновляем событие в календаре
        if appointment.google_calendar_event_id and (new_datetime or new_service_duration):
            try:
                from datetime import timedelta
                calendar_service = get_calendar_service()
                
                end_datetime = appointment.appointment_date + timedelta(
                    minutes=appointment.service_duration
                )
                
                calendar_service.update_event(
                    appointment.google_calendar_event_id,
                    summary=f"{appointment.service_type} - {appointment.full_name}",
                    start_datetime=appointment.appointment_date,
                    end_datetime=end_datetime,
                    description=(
                        f"Клиент: {appointment.full_name}\n"
                        f"Телефон: {appointment.phone}\n"
                        f"Услуга: {appointment.service_type}"
                    )
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении события в календаре: {e}")
        
        db.commit()
        logger.info(f"Запись обновлена: ID {appointment_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении записи: {e}")
        db.rollback()
        return False


def cancel_appointment(
    db: Session,
    appointment_id: int,
    cancelled_by_doctor: bool = False
) -> bool:
    """
    Отменяет запись на приём.
    
    Args:
        db: Сессия базы данных
        appointment_id: ID записи
        cancelled_by_doctor: True если отменено врачом
        
    Returns:
        bool: True если успешно, False иначе
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            return False
        
        if appointment.status != AppointmentStatus.ACTIVE:
            return False
        
        appointment.status = AppointmentStatus.CANCELLED
        
        # Удаляем событие из календаря
        if appointment.google_calendar_event_id:
            try:
                calendar_service = get_calendar_service()
                calendar_service.delete_event(appointment.google_calendar_event_id)
            except Exception as e:
                logger.error(f"Ошибка при удалении события из календаря: {e}")
        
        db.commit()
        logger.info(f"Запись отменена: ID {appointment_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отмене записи: {e}")
        db.rollback()
        return False

