"""
SQLAlchemy модели для базы данных.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class AppointmentStatus(enum.Enum):
    """Статусы записей на приём."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OrderStatus(enum.Enum):
    """Статусы обработки заказов БАДов."""
    PENDING = "pending"
    PROCESSED = "processed"


class VacationType(enum.Enum):
    """Типы периодов отсутствия."""
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    appointments = relationship("Appointment", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Appointment(Base):
    """Модель записи на приём."""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_user_id = Column(Integer, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    appointment_date = Column(DateTime, nullable=False, index=True)
    service_type = Column(String(255), nullable=False)
    service_duration = Column(Integer, nullable=False)  # в минутах
    comment = Column(String(1000), nullable=True)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.ACTIVE, nullable=False)
    google_calendar_event_id = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_doctor = Column(Boolean, default=False)
    
    # Связи
    user = relationship("User", back_populates="appointments")


class Order(Base):
    """Модель заказа БАДов NSP."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_user_id = Column(Integer, nullable=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    products_list = Column(String(2000), nullable=False)
    comment = Column(String(1000), nullable=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="orders")


class Holiday(Base):
    """Модель праздничных/выходных дней."""
    __tablename__ = "holidays"
    
    id = Column(Integer, primary_key=True)
    holiday_date = Column(DateTime, nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Vacation(Base):
    """Модель периодов отпуска и больничного."""
    __tablename__ = "vacations"
    
    id = Column(Integer, primary_key=True)
    vacation_type = Column(SQLEnum(VacationType), nullable=False)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduleChange(Base):
    """Модель изменений рабочего расписания."""
    __tablename__ = "schedule_changes"
    
    id = Column(Integer, primary_key=True)
    day_of_week = Column(Integer, nullable=False)  # 0=понедельник, 6=воскресенье
    start_time = Column(String(5), nullable=False)  # Формат HH:MM
    end_time = Column(String(5), nullable=False)  # Формат HH:MM
    effective_from = Column(DateTime, nullable=False, index=True)
    effective_to = Column(DateTime, nullable=True, index=True)  # NULL = бессрочно
    created_at = Column(DateTime, default=datetime.utcnow)

