# Инструкция по настройке переменных окружения

## 1. BOT_TOKEN (Telegram Bot Token)

1. Откройте Telegram и найдите бота [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: "Стоматолог Прокопчик")
   - Введите username бота (должен заканчиваться на `bot`, например: `stomatolog_bot`)
4. BotFather пришлёт вам токен вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Скопируйте этот токен в `.env` файл:
   ```
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

## 2. Google Calendar API - Получение Client ID и Client Secret

### Шаг 1: Создание проекта в Google Cloud

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Войдите в свой Google аккаунт (или создайте новый)
3. Нажмите на выпадающий список проектов вверху
4. Нажмите "Новый проект" (New Project)
5. Введите название проекта (например: "Telegram Bot Calendar")
6. Нажмите "Создать"

### Шаг 2: Включение Google Calendar API

1. В меню слева выберите "APIs & Services" > "Library"
2. В поиске введите "Google Calendar API"
3. Нажмите на "Google Calendar API"
4. Нажмите кнопку "Enable" (Включить)

### Шаг 3: Создание OAuth 2.0 Credentials

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "OAuth client ID"
3. Если появится запрос на настройку OAuth consent screen:
   - Выберите "External" (для личного использования)
   - Заполните обязательные поля:
     - App name: "Telegram Bot Calendar"
     - User support email: ваш email (tgstamotolognsp@gmail.com)
     - Developer contact: ваш email
   - Нажмите "Save and Continue"
   - На странице "Scopes" нажмите "Save and Continue"
   - На странице "Test users" нажмите "Save and Continue"
   - На странице "Summary" нажмите "Back to Dashboard"

4. Вернитесь в "Credentials" и нажмите "Create Credentials" > "OAuth client ID"
5. Выберите тип "Desktop app" или "Other"
6. Введите название (например: "Telegram Bot")
7. Нажмите "Create"
8. Появится окно с:
   - **Client ID** (скопируйте его)
   - **Client Secret** (скопируйте его)
9. Сохраните эти значения в `.env`:
   ```
   GOOGLE_CLIENT_ID=ваш_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=ваш_client_secret
   ```

### Шаг 4: Получение Refresh Token

Создайте файл `get_refresh_token.py`:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Создайте файл credentials.json с вашими данными
# Или используйте переменные окружения
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"]
        }
    },
    SCOPES
)

# Запустите авторизацию
credentials = flow.run_local_server(port=0)

print(f"Refresh Token: {credentials.refresh_token}")
print(f"Access Token: {credentials.token}")
```

**Или используйте готовый скрипт:**

1. Создайте файл `get_token.py` (см. ниже)
2. Запустите: `python get_token.py`
3. Скопируйте полученный Refresh Token в `.env`

## 3. GOOGLE_CALENDAR_EMAIL и GOOGLE_CALENDAR_ID

- **GOOGLE_CALENDAR_EMAIL**: Email вашего Google аккаунта (tgstamotolognsp@gmail.com)
- **GOOGLE_CALENDAR_ID**: Обычно равен email. Если используете основной календарь, то это email.
  Для получения ID календаря:
  1. Откройте [Google Calendar](https://calendar.google.com)
  2. Нажмите на три точки рядом с календарём
  3. Выберите "Settings and sharing"
  4. Найдите "Calendar ID" - это и есть ваш GOOGLE_CALENDAR_ID

## 4. ADMIN_TELEGRAM_ID (опционально)

1. Найдите бота [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте ему любое сообщение
3. Он вернёт ваш Telegram ID (число вида `123456789`)
4. Скопируйте это число в `.env`:
   ```
   ADMIN_TELEGRAM_ID=123456789
   ```

**Примечание:** Если не указать ADMIN_TELEGRAM_ID, доступ к админ-панели будет по паролю (ADMIN_PASSWORD).

## 5. ADMIN_PASSWORD (опционально)

Придумайте любой пароль для доступа к админ-панели:
```
ADMIN_PASSWORD=ваш_секретный_пароль
```

## 6. DATABASE_URL

Для SQLite (по умолчанию):
```
DATABASE_URL=sqlite:///database.db
```

Для PostgreSQL:
```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## 7. TIMEZONE

Часовой пояс в формате IANA:
```
TIMEZONE=Europe/Minsk
```

Другие варианты:
- `Europe/Moscow` (Москва)
- `Europe/Kiev` (Киев)
- `UTC` (UTC)

## 8. LOG_LEVEL

Уровень логирования:
```
LOG_LEVEL=INFO
```

Варианты: `DEBUG`, `INFO`, `WARNING`, `ERROR`

---

## Пример полного .env файла

```env
# Telegram Bot Configuration
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Google Calendar API Configuration
GOOGLE_CALENDAR_EMAIL=tgstamotolognsp@gmail.com
GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
GOOGLE_REFRESH_TOKEN=1//0abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvwxyz
GOOGLE_CALENDAR_ID=tgstamotolognsp@gmail.com

# Database Configuration
DATABASE_URL=sqlite:///database.db

# Admin Configuration
ADMIN_TELEGRAM_ID=123456789
ADMIN_PASSWORD=my_secret_password_123

# Timezone Configuration
TIMEZONE=Europe/Minsk

# Logging Configuration
LOG_LEVEL=INFO
```


