#!/usr/bin/env python3
"""
Скрипт для получения Refresh Token для Google Calendar API.

ВАЖНО: Перед запуском убедитесь, что:
1. OAuth приложение опубликовано ИЛИ вы добавлены как тестировщик
2. GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET установлены в .env

Если получаете ошибку 403: access_denied:
1. Зайдите в Google Cloud Console
2. APIs & Services > OAuth consent screen
3. Добавьте ваш email в "Test users" ИЛИ опубликуйте приложение
4. Запустите скрипт снова
"""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

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
print("\n⚠️  ВАЖНО:")
print("   Если приложение в тестовом режиме, убедитесь что ваш email добавлен как тестировщик")
print("   или опубликуйте приложение в Google Cloud Console")
print("\nОткроется браузер для авторизации...")

try:
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

    if not credentials.refresh_token:
        print("\n❌ Ошибка: Refresh Token не получен")
        print("   Возможно, приложение уже было авторизовано ранее")
        print("   Попробуйте отозвать доступ и авторизоваться заново")
        exit(1)

    print("\n✅ Авторизация успешна!")
    print("\n📋 Скопируйте следующую строку в ваш .env файл:")
    print(f"\nGOOGLE_REFRESH_TOKEN={credentials.refresh_token}")
    print("\n💡 Сохраните Refresh Token в .env файле!")
    print("   После этого бот сможет работать с Google Calendar.")

except Exception as e:
    if "access_denied" in str(e) or "403" in str(e):
        print("\n❌ Ошибка 403: access_denied")
        print("\n🔧 Решение:")
        print("1. Зайдите в Google Cloud Console:")
        print("   https://console.cloud.google.com/apis/credentials/consent")
        print("2. Перейдите в 'OAuth consent screen'")
        print("3. Добавьте ваш email в раздел 'Test users'")
        print("   ИЛИ опубликуйте приложение (Publish App)")
        print("4. Подождите несколько минут и запустите скрипт снова")
        print("\n💡 Если приложение уже опубликовано, проверьте:")
        print("   - Правильность CLIENT_ID и CLIENT_SECRET")
        print("   - Наличие прав доступа к Google Calendar API")
    else:
        print(f"\n❌ Ошибка: {e}")
    exit(1)


