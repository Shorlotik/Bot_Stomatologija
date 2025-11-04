# Инструкция по запуску бота в Docker

## Предварительные требования

1. Установите [Docker](https://docs.docker.com/get-docker/)
2. Установите [Docker Compose](https://docs.docker.com/compose/install/)
3. Создайте файл `.env` с настройками (см. SETUP.md)

## Быстрый старт

### 1. Создайте файл .env

```bash
cp .env.example .env
# Отредактируйте .env и заполните все необходимые переменные
```

### 2. Соберите и запустите контейнер

```bash
docker-compose up -d --build
```

### 3. Проверьте логи

```bash
docker-compose logs -f bot
```

### 4. Остановите бота

```bash
docker-compose down
```

## Детальная инструкция

### Сборка образа

```bash
docker-compose build
```

### Запуск в фоновом режиме

```bash
docker-compose up -d
```

### Просмотр логов

```bash
# Все логи
docker-compose logs bot

# Следить за логами в реальном времени
docker-compose logs -f bot

# Последние 100 строк
docker-compose logs --tail=100 bot
```

### Остановка и удаление

```bash
# Остановить контейнер
docker-compose stop

# Остановить и удалить контейнер
docker-compose down

# Остановить, удалить контейнер и volumes (БД будет удалена!)
docker-compose down -v
```

### Перезапуск бота

```bash
docker-compose restart bot
```

### Обновление бота

```bash
# Остановить
docker-compose down

# Получить последние изменения (если используете git)
git pull

# Пересобрать и запустить
docker-compose up -d --build
```

## Работа с базой данных

### Просмотр базы данных

База данных SQLite сохраняется в файле `database.db` в корне проекта.

### Резервное копирование

```bash
# Создать бэкап
cp database.db database.db.backup

# Восстановить из бэкапа
cp database.db.backup database.db
```

### Инициализация базы данных

Если нужно инициализировать БД заново:

```bash
docker-compose exec bot python -c "from database.migrations import init_db; init_db()"
```

## Использование PostgreSQL (опционально)

Для production рекомендуется использовать PostgreSQL вместо SQLite.

### 1. Раскомментируйте секцию postgres в docker-compose.yml

### 2. Обновите DATABASE_URL в .env:

```env
DATABASE_URL=postgresql://bot_user:bot_password@postgres:5432/bot_db
```

### 3. Пересоберите и запустите:

```bash
docker-compose up -d --build
```

## Troubleshooting

### Бот не запускается

1. Проверьте логи:
   ```bash
   docker-compose logs bot
   ```

2. Проверьте .env файл:
   ```bash
   docker-compose config
   ```

3. Проверьте, что все переменные заполнены:
   ```bash
   cat .env
   ```

### Ошибки подключения к Google Calendar

1. Проверьте, что GOOGLE_REFRESH_TOKEN актуален
2. Если нужно, получите новый токен:
   ```bash
   docker-compose exec bot python get_token.py
   ```

### Проблемы с правами доступа

```bash
# Исправьте права на файлы
sudo chown -R $USER:$USER .
chmod -R 755 .
```

## Мониторинг

### Проверка статуса контейнера

```bash
docker-compose ps
```

### Использование ресурсов

```bash
docker stats telegram_bot_stomatolog
```

### Вход в контейнер

```bash
docker-compose exec bot bash
```

## Автозапуск при перезагрузке сервера

Docker Compose автоматически перезапускает контейнер при перезагрузке сервера (благодаря `restart: unless-stopped`).

## Production рекомендации

1. Используйте PostgreSQL вместо SQLite
2. Настройте регулярные бэкапы базы данных
3. Используйте secrets для хранения паролей (Docker Secrets)
4. Настройте мониторинг (например, через healthcheck)
5. Используйте reverse proxy (nginx) для дополнительной защиты

### Пример healthcheck в docker-compose.yml:

```yaml
services:
  bot:
    # ... остальные настройки
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('https://api.telegram.org/bot${BOT_TOKEN}/getMe')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```


