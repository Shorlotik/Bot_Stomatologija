"""
Модуль для работы с Google Calendar API.
"""
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from config import config
from utils.logger import logger
from utils.date_helpers import get_timezone


# Области доступа для Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    """Класс для работы с Google Calendar API."""
    
    def __init__(self):
        """Инициализация сервиса Google Calendar."""
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Инициализирует сервис Google Calendar с использованием refresh token из .env."""
        try:
            # Используем refresh token из .env
            if not config.GOOGLE_REFRESH_TOKEN:
                logger.warning("GOOGLE_REFRESH_TOKEN не установлен в .env")
                logger.warning("Бот будет работать без синхронизации с Google Calendar")
                logger.info("Для получения refresh token запустите: python3 get_token.py")
                self.service = None
                return
            
            if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
                logger.error("GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET не установлены")
                logger.warning("Бот будет работать без синхронизации с Google Calendar")
                self.service = None
                return
            
            # Создаем credentials из refresh token
            self.credentials = Credentials(
                token=None,
                refresh_token=config.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.GOOGLE_CLIENT_ID,
                client_secret=config.GOOGLE_CLIENT_SECRET,
                scopes=SCOPES
            )
            
            # Обновляем токен если нужно
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            
            # Создаём сервис
            if self.credentials:
                self.service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar сервис успешно инициализирован")
            else:
                logger.warning("Google Calendar сервис не инициализирован - токены отсутствуют")
                self.service = None
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации Google Calendar сервиса: {e}")
            logger.warning("Бот будет работать без синхронизации с Google Calendar")
            self.service = None
    
    def create_event(
        self,
        summary: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str = "",
        attendee_email: Optional[str] = None
    ) -> Optional[str]:
        """
        Создаёт событие в Google Calendar.
        
        Args:
            summary: Название события
            start_datetime: Дата и время начала
            end_datetime: Дата и время окончания
            description: Описание события
            attendee_email: Email участника (опционально)
            
        Returns:
            Optional[str]: ID созданного события или None в случае ошибки
        """
        try:
            # Преобразуем datetime в RFC3339 формат
            tz = get_timezone()
            if start_datetime.tzinfo is None:
                start_datetime = tz.localize(start_datetime)
            if end_datetime.tzinfo is None:
                end_datetime = tz.localize(end_datetime)
            
            start_rfc3339 = start_datetime.isoformat()
            end_rfc3339 = end_datetime.isoformat()
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_rfc3339,
                    'timeZone': str(tz),
                },
                'end': {
                    'dateTime': end_rfc3339,
                    'timeZone': str(tz),
                },
            }
            
            if attendee_email:
                event['attendees'] = [{'email': attendee_email}]
            
            # Создаём событие
            created_event = self.service.events().insert(
                calendarId=config.GOOGLE_CALENDAR_ID,
                body=event
            ).execute()
            
            event_id = created_event.get('id')
            logger.info(f"Событие создано в календаре: {event_id}")
            
            return event_id
            
        except HttpError as e:
            logger.error(f"Ошибка HTTP при создании события в календаре: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании события в календаре: {e}")
            return None
    
    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Обновляет событие в Google Calendar.
        
        Args:
            event_id: ID события для обновления
            summary: Новое название (опционально)
            start_datetime: Новое время начала (опционально)
            end_datetime: Новое время окончания (опционально)
            description: Новое описание (опционально)
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        if not self.service:
            logger.warning("Google Calendar сервис не доступен - событие не обновлено")
            return False
        
        try:
            # Получаем существующее событие
            event = self.service.events().get(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            # Обновляем поля
            if summary:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if start_datetime:
                tz = get_timezone()
                if start_datetime.tzinfo is None:
                    start_datetime = tz.localize(start_datetime)
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': str(tz),
                }
            if end_datetime:
                tz = get_timezone()
                if end_datetime.tzinfo is None:
                    end_datetime = tz.localize(end_datetime)
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': str(tz),
                }
            
            # Обновляем событие
            updated_event = self.service.events().update(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Событие обновлено в календаре: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Ошибка HTTP при обновлении события: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении события: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """
        Удаляет событие из Google Calendar.
        
        Args:
            event_id: ID события для удаления
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        if not self.service:
            logger.warning("Google Calendar сервис не доступен - событие не удалено")
            return False
        
        try:
            self.service.events().delete(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            logger.info(f"Событие удалено из календаря: {event_id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Событие {event_id} не найдено в календаре")
                return True  # Уже удалено
            logger.error(f"Ошибка HTTP при удалении события: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении события: {e}")
            return False
    
    def get_events_for_date(self, date: datetime) -> list:
        """
        Получает все события для указанной даты.
        
        Args:
            date: Дата для проверки
            
        Returns:
            list: Список событий
        """
        if not self.service:
            logger.warning("Google Calendar сервис не доступен - события не получены")
            return []
        
        try:
            tz = get_timezone()
            if date.tzinfo is None:
                date = tz.localize(date)
            
            # Начало и конец дня
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = date.replace(hour=23, minute=59, second=59, microsecond=999)
            
            # Получаем события
            events_result = self.service.events().list(
                calendarId=config.GOOGLE_CALENDAR_ID,
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Найдено {len(events)} событий на {date.date()}")
            
            return events
            
        except HttpError as e:
            logger.error(f"Ошибка HTTP при получении событий: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении событий: {e}")
            return []
    
    def is_time_available(self, start_datetime: datetime, duration_minutes: int) -> bool:
        """
        Проверяет, доступно ли время для записи.
        
        Args:
            start_datetime: Дата и время начала
            duration_minutes: Продолжительность в минутах
            
        Returns:
            bool: True если время доступно, False иначе
        """
        try:
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            
            # Получаем события в этом диапазоне
            events = self.get_events_for_date(start_datetime)
            
            for event in events:
                event_start_str = event.get('start', {}).get('dateTime', '')
                event_end_str = event.get('end', {}).get('dateTime', '')
                
                if not event_start_str or not event_end_str:
                    continue
                
                event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                
                # Проверяем пересечение
                if start_datetime < event_end and end_datetime > event_start:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности времени: {e}")
            return False


# Глобальный экземпляр сервиса
_calendar_service: Optional[GoogleCalendarService] = None


def get_calendar_service() -> GoogleCalendarService:
    """Получает или создаёт экземпляр сервиса Google Calendar."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service

