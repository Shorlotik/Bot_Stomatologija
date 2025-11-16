"""
Обработчики админ-панели.
"""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from config import config
from database.db import get_db
from database.models import (
    Appointment, AppointmentStatus, Order, OrderStatus,
    Holiday, Vacation, VacationType, ScheduleChange
)
from keyboards.admin import (
    get_admin_main_keyboard, get_appointments_list_keyboard,
    get_appointment_actions_keyboard, get_orders_list_keyboard,
    get_order_actions_keyboard, get_schedule_management_keyboard,
    get_holidays_management_keyboard, get_vacations_management_keyboard,
    get_confirm_keyboard
)
from keyboards.booking import get_calendar_keyboard
from utils.formatters import format_appointment_info, format_order_info, format_success_message
from utils.logger import logger
from utils.date_helpers import format_date
from services.calendar import get_calendar_service
from services.notifications import send_appointment_cancellation, send_appointment_change

router = Router()


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    waiting_for_password = State()
    waiting_for_holiday_date = State()
    waiting_for_vacation_start = State()
    waiting_for_vacation_end = State()
    waiting_for_schedule_day = State()
    waiting_for_schedule_start = State()
    waiting_for_schedule_end = State()
    # Создание записи врачом
    create_appointment_name = State()
    create_appointment_phone = State()
    create_appointment_date = State()
    create_appointment_time = State()
    create_appointment_service = State()
    create_appointment_comment = State()
    # Редактирование записи
    edit_appointment_date = State()
    edit_appointment_time = State()
    edit_appointment_service = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    # Список админов (можно расширить через переменную окружения)
    admin_ids = []
    
    # Добавляем админа из конфигурации, если указан
    if config.ADMIN_TELEGRAM_ID:
        admin_ids.append(config.ADMIN_TELEGRAM_ID)
    
    # Добавляем дополнительных админов
    admin_ids.append(1184718761)
    
    return user_id in admin_ids


@router.message(lambda message: message.text and message.text.startswith("/admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Обработчик команды /admin."""
    try:
        user_id = message.from_user.id
        
        # Проверяем доступ
        if is_admin(user_id):
            # Прямой доступ по Telegram ID
            await show_admin_menu(message, state)
        elif config.ADMIN_PASSWORD:
            # Запрашиваем пароль
            await state.set_state(AdminStates.waiting_for_password)
            await message.answer(
                "🔐 **Доступ к админ-панели**\n\nВведите пароль:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer("❌ Доступ запрещён")
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике /admin: {e}")


@router.message(AdminStates.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext):
    """Обработчик ввода пароля админа."""
    password = message.text.strip()
    
    if password == config.ADMIN_PASSWORD:
        await state.clear()
        await show_admin_menu(message, state)
    else:
        await message.answer(
            "❌ Неверный пароль. Попробуйте ещё раз или отмените.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
            ])
        )


async def show_admin_menu(message_or_callback, state: FSMContext = None):
    """Показывает главное меню админ-панели."""
    try:
        text = "🔐 **Админ-панель**\n\nВыберите действие:"
        keyboard = get_admin_main_keyboard()
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)
            await message_or_callback.answer()
            
    except Exception as e:
        logger.error(f"Ошибка при показе админ-меню: {e}")


@router.callback_query(F.data == "admin_main")
async def callback_admin_main(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню админ-панели."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await show_admin_menu(callback, state)


@router.callback_query(F.data == "admin_appointments")
async def callback_admin_appointments(callback: CallbackQuery):
    """Обработчик просмотра списка записей."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        db = next(get_db())
        
        # Получаем все записи
        appointments = db.query(Appointment).order_by(
            Appointment.appointment_date.asc()
        ).all()
        
        if not appointments:
            text = "📅 Записей пока нет."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Формируем текст
        text = f"📅 **Управление записями**\n\nВсего записей: {len(appointments)}\n\n"
        text += "Выберите запись для просмотра:"
        
        keyboard = get_appointments_list_keyboard(appointments, page=0)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_appointments: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_appointment_"))
async def callback_admin_appointment_detail(callback: CallbackQuery):
    """Обработчик просмотра деталей записи."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        appointment_id = int(callback.data.split("_")[-1])
        db = next(get_db())
        
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        appointment_text = format_appointment_info(
            full_name=appointment.full_name,
            appointment_date=format_date(appointment.appointment_date, "full"),
            service_type=appointment.service_type,
            phone=appointment.phone,
            comment=appointment.comment if appointment.comment else None
        )
        
        status_text = {
            AppointmentStatus.ACTIVE: "✅ Активна",
            AppointmentStatus.CANCELLED: "❌ Отменена",
            AppointmentStatus.COMPLETED: "✓ Завершена"
        }.get(appointment.status, "❓ Неизвестно")
        
        text = f"{appointment_text}\n\nСтатус: {status_text}"
        keyboard = get_appointment_actions_keyboard(appointment_id)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_appointment_detail: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_cancel_appointment_"))
async def callback_admin_cancel_appointment(callback: CallbackQuery):
    """Обработчик отмены записи врачом."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        appointment_id = int(callback.data.split("_")[-1])
        db = next(get_db())
        
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        if appointment.status != AppointmentStatus.ACTIVE:
            await callback.answer("❌ Запись уже отменена или завершена", show_alert=True)
            return
        
        # Отменяем запись
        appointment.status = AppointmentStatus.CANCELLED
        db.commit()
        
        # Удаляем из календаря
        if appointment.google_calendar_event_id:
            try:
                calendar_service = get_calendar_service()
                calendar_service.delete_event(appointment.google_calendar_event_id)
            except Exception as e:
                logger.error(f"Ошибка при удалении события из календаря: {e}")
        
        # Отправляем уведомление клиенту
        if appointment.telegram_user_id:
            try:
                await send_appointment_cancellation(
                    callback.bot,
                    appointment.telegram_user_id,
                    appointment,
                    reason="Отменено врачом"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {e}")
        
        text = format_success_message("Запись успешно отменена!")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_appointments")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Запись отменена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_cancel_appointment: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_complete_appointment_"))
async def callback_admin_complete_appointment(callback: CallbackQuery):
    """Обработчик завершения записи."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        appointment_id = int(callback.data.split("_")[-1])
        db = next(get_db())
        
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        appointment.status = AppointmentStatus.COMPLETED
        db.commit()
        
        text = format_success_message("Запись отмечена как завершённая!")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_appointments")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Запись завершена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_complete_appointment: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_orders")
async def callback_admin_orders(callback: CallbackQuery):
    """Обработчик просмотра заказов БАДов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        db = next(get_db())
        
        orders = db.query(Order).order_by(Order.created_at.desc()).all()
        
        if not orders:
            text = "📦 Заказов пока нет."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        pending_count = sum(1 for o in orders if o.status == OrderStatus.PENDING)
        
        text = (
            f"📦 **Заказы БАДов NSP**\n\n"
            f"Всего заказов: {len(orders)}\n"
            f"Ожидают обработки: {pending_count}\n\n"
            f"Выберите заказ для просмотра:"
        )
        
        keyboard = get_orders_list_keyboard(orders, page=0)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_orders: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_order_"))
async def callback_admin_order_detail(callback: CallbackQuery):
    """Обработчик просмотра деталей заказа."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split("_")[-1])
        db = next(get_db())
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        order_text = format_order_info(
            full_name=order.full_name,
            phone=order.phone,
            products=order.products_list,
            comment=order.comment if order.comment else None
        )
        
        status_text = "✅ Обработан" if order.status == OrderStatus.PROCESSED else "⏳ Ожидает обработки"
        date_text = format_date(order.created_at, "full")
        
        text = f"{order_text}\n\nСтатус: {status_text}\nДата создания: {date_text}"
        keyboard = get_order_actions_keyboard(order_id)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_order_detail: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_process_order_"))
async def callback_admin_process_order(callback: CallbackQuery):
    """Обработчик отметки заказа как обработанного."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split("_")[-1])
        db = next(get_db())
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        order.status = OrderStatus.PROCESSED
        db.commit()
        
        text = format_success_message("Заказ отмечен как обработанный!")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_orders")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Заказ обработан", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_process_order: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_edit_appointment_"))
async def callback_admin_edit_appointment(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала редактирования записи."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        appointment_id = int(callback.data.split("_")[-1])
        await state.update_data(edit_appointment_id=appointment_id)
        await state.set_state(AdminStates.edit_appointment_date)
        
        text = "✏️ **Редактирование записи**\n\nВыберите новую дату:"
        keyboard = get_calendar_keyboard()
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_edit_appointment: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_create_appointment")
async def callback_admin_create_appointment(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала создания записи врачом."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        await state.set_state(AdminStates.create_appointment_name)
        
        text = "➕ **Создание записи врачом**\n\nВведите ФИО клиента:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_create_appointment: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.message(AdminStates.create_appointment_name)
async def process_create_appointment_name(message: Message, state: FSMContext):
    """Обработчик ввода ФИО при создании записи врачом."""
    from utils.validators import validate_full_name, get_name_validation_error
    
    full_name = message.text.strip()
    
    if not validate_full_name(full_name):
        await message.answer(
            get_name_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
            ])
        )
        return
    
    await state.update_data(create_full_name=full_name)
    await state.set_state(AdminStates.create_appointment_phone)
    
    await message.answer(
        "📞 Введите номер телефона клиента:\n\n"
        "Формат: +375291234567 или 80291234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
        ])
    )


@router.message(AdminStates.create_appointment_phone)
async def process_create_appointment_phone(message: Message, state: FSMContext):
    """Обработчик ввода телефона при создании записи врачом."""
    from utils.validators import validate_phone, format_phone, get_phone_validation_error
    
    phone = message.text.strip()
    
    if not validate_phone(phone):
        await message.answer(
            get_phone_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
            ])
        )
        return
    
    formatted_phone = format_phone(phone)
    await state.update_data(create_phone=formatted_phone)
    await state.set_state(AdminStates.create_appointment_date)
    
    await message.answer(
        "📅 Выберите дату:",
        reply_markup=get_calendar_keyboard()
    )


@router.callback_query(AdminStates.create_appointment_date, F.data.startswith("calendar_select_"))
async def callback_create_appointment_date(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора даты при создании записи врачом."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from utils.date_helpers import get_timezone
        from utils.schedule import calculate_time_slots, is_date_available
        from keyboards.booking import get_time_slots_keyboard
        
        date_str = callback.data.split("_")[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        tz = get_timezone()
        selected_date = tz.localize(selected_date)
        
        db = next(get_db())
        if not is_date_available(db, selected_date):
            await callback.answer("❌ Эта дата недоступна", show_alert=True)
            return
        
        await state.update_data(create_selected_date=selected_date)
        await state.set_state(AdminStates.create_appointment_time)
        
        # Рассчитываем доступные слоты
        time_slots = calculate_time_slots(db, selected_date, 60, False)
        
        if not time_slots:
            await callback.answer("❌ На эту дату нет свободных слотов", show_alert=True)
            return
        
        text = f"🕐 Выберите время:\n\n📅 Дата: {format_date(selected_date, 'date_only')}"
        keyboard = get_time_slots_keyboard(time_slots)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике create_appointment_date: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(AdminStates.create_appointment_time, F.data.startswith("time_select_"))
async def callback_create_appointment_time(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора времени при создании записи врачом."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from handlers.booking import SERVICE_DURATIONS
        
        # Парсим время из callback_data (формат: time_select_HH-MM или time_select_HH:MM)
        time_str = callback.data.replace("time_select_", "")
        # Заменяем дефис обратно на двоеточие (если был заменен)
        time_str = time_str.replace("-", ":")
        await state.update_data(create_selected_time=time_str)
        await state.set_state(AdminStates.create_appointment_service)
        
        from handlers.dentistry import DENTISTRY_SERVICES
        from handlers.nutrition import NUTRITION_SERVICES
        
        services = DENTISTRY_SERVICES + NUTRITION_SERVICES
        text = "💼 Выберите тип услуги:"
        
        # Создаём клавиатуру с услугами
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard_buttons = []
        for service in services:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=service,
                    callback_data=f"service_select_{service}"
                )
            ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике create_appointment_time: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(AdminStates.create_appointment_service, F.data.startswith("service_select_"))
async def callback_create_appointment_service(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора услуги при создании записи врачом."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from handlers.booking import SERVICE_DURATIONS
        
        service_type = callback.data.replace("service_select_", "")
        service_duration = SERVICE_DURATIONS.get(service_type, 60)
        
        await state.update_data(
            create_service_type=service_type,
            create_service_duration=service_duration
        )
        await state.set_state(AdminStates.create_appointment_comment)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="admin_skip_comment")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
        ])
        
        await callback.message.edit_text(
            "📝 Введите комментарий (или нажмите 'Пропустить'):",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике create_appointment_service: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.message(AdminStates.create_appointment_comment)
async def process_create_appointment_comment(message: Message, state: FSMContext):
    """Обработчик ввода комментария при создании записи врачом."""
    comment = message.text.strip()
    await state.update_data(create_comment=comment)
    
    # Сохраняем запись
    await save_admin_created_appointment(message, state)


@router.callback_query(F.data == "admin_skip_comment")
async def callback_admin_skip_comment(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска комментария."""
    await state.update_data(create_comment="")
    await save_admin_created_appointment(callback.message, state)
    await callback.answer()


async def save_admin_created_appointment(message_or_callback, state: FSMContext):
    """Сохраняет запись, созданную врачом."""
    try:
        data = await state.get_data()
        
        db = next(get_db())
        
        full_name = data.get("create_full_name")
        phone = data.get("create_phone")
        selected_date = data.get("create_selected_date")
        selected_time = data.get("create_selected_time")
        service_type = data.get("create_service_type")
        service_duration = data.get("create_service_duration", 60)
        comment = data.get("create_comment", "")
        
        # Формируем datetime
        hour, minute = map(int, selected_time.split(':'))
        appointment_datetime = selected_date.replace(hour=hour, minute=minute)
        
        # Создаём запись
        appointment = Appointment(
            user_id=None,  # Клиент без Telegram
            telegram_user_id=None,
            full_name=full_name,
            phone=phone,
            appointment_date=appointment_datetime,
            service_type=service_type,
            service_duration=service_duration,
            comment=comment if comment else None,
            status=AppointmentStatus.ACTIVE,
            created_by_doctor=True
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
                f"Услуга: {service_type}\n"
                f"Создано врачом"
            )
            if comment:
                event_description += f"\nКомментарий: {comment}"
            
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
        
        text = format_success_message(
            f"Запись успешно создана!\n\n"
            f"📅 Дата: {format_date(appointment_datetime, 'full')}\n"
            f"🦷 Услуга: {service_type}\n"
            f"👤 Клиент: {full_name}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_main")]
        ])
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.edit_text(text, reply_markup=keyboard)
            await message_or_callback.answer()
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении записи врачом: {e}")
        error_text = "❌ Произошла ошибка при создании записи."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_main")]
        ])
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(error_text, reply_markup=keyboard)
        else:
            await message_or_callback.edit_text(error_text, reply_markup=keyboard)
            await message_or_callback.answer()


@router.callback_query(F.data == "admin_holidays")
async def callback_admin_holidays(callback: CallbackQuery):
    """Обработчик управления праздничными днями."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    text = "📝 **Управление праздничными днями**\n\nВыберите действие:"
    keyboard = get_holidays_management_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_add_holiday")
async def callback_admin_add_holiday(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления праздничного дня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_holiday_date)
    
    text = "📅 **Добавление праздничного дня**\n\nВыберите дату:"
    keyboard = get_calendar_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminStates.waiting_for_holiday_date, F.data.startswith("calendar_select_"))
async def callback_holiday_date_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора даты для праздничного дня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from utils.date_helpers import get_timezone
        
        date_str = callback.data.split("_")[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        tz = get_timezone()
        selected_date = tz.localize(selected_date)
        
        db = next(get_db())
        
        # Проверяем, не существует ли уже
        existing = db.query(Holiday).filter(
            Holiday.holiday_date == selected_date.date()
        ).first()
        
        if existing:
            await callback.answer("❌ Этот день уже отмечен как праздничный", show_alert=True)
            return
        
        # Создаём праздничный день
        holiday = Holiday(holiday_date=selected_date)
        db.add(holiday)
        db.commit()
        
        text = format_success_message(
            f"Праздничный день добавлен: {format_date(selected_date, 'date_only')}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_holidays")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике holiday_date_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_list_holidays")
async def callback_admin_list_holidays(callback: CallbackQuery):
    """Обработчик просмотра списка праздничных дней."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        db = next(get_db())
        
        holidays = db.query(Holiday).order_by(Holiday.holiday_date.asc()).all()
        
        if not holidays:
            text = "📝 Праздничных дней пока нет."
        else:
            text = "📝 **Праздничные дни:**\n\n"
            for holiday in holidays:
                text += f"• {format_date(holiday.holiday_date, 'date_only')}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_holidays")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_list_holidays: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_vacations")
async def callback_admin_vacations(callback: CallbackQuery):
    """Обработчик управления отпуском и больничным."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    text = "🏖️ **Управление отпуском и больничным**\n\nВыберите действие:"
    keyboard = get_vacations_management_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.in_(["admin_set_vacation", "admin_set_sick_leave"]))
async def callback_admin_set_vacation(callback: CallbackQuery, state: FSMContext):
    """Обработчик установки отпуска или больничного."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    vacation_type = VacationType.VACATION if callback.data == "admin_set_vacation" else VacationType.SICK_LEAVE
    
    await state.update_data(vacation_type=vacation_type)
    await state.set_state(AdminStates.waiting_for_vacation_start)
    
    type_text = "отпуск" if vacation_type == VacationType.VACATION else "больничный"
    text = f"📅 **Установка {type_text}**\n\nВыберите дату начала:"
    keyboard = get_calendar_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminStates.waiting_for_vacation_start, F.data.startswith("calendar_select_"))
async def callback_vacation_start_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора даты начала отпуска/больничного."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from utils.date_helpers import get_timezone
        
        date_str = callback.data.split("_")[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        tz = get_timezone()
        selected_date = tz.localize(selected_date)
        
        await state.update_data(vacation_start=selected_date)
        await state.set_state(AdminStates.waiting_for_vacation_end)
        
        data = await state.get_data()
        vacation_type = data.get("vacation_type")
        type_text = "отпуска" if vacation_type == VacationType.VACATION else "больничного"
        
        text = f"📅 Выберите дату окончания {type_text}:"
        keyboard = get_calendar_keyboard()
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике vacation_start_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(AdminStates.waiting_for_vacation_end, F.data.startswith("calendar_select_"))
async def callback_vacation_end_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора даты окончания отпуска/больничного."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from utils.date_helpers import get_timezone
        from services.notifications import send_appointment_cancellation
        
        date_str = callback.data.split("_")[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        tz = get_timezone()
        selected_date = tz.localize(selected_date)
        
        data = await state.get_data()
        start_date = data.get("vacation_start")
        vacation_type = data.get("vacation_type")
        
        if selected_date < start_date:
            await callback.answer("❌ Дата окончания должна быть после даты начала", show_alert=True)
            return
        
        db = next(get_db())
        
        # Находим конфликтующие записи
        conflicting_appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= selected_date.replace(hour=23, minute=59),
            Appointment.status == AppointmentStatus.ACTIVE
        ).all()
        
        # Создаём период отпуска/больничного
        vacation = Vacation(
            vacation_type=vacation_type,
            start_date=start_date,
            end_date=selected_date.replace(hour=23, minute=59)
        )
        db.add(vacation)
        db.flush()
        
        # Отменяем конфликтующие записи
        for appointment in conflicting_appointments:
            appointment.status = AppointmentStatus.CANCELLED
            
            # Удаляем из календаря
            if appointment.google_calendar_event_id:
                try:
                    calendar_service = get_calendar_service()
                    calendar_service.delete_event(appointment.google_calendar_event_id)
                except Exception as e:
                    logger.error(f"Ошибка при удалении события: {e}")
            
            # Отправляем уведомление клиенту
            if appointment.telegram_user_id:
                try:
                    reason = "Отпуск врача" if vacation_type == VacationType.VACATION else "Больничный врача"
                    await send_appointment_cancellation(
                        callback.bot,
                        appointment.telegram_user_id,
                        appointment,
                        reason=reason
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления: {e}")
        
        db.commit()
        
        type_text = "отпуск" if vacation_type == VacationType.VACATION else "больничный"
        text = format_success_message(
            f"{type_text.capitalize()} установлен!\n\n"
            f"📅 С {format_date(start_date, 'date_only')} по {format_date(selected_date, 'date_only')}\n"
            f"Отменено записей: {len(conflicting_appointments)}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_vacations")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике vacation_end_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_list_vacations")
async def callback_admin_list_vacations(callback: CallbackQuery):
    """Обработчик просмотра списка периодов отпуска/больничного."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        db = next(get_db())
        
        vacations = db.query(Vacation).order_by(Vacation.start_date.desc()).all()
        
        if not vacations:
            text = "🏖️ Периодов отпуска/больничного пока нет."
        else:
            text = "🏖️ **Периоды отпуска и больничного:**\n\n"
            for vacation in vacations:
                type_text = "🏖️ Отпуск" if vacation.vacation_type == VacationType.VACATION else "🏥 Больничный"
                text += (
                    f"{type_text}\n"
                    f"📅 {format_date(vacation.start_date, 'date_only')} - "
                    f"{format_date(vacation.end_date, 'date_only')}\n\n"
                )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_vacations")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_list_vacations: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_schedule")
async def callback_admin_schedule(callback: CallbackQuery):
    """Обработчик управления расписанием."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    text = "📅 **Управление расписанием**\n\nВыберите действие:"
    keyboard = get_schedule_management_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_view_schedule")
async def callback_admin_view_schedule(callback: CallbackQuery):
    """Обработчик просмотра текущего расписания."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        from utils.schedule import BASE_SCHEDULE
        from utils.formatters import format_schedule
        
        # Получаем базовое расписание
        schedule_dict = {}
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        
        for i, day in enumerate(days):
            schedule = BASE_SCHEDULE.get(i)
            if schedule:
                schedule_dict[day] = f"{schedule[0]} - {schedule[1]}"
            else:
                schedule_dict[day] = "выходной"
        
        text = format_schedule(schedule_dict)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_schedule")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике admin_view_schedule: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "admin_change_schedule")
async def callback_admin_change_schedule(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения расписания."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_schedule_day)
    
    text = "📅 **Изменение расписания**\n\nВыберите день недели:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Понедельник", callback_data="schedule_day_0"),
            InlineKeyboardButton(text="Вторник", callback_data="schedule_day_1")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="schedule_day_2"),
            InlineKeyboardButton(text="Четверг", callback_data="schedule_day_3")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="schedule_day_4"),
            InlineKeyboardButton(text="Суббота", callback_data="schedule_day_5")
        ],
        [
            InlineKeyboardButton(text="Воскресенье", callback_data="schedule_day_6")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminStates.waiting_for_schedule_day, F.data.startswith("schedule_day_"))
async def callback_schedule_day_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора дня недели для изменения расписания."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        day_of_week = int(callback.data.split("_")[-1])
        await state.update_data(schedule_day=day_of_week)
        await state.set_state(AdminStates.waiting_for_schedule_start)
        
        text = "🕐 Введите время начала работы (формат HH:MM):\n\nНапример: 09:00"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике schedule_day_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.message(AdminStates.waiting_for_schedule_start)
async def process_schedule_start(message: Message, state: FSMContext):
    """Обработчик ввода времени начала работы."""
    time_str = message.text.strip()
    
    # Валидация формата HH:MM
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer(
            "❌ Неверный формат. Используйте HH:MM (например, 09:00)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")]
            ])
        )
        return
    
    await state.update_data(schedule_start=time_str)
    await state.set_state(AdminStates.waiting_for_schedule_end)
    
    await message.answer(
        "🕐 Введите время окончания работы (формат HH:MM):\n\nНапример: 18:00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")]
        ])
    )


@router.message(AdminStates.waiting_for_schedule_end)
async def process_schedule_end(message: Message, state: FSMContext):
    """Обработчик ввода времени окончания работы."""
    time_str = message.text.strip()
    
    # Валидация формата HH:MM
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer(
            "❌ Неверный формат. Используйте HH:MM (например, 18:00)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")]
            ])
        )
        return
    
    data = await state.get_data()
    start_time = data.get("schedule_start")
    
    # Проверяем, что время окончания после начала
    start_hour, start_minute = map(int, start_time.split(':'))
    end_hour, end_minute = map(int, time_str.split(':'))
    
    if (end_hour < start_hour) or (end_hour == start_hour and end_minute <= start_minute):
        await message.answer(
            "❌ Время окончания должно быть после времени начала",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")]
            ])
        )
        return
    
    # Сохраняем изменение расписания
    try:
        db = next(get_db())
        day_of_week = data.get("schedule_day")
        
        # Проверяем конфликты с существующими записями
        from utils.schedule import get_schedule_for_day, is_workday
        from datetime import datetime, timedelta
        
        # Находим ближайшую дату с этим днём недели
        today = datetime.now()
        days_ahead = day_of_week - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
        
        # Получаем текущее расписание для этого дня
        current_schedule = get_schedule_for_day(db, target_date, False)
        
        # Проверяем записи на будущие даты с этим днём недели
        future_appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= today,
            Appointment.status == AppointmentStatus.ACTIVE
        ).all()
        
        conflicting_appointments = []
        for appointment in future_appointments:
            if appointment.appointment_date.weekday() == day_of_week:
                appt_hour = appointment.appointment_date.hour
                appt_minute = appointment.appointment_date.minute
                
                # Проверяем, попадает ли запись в новое расписание
                start_hour, start_minute = map(int, start_time.split(':'))
                end_hour, end_minute = map(int, time_str.split(':'))
                
                appt_time = appt_hour * 60 + appt_minute
                new_start = start_hour * 60 + start_minute
                new_end = end_hour * 60 + end_minute
                
                if not (new_start <= appt_time < new_end):
                    conflicting_appointments.append(appointment)
        
        # Показываем конфликты, если есть
        if conflicting_appointments:
            text = (
                f"⚠️ **Обнаружены конфликтующие записи:**\n\n"
                f"Найдено {len(conflicting_appointments)} записей, которые попадают вне нового расписания.\n\n"
                f"Что сделать?"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Применить (отменить конфликты)",
                        callback_data=f"admin_confirm_schedule_{day_of_week}_{start_time}_{time_str}"
                    )
                ],
                [
                    InlineKeyboardButton(text="❌ Отмена", callback_data="admin_schedule")
                ]
            ])
            
            await state.update_data(
                schedule_end=time_str,
                conflicting_appointments=[a.id for a in conflicting_appointments]
            )
            await message.answer(text, reply_markup=keyboard)
            await state.clear()
            return
        
        # Нет конфликтов, сохраняем
        schedule_change = ScheduleChange(
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=time_str,
            effective_from=datetime.now(),
            effective_to=None  # Бессрочно
        )
        
        db.add(schedule_change)
        db.commit()
        
        text = format_success_message(
            f"Расписание изменено!\n\n"
            f"День: {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][day_of_week]}\n"
            f"Время: {start_time} - {time_str}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_schedule")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении расписания: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении расписания",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_schedule")]
            ])
        )


@router.callback_query(F.data.startswith("admin_confirm_schedule_"))
async def callback_admin_confirm_schedule(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения изменения расписания с конфликтами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        parts = callback.data.split("_")
        day_of_week = int(parts[3])
        start_time = parts[4]
        end_time = parts[5]
        
        db = next(get_db())
        
        # Сохраняем изменение расписания
        schedule_change = ScheduleChange(
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            effective_from=datetime.now(),
            effective_to=None
        )
        db.add(schedule_change)
        db.flush()
        
        # Отменяем конфликтующие записи
        conflicting_ids = state.get_data().get("conflicting_appointments", [])
        cancelled_count = 0
        
        for appointment_id in conflicting_ids:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if appointment and appointment.status == AppointmentStatus.ACTIVE:
                appointment.status = AppointmentStatus.CANCELLED
                
                # Удаляем из календаря
                if appointment.google_calendar_event_id:
                    try:
                        calendar_service = get_calendar_service()
                        calendar_service.delete_event(appointment.google_calendar_event_id)
                    except Exception as e:
                        logger.error(f"Ошибка при удалении события: {e}")
                
                # Уведомляем клиента
                if appointment.telegram_user_id:
                    try:
                        await send_appointment_cancellation(
                            callback.bot,
                            appointment.telegram_user_id,
                            appointment,
                            reason="Изменение расписания работы"
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления: {e}")
                
                cancelled_count += 1
        
        db.commit()
        
        text = format_success_message(
            f"Расписание изменено!\n\n"
            f"День: {['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][day_of_week]}\n"
            f"Время: {start_time} - {end_time}\n\n"
            f"Отменено записей: {cancelled_count}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_schedule")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике confirm_schedule: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


def register_admin_handlers(dp):
    """Регистрирует обработчики админ-панели."""
    dp.include_router(router)

