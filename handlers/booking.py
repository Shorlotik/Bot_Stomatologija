"""
Обработчики процесса записи на приём.
Использует FSM для многошаговой формы.
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Appointment, AppointmentStatus, User
from keyboards.booking import get_calendar_keyboard, get_time_slots_keyboard, get_confirmation_keyboard
from keyboards.main import get_back_to_main_keyboard
from utils.schedule import (
    calculate_time_slots, check_appointment_limit, is_time_slot_available,
    is_date_available
)
from utils.validators import validate_phone, validate_full_name, format_phone, get_phone_validation_error, get_name_validation_error
from utils.formatters import format_appointment_info, format_success_message, format_error_message
from utils.date_helpers import format_date, get_timezone
from utils.logger import logger

router = Router()


class BookingStates(StatesGroup):
    """Состояния процесса записи на приём."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_service = State()
    waiting_for_comment = State()
    confirmation = State()


class OrderBadsStates(StatesGroup):
    """Состояния процесса заказа БАДов."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_products = State()
    waiting_for_comment = State()


# Продолжительность услуг в минутах
SERVICE_DURATIONS = {
    "Консультация": 30,
    "Лечение кариеса": 60,
    "Лечение пульпита": 90,
    "Профессиональная чистка зубов": 60,
    "Отбеливание зубов": 90,
    "Протезирование": 120,
    "Имплантация": 120,
    "Выявление дефицитов в организме по зубам": 60,
    "Выявление дефицитов при помощи БРТ": 30,
    "Подбор витаминов и минералов": 60,
    "БРТ": 30,
    "Другое": 60,
}


def get_service_keyboard(services: list[str]) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора услуги."""
    keyboard = []
    row = []
    
    for i, service in enumerate(services):
        if i > 0 and i % 2 == 0:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            text=service,
            callback_data=f"service_select_{service}"
        ))
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Обработчики календаря
@router.callback_query(F.data.startswith("calendar_select_"))
async def callback_calendar_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора даты в календаре."""
    try:
        date_str = callback.data.split("_")[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        tz = get_timezone()
        selected_date = tz.localize(selected_date)
        
        # Сохраняем выбранную дату
        data = await state.get_data()
        is_brt = data.get("is_brt", False)
        
        # Проверяем доступность даты
        db = next(get_db())
        if not is_date_available(db, selected_date):
            await callback.answer("❌ Эта дата недоступна для записи", show_alert=True)
            return
        
        # Для БРТ проверяем, что это понедельник
        if is_brt and selected_date.weekday() != 0:
            await callback.answer("❌ БРТ доступен только по понедельникам", show_alert=True)
            return
        
        await state.update_data(selected_date=selected_date)
        await state.set_state(BookingStates.waiting_for_time)
        
        # Рассчитываем доступные временные слоты
        service_duration = data.get("service_duration", 60)
        time_slots = calculate_time_slots(db, selected_date, service_duration, is_brt)
        
        if not time_slots:
            await callback.answer("❌ На эту дату нет свободных слотов", show_alert=True)
            return
        
        text = f"🕐 Выберите время:\n\n📅 Дата: {format_date(selected_date, 'date_only')}"
        keyboard = get_time_slots_keyboard(time_slots)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике calendar_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("time_select_"))
async def callback_time_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора времени."""
    try:
        time_str = callback.data.split("_")[-1]
        
        data = await state.get_data()
        selected_date = data.get("selected_date")
        
        if not selected_date:
            await callback.answer("❌ Ошибка: дата не выбрана", show_alert=True)
            return
        
        # Проверяем доступность слота
        db = next(get_db())
        service_duration = data.get("service_duration", 60)
        
        if not is_time_slot_available(db, selected_date, time_str, service_duration):
            await callback.answer("❌ Это время уже занято", show_alert=True)
            return
        
        await state.update_data(selected_time=time_str)
        
        # Если услуга уже выбрана, переходим к подтверждению
        if data.get("service_type"):
            await state.set_state(BookingStates.confirmation)
            await show_confirmation(callback, state)
        else:
            await state.set_state(BookingStates.waiting_for_service)
            await show_service_selection(callback, state)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике time_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


async def show_service_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор услуги."""
    data = await state.get_data()
    is_brt = data.get("is_brt", False)
    
    if is_brt:
        services = ["БРТ"]
    else:
        # Определяем услуги в зависимости от типа записи
        service_type_context = data.get("service_type_context", "dentistry")
        if service_type_context == "dentistry":
            from handlers.dentistry import DENTISTRY_SERVICES
            services = DENTISTRY_SERVICES
        else:
            from handlers.nutrition import NUTRITION_SERVICES
            services = NUTRITION_SERVICES
    
    text = "💼 Выберите тип услуги:"
    keyboard = get_service_keyboard(services)
    
    await callback.message.edit_text(text, reply_markup=keyboard)




async def show_confirmation(callback: CallbackQuery, state: FSMContext):
    """Показывает подтверждение записи."""
    data = await state.get_data()
    
    full_name = data.get("full_name", "")
    phone = data.get("phone", "")
    selected_date = data.get("selected_date")
    selected_time = data.get("selected_time", "")
    service_type = data.get("service_type", "")
    comment = data.get("comment", "")
    
    if selected_date:
        hour, minute = map(int, selected_time.split(':'))
        appointment_datetime = selected_date.replace(hour=hour, minute=minute)
        
        appointment_text = format_appointment_info(
            full_name=full_name,
            appointment_date=format_date(appointment_datetime, "full"),
            service_type=service_type,
            phone=phone,
            comment=comment if comment else None
        )
        
        text = f"{appointment_text}\n\n✅ Проверьте данные и подтвердите запись:"
        keyboard = get_confirmation_keyboard()
        
        await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "booking_confirm")
async def callback_booking_confirm(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения записи."""
    try:
        data = await state.get_data()
        
        # Проверяем лимит записей
        db = next(get_db())
        telegram_user_id = callback.from_user.id
        
        if not check_appointment_limit(db, telegram_user_id):
            await callback.answer(
                "❌ У вас уже есть активная запись. Отмените её перед созданием новой.",
                show_alert=True
            )
            return
        
        # Получаем данные
        full_name = data.get("full_name")
        phone = data.get("phone")
        selected_date = data.get("selected_date")
        selected_time = data.get("selected_time")
        service_type = data.get("service_type")
        service_duration = data.get("service_duration", 60)
        comment = data.get("comment", "")
        
        # Формируем datetime
        hour, minute = map(int, selected_time.split(':'))
        appointment_datetime = selected_date.replace(hour=hour, minute=minute)
        
        # Проверяем доступность времени ещё раз
        if not is_time_slot_available(db, selected_date, selected_time, service_duration):
            await callback.answer("❌ Это время уже занято", show_alert=True)
            return
        
        # Создаём или находим пользователя
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
            user_id=user.id,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            phone=phone,
            appointment_date=appointment_datetime,
            service_type=service_type,
            service_duration=service_duration,
            comment=comment if comment else None,
            status=AppointmentStatus.ACTIVE,
            created_by_doctor=False
        )
        
        db.add(appointment)
        db.flush()
        
        # Создаём событие в Google Calendar
        try:
            from services.calendar import get_calendar_service
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
            
            event_id = calendar_service.create_event(
                summary=f"{service_type} - {full_name}",
                start_datetime=appointment_datetime,
                end_datetime=end_datetime,
                description=event_description
            )
            
            if event_id:
                appointment.google_calendar_event_id = event_id
                db.commit()
            else:
                db.commit()
                logger.warning("Не удалось создать событие в Google Calendar")
        except Exception as e:
            logger.error(f"Ошибка при создании события в Google Calendar: {e}")
            db.commit()
        
        # Отправляем уведомления
        try:
            from services.notifications import (
                send_appointment_confirmation,
                send_new_appointment_notification
            )
            
            # Уведомление клиенту
            if telegram_user_id:
                await send_appointment_confirmation(callback.bot, telegram_user_id, appointment)
            
            # Уведомление врачу
            await send_new_appointment_notification(callback.bot, appointment)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {e}")
        
        text = format_success_message(
            f"Ваша запись успешно создана!\n\n"
            f"📅 Дата: {format_date(appointment_datetime, 'full')}\n"
            f"🦷 Услуга: {service_type}"
        )
        
        keyboard = get_back_to_main_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Запись создана!", show_alert=True)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике booking_confirm: {e}")
        await callback.answer("Произошла ошибка при создании записи", show_alert=True)


@router.callback_query(F.data == "booking_cancel")
async def callback_booking_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены записи."""
    await state.clear()
    from utils.formatters import format_welcome_message
    from keyboards.main import get_main_menu_keyboard
    
    text = format_welcome_message()
    keyboard = get_main_menu_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("Запись отменена")


# Обработчики начала процесса записи
@router.callback_query(F.data.in_(["dentistry_book", "nutrition_consultation"]))
async def callback_start_booking(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс записи на приём."""
    try:
        # Определяем тип записи
        is_brt = False
        service_type_context = "dentistry" if callback.data == "dentistry_book" else "nutrition"
        
        await state.update_data(
            is_brt=is_brt,
            service_type_context=service_type_context
        )
        await state.set_state(BookingStates.waiting_for_name)
        
        text = "📝 **Запись на приём**\n\nПожалуйста, введите ваше ФИО:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start_booking: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "nutrition_brt")
async def callback_start_brt_booking(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс записи на БРТ."""
    try:
        await state.update_data(
            is_brt=True,
            service_type_context="nutrition",
            service_type="БРТ",
            service_duration=30
        )
        await state.set_state(BookingStates.waiting_for_name)
        
        text = "🔬 **Запись на сеанс БРТ**\n\nПожалуйста, введите ваше ФИО:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start_brt_booking: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# Обработчики ввода данных
@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработчик ввода ФИО."""
    full_name = message.text.strip()
    
    if not validate_full_name(full_name):
        await message.answer(
            get_name_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
            ])
        )
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(BookingStates.waiting_for_phone)
    
    await message.answer(
        "📞 Введите ваш номер телефона:\n\n"
        "Формат: +375291234567 или 80291234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
    )


@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработчик ввода телефона."""
    phone = message.text.strip()
    
    if not validate_phone(phone):
        await message.answer(
            get_phone_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
            ])
        )
        return
    
    formatted_phone = format_phone(phone)
    await state.update_data(phone=formatted_phone)
    
    data = await state.get_data()
    is_brt = data.get("is_brt", False)
    
    if is_brt:
        # Для БРТ сразу переходим к выбору даты (только понедельники)
        await state.set_state(BookingStates.waiting_for_date)
        text = "📅 Выберите дату (доступны только понедельники):"
        keyboard = get_calendar_keyboard()
    else:
        # Для обычной записи выбираем дату
        await state.set_state(BookingStates.waiting_for_date)
        text = "📅 Выберите дату:"
        keyboard = get_calendar_keyboard()
    
    await message.answer(text, reply_markup=keyboard)


@router.message(BookingStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработчик ввода комментария."""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(BookingStates.confirmation)
    
    # Показываем подтверждение
    data = await state.get_data()
    selected_date = data.get("selected_date")
    selected_time = data.get("selected_time")
    
    if selected_date and selected_time:
        hour, minute = map(int, selected_time.split(':'))
        appointment_datetime = selected_date.replace(hour=hour, minute=minute)
        
        full_name = data.get("full_name", "")
        phone = data.get("phone", "")
        service_type = data.get("service_type", "")
        
        appointment_text = format_appointment_info(
            full_name=full_name,
            appointment_date=format_date(appointment_datetime, "full"),
            service_type=service_type,
            phone=phone,
            comment=comment
        )
        
        text = f"{appointment_text}\n\n✅ Проверьте данные и подтвердите запись:"
        keyboard = get_confirmation_keyboard()
        
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "booking_edit")
async def callback_booking_edit(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования записи."""
    await state.set_state(BookingStates.waiting_for_comment)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="booking_skip_comment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
    ])
    await callback.message.edit_text(
        "📝 Введите комментарий (или нажмите 'Пропустить'):",
        reply_markup=keyboard
    )
    await callback.answer()


# Добавляем проверку комментария после выбора услуги
@router.callback_query(F.data.startswith("service_select_"))
async def callback_service_select(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора услуги."""
    try:
        service_type = callback.data.replace("service_select_", "")
        service_duration = SERVICE_DURATIONS.get(service_type, 60)
        
        await state.update_data(
            service_type=service_type,
            service_duration=service_duration
        )
        
        # Переходим к комментарию (опционально)
        await state.set_state(BookingStates.waiting_for_comment)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="booking_skip_comment")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
        
        await callback.message.edit_text(
            "📝 Введите комментарий (или нажмите 'Пропустить'):",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике service_select: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "booking_back_to_date")
async def callback_back_to_date(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору даты."""
    await state.set_state(BookingStates.waiting_for_date)
    data = await state.get_data()
    is_brt = data.get("is_brt", False)
    
    text = "📅 Выберите дату:" + (" (только понедельники)" if is_brt else "")
    keyboard = get_calendar_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_prev_") | F.data.startswith("calendar_next_"))
async def callback_calendar_navigate(callback: CallbackQuery, state: FSMContext):
    """Обработчик навигации по календарю (предыдущий/следующий месяц)."""
    try:
        parts = callback.data.split("_")
        direction = parts[1]  # "prev" или "next"
        month_offset = int(parts[2])
        
        keyboard = get_calendar_keyboard(month_offset=month_offset)
        
        data = await state.get_data()
        is_brt = data.get("is_brt", False)
        text = "📅 Выберите дату:" + (" (только понедельники)" if is_brt else "")
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике calendar_navigate: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.in_(["calendar_info", "calendar_empty", "calendar_past"]))
async def callback_calendar_info(callback: CallbackQuery):
    """Обработчик информационных callback календаря."""
    await callback.answer()


# Обработка комментария - если пользователь пропустил
@router.callback_query(F.data == "booking_skip_comment")
async def callback_skip_comment(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска комментария."""
    await state.update_data(comment="")
    await state.set_state(BookingStates.confirmation)
    await show_confirmation(callback, state)
    await callback.answer()


# Обработчики заказа БАДов
@router.callback_query(F.data == "nutrition_order_bads")
async def callback_start_order_bads(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс заказа БАДов."""
    try:
        await state.set_state(OrderBadsStates.waiting_for_name)
        
        text = "📦 **Заказ БАДов NSP**\n\nПожалуйста, введите ваше ФИО:"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start_order_bads: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.message(OrderBadsStates.waiting_for_name)
async def process_order_name(message: Message, state: FSMContext):
    """Обработчик ввода ФИО для заказа."""
    full_name = message.text.strip()
    
    if not validate_full_name(full_name):
        await message.answer(
            get_name_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
            ])
        )
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(OrderBadsStates.waiting_for_phone)
    
    await message.answer(
        "📞 Введите ваш номер телефона:\n\n"
        "Формат: +375291234567 или 80291234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
    )


@router.message(OrderBadsStates.waiting_for_phone)
async def process_order_phone(message: Message, state: FSMContext):
    """Обработчик ввода телефона для заказа."""
    phone = message.text.strip()
    
    if not validate_phone(phone):
        await message.answer(
            get_phone_validation_error(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
            ])
        )
        return
    
    formatted_phone = format_phone(phone)
    await state.update_data(phone=formatted_phone)
    await state.set_state(OrderBadsStates.waiting_for_products)
    
    await message.answer(
        "📦 Введите список желаемых продуктов NSP:\n\n"
        "Опишите, какие продукты вы хотите заказать.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
        ])
    )


@router.message(OrderBadsStates.waiting_for_products)
async def process_order_products(message: Message, state: FSMContext):
    """Обработчик ввода списка продуктов."""
    products = message.text.strip()
    
    if not products or len(products) < 3:
        await message.answer(
            "❌ Пожалуйста, укажите список продуктов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
            ])
        )
        return
    
    await state.update_data(products=products)
    await state.set_state(OrderBadsStates.waiting_for_comment)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="order_skip_comment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")]
    ])
    
    await message.answer(
        "📝 Введите комментарий к заказу (или нажмите 'Пропустить'):",
        reply_markup=keyboard
    )


@router.message(OrderBadsStates.waiting_for_comment)
async def process_order_comment(message: Message, state: FSMContext):
    """Обработчик ввода комментария для заказа."""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    
    # Сохраняем заказ
    await save_order_to_db(message, state)
    

@router.callback_query(F.data == "order_skip_comment")
async def callback_order_skip_comment(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска комментария в заказе."""
    await state.update_data(comment="")
    # Сохраняем заказ
    await save_order_to_db(callback.message, state)
    await callback.answer()


async def save_order_to_db(message: Message, state: FSMContext):
    """Сохраняет заказ БАДов в базу данных."""
    try:
        data = await state.get_data()
        
        db = next(get_db())
        telegram_user_id = message.from_user.id
        
        # Создаём или находим пользователя
        user = db.query(User).filter(User.telegram_id == telegram_user_id).first()
        if not user:
            user = User(
                telegram_id=telegram_user_id,
                full_name=data.get("full_name"),
                phone=data.get("phone")
            )
            db.add(user)
            db.flush()
        
        # Создаём заказ
        from database.models import Order, OrderStatus
        
        order = Order(
            user_id=user.id,
            telegram_user_id=telegram_user_id,
            full_name=data.get("full_name"),
            phone=data.get("phone"),
            products_list=data.get("products", ""),
            comment=data.get("comment", ""),
            status=OrderStatus.PENDING
        )
        
        db.add(order)
        db.commit()
        
        # Отправляем уведомление врачу о новом заказе
        try:
            from services.notifications import send_new_order_notification
            await send_new_order_notification(message.bot, order)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о заказе: {e}")
        
        from utils.formatters import format_success_message, format_order_info
        from keyboards.main import get_main_menu_keyboard
        
        text = format_success_message(
            "Ваш заказ успешно принят!\n\n"
            "Врач свяжется с вами в ближайшее время."
        )
        
        keyboard = get_main_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {e}")
        await message.answer(
            format_error_message("Произошла ошибка при сохранении заказа. Попробуйте позже."),
            reply_markup=get_back_to_main_keyboard()
        )


# Обработчики истории записей и отмены
@router.callback_query(F.data == "my_appointments")
async def callback_my_appointments(callback: CallbackQuery):
    """Обработчик просмотра истории записей клиентом."""
    try:
        db = next(get_db())
        telegram_user_id = callback.from_user.id
        
        # Получаем все записи пользователя
        appointments = db.query(Appointment).filter(
            Appointment.telegram_user_id == telegram_user_id
        ).order_by(Appointment.appointment_date.desc()).all()
        
        if not appointments:
            text = "📋 У вас пока нет записей."
            keyboard = get_back_to_main_keyboard()
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Формируем текст с историей записей
        text = "📋 **Ваши записи:**\n\n"
        
        from utils.date_helpers import format_date
        from database.models import AppointmentStatus
        
        for i, appointment in enumerate(appointments[:10], 1):  # Показываем последние 10
            status_emoji = {
                AppointmentStatus.ACTIVE: "✅",
                AppointmentStatus.CANCELLED: "❌",
                AppointmentStatus.COMPLETED: "✓"
            }.get(appointment.status, "📅")
            
            status_text = {
                AppointmentStatus.ACTIVE: "Активна",
                AppointmentStatus.CANCELLED: "Отменена",
                AppointmentStatus.COMPLETED: "Завершена"
            }.get(appointment.status, "Неизвестно")
            
            text += (
                f"{status_emoji} **{i}. {appointment.service_type}**\n"
                f"📅 {format_date(appointment.appointment_date, 'full')}\n"
                f"📞 {appointment.phone}\n"
                f"Статус: {status_text}\n\n"
            )
        
        if len(appointments) > 10:
            text += f"\n... и ещё {len(appointments) - 10} записей"
        
        # Кнопки для активных записей
        active_appointments = [
            a for a in appointments
            if a.status == AppointmentStatus.ACTIVE
        ]
        
        keyboard_buttons = []
        if active_appointments:
            # Добавляем кнопки для отмены активных записей
            for appointment in active_appointments[:5]:  # Максимум 5 кнопок
                date_str = appointment.appointment_date.strftime("%d.%m %H:%M")
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"❌ Отменить {date_str}",
                        callback_data=f"cancel_appointment_{appointment.id}"
                    )
                ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике my_appointments: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("cancel_appointment_"))
async def callback_cancel_appointment(callback: CallbackQuery):
    """Обработчик отмены записи клиентом."""
    try:
        appointment_id = int(callback.data.split("_")[-1])
        
        db = next(get_db())
        telegram_user_id = callback.from_user.id
        
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.telegram_user_id == telegram_user_id,
            Appointment.status == AppointmentStatus.ACTIVE
        ).first()
        
        if not appointment:
            await callback.answer("❌ Запись не найдена или уже отменена", show_alert=True)
            return
        
        # Отменяем запись
        appointment.status = AppointmentStatus.CANCELLED
        
        # Удаляем событие из Google Calendar
        if appointment.google_calendar_event_id:
            try:
                from services.calendar import get_calendar_service
                calendar_service = get_calendar_service()
                calendar_service.delete_event(appointment.google_calendar_event_id)
            except Exception as e:
                logger.error(f"Ошибка при удалении события из календаря: {e}")
        
        db.commit()
        
        # TODO: Отправить уведомление врачу (задача 4.0)
        
        from utils.formatters import format_success_message
        from utils.date_helpers import format_date
        
        text = format_success_message(
            f"Запись успешно отменена!\n\n"
            f"📅 Дата: {format_date(appointment.appointment_date, 'full')}\n"
            f"🦷 Услуга: {appointment.service_type}"
        )
        
        keyboard = get_back_to_main_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Запись отменена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике cancel_appointment: {e}")
        await callback.answer("Произошла ошибка при отмене записи", show_alert=True)


def register_booking_handlers(dp):
    """Регистрирует обработчики процесса записи."""
    dp.include_router(router)

