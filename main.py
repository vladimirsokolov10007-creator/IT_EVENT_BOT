import feedparser
import requests
from datetime import datetime

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

# Источники данных (RSS-ленты). Можете добавлять свои через запятую.
RSS_FEEDS = [
    'https://devpost.com/hackathons.rss',          # Глобальные хакатоны
    'https://habr.com/ru/rss/hub/career/',         # Карьера и образование (Habr)
    'https://events.yandex.ru/api/events/rss/',    # События Яндекса (если доступен)
]

# Ключевые слова для фильтрации (чтобы отсеять лишнее)
KEYWORDS = ['хакатон', 'олимпиада', 'конкурс', 'митап', 'meetup', 'hackathon', 'olympiad', 'соревнован', 'чемпионат']

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Сообщение успешно отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def main():
    report = "🗓 *Свежие ИТ-мероприятия (хакатоны, олимпиады)*\n"
    report += f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    
    events_found = 0

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            # Проверяем последние 20 записей из каждой ленты
            for entry in feed.entries[:20]: 
                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                full_text = title + " " + summary
                
                # Если найдено хотя бы одно ключевое слово
                if any(keyword in full_text for keyword in KEYWORDS):
                    orig_title = entry.get('title', 'Без названия')
                    link = entry.get('link', '#')
                    published = entry.get('published', 'Дата не указана')
                    
                    report += f"🔹 *{orig_title}*\n"
                    report += f"📅 {published}\n"
                    report += f"🔗 [Подробнее]({link})\n\n"
                    events_found += 1
                    
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {feed_url}: {e}")

    if events_found > 0:
        report += f"_Найдено подходящих событий: {events_found}_"
        send_to_telegram(report)
    else:
        send_to_telegram("🔍 На данный момент новых анонсов по заданным ключевым словам не найдено.")

if __name__ == "__main__":
    main()
