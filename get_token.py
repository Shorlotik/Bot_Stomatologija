#!/usr/bin/env python3
"""
Скрипт для получения Refresh Token для Google Calendar API.
Запустите этот скрипт после настройки GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET в .env
"""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Загружаем переменные окружения
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Ошибка: GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET должны быть установлены в .env файле")
    print("\nПожалуйста, сначала:")
    print("1. Создайте .env файл из .env.example")
    print("2. Заполните GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET")
    print("3. Запустите этот скрипт снова")
    exit(1)

print("🔐 Настройка OAuth 2.0 для Google Calendar API")
print("\nОткроется браузер для авторизации...")

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

# Запускаем локальный сервер для авторизации
credentials = flow.run_local_server(port=0)

print("\n✅ Авторизация успешна!")
print("\n📋 Скопируйте следующие значения в ваш .env файл:")
print(f"\nGOOGLE_REFRESH_TOKEN={credentials.refresh_token}")

if credentials.token:
    print(f"\nAccess Token (временный, не нужен для .env): {credentials.token[:20]}...")

print("\n💡 Сохраните Refresh Token в .env файле!")
print("   После этого бот сможет работать с Google Calendar.")


