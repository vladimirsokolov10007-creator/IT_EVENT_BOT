import feedparser
import requests
from datetime import datetime

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

# Проверенные и активные RSS-ленты
RSS_FEEDS = [
    ('Devpost Hackathons', 'https://devpost.com/hackathons.rss'),
    ('Habr Карьера', 'https://habr.com/ru/rss/hub/career/'),
    ('Habr Обучение', 'https://habr.com/ru/rss/hub/education/'),
    ('Dev.to Hackathons', 'https://dev.to/feed/tag/hackathon')
]

# Ключевые слова (расширенный список, ищем и в заголовке, и в описании)
KEYWORDS = [
    'хакатон', 'олимпиада', 'конкурс', 'митап', 'соревнован', 'чемпионат',
    'hackathon', 'olympiad', 'meetup', 'contest', 'coding', 'квиз'
]

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
    report = "🗓 *Свежие ИТ-мероприятия*\n"
    report += f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    
    events_found = 0
    debug_info = "" # Для отладки, если ничего не найдено

    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            # Проверяем последние 15 записей из каждой ленты
            for entry in feed.entries[:15]: 
                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                full_text = title + " " + summary
                
                # Сохраняем заголовки для отладки (покажем последние 2 из каждой ленты)
                debug_info += f"  • {entry.get('title', 'Без названия')[:60]}...\n"

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
            print(f"⚠️ Ошибка при чтении {feed_name}: {e}")

    if events_found > 0:
        report += f"_✅ Найдено событий: {events_found}_"
        send_to_telegram(report)
    else:
        # Если ничего не найдено, показываем, что вообще есть в лентах, чтобы понять причину
        debug_report = "🔍 *Новых анонсов по ключевым словам не найдено.*\n\n"
        debug_report += "Возможно, за последние дни не было публикаций. Вот последние заголовки в лентах, чтобы вы понимали, что бот работает:\n\n"
        debug_report += debug_info
        debug_report += "\n_Попробуйте расширить список ключевых слов в main.py или добавьте новые RSS-источники._"
        send_to_telegram(debug_report)

if __name__ == "__main__":
    main()
