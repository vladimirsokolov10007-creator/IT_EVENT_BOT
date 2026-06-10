import feedparser
import requests
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()
        print("✅ Сообщение отправлено!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    # Простой тест без Markdown
    message = "🗓 ИТ-мероприятия\n\n"
    message += "🔹 Тестовое событие\n"
    message += "📅 Дата: 15.06.2026\n"
    message += "🏢 Организатор: Тест\n"
    message += "💰 Приз: 100000 руб\n"
    message += "🎯 Тематика: AI\n"
    message += "🔗 Ссылка: https://example.com\n\n"
    message += "✅ Найдено: 1 событие"
    
    send_to_telegram(message)

if __name__ == "__main__":
    main()
