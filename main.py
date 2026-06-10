import feedparser
import requests
from datetime import datetime

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

# РОССИЙСКИЕ ИСТОЧНИКИ (Timepad, Habr и др.)
RSS_FEEDS = [
    ('Timepad IT Москва', 'https://timepad.ru/api/2/events/?search[city_id]=1&search[is_free]=false&search[limit]=20&search[order_by]=start_date&search[status]=active&search[tags]=it'),
    ('Habr Митапы', 'https://habr.com/ru/rss/hub/meetups/'),
    ('Habr Карьера', 'https://habr.com/ru/rss/hub/career/'),
    ('Habr Обучение', 'https://habr.com/ru/rss/hub/education/'),
    ('VC.ru Мероприятия', 'https://vc.ru/rss'),
]

# Ключевые слова для российских событий
KEYWORDS = [
    'хакатон', 'олимпиада', 'конкурс', 'митап', 'соревнован', 'чемпионат', 'конференц',
    'воркшоп', 'мк', 'мастер-класс', 'встреча', 'митап', 'хакатон', 'coding', 'программирован',
    'hackathon', 'meetup', 'olympiad', 'квиз', 'чемпионат'
]

# Ключевые слова для фильтрации по Москве/России
LOCATION_KEYWORDS = ['москва', 'moscow', 'онлайн', 'online', 'россия', 'russia', 'мск']

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
    report = "🗓 *ИТ-мероприятия в Москве и онлайн*\n"
    report += f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    
    events_found = 0
    debug_info = ""

    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]: 
                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                full_text = title + " " + summary
                
                # Проверяем наличие ключевых слов И локацию (Москва/онлайн/Россия)
                has_keyword = any(keyword in full_text for keyword in KEYWORDS)
                has_location = any(loc in full_text for loc in LOCATION_KEYWORDS)
                
                # Сохраняем для отладки
                if len(debug_info.split('\n')) < 10:  # Только первые 10 заголовков
                    debug_info += f"  • {entry.get('title', 'Без названия')[:60]}...\n"

                if has_keyword and has_location:
                    orig_title = entry.get('title', 'Без названия')
                    link = entry.get('link', '#')
                    published = entry.get('published', 'Дата не указана')
                    
                    report += f"🔹 *{orig_title}*\n"
                    report += f"📅 {published}\n"
                    report += f"🔗 [Подробнее]({link})\n\n"
                    events_found += 1
                    
                    # Ограничим 10 событиями, чтобы не спамить
                    if events_found >= 10:
                        break
                        
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {feed_name}: {e}")
        
        if events_found >= 10:
            break

    if events_found > 0:
        report += f"_✅ Найдено событий: {events_found}_"
        send_to_telegram(report)
    else:
        debug_report = "🔍 *Новых анонсов по ключевым словам не найдено.*\n\n"
        debug_report += "Последние заголовки в лентах:\n\n"
        debug_report += debug_info
        debug_report += "\n_Попробуйте расширить список ключевых слов в main.py_"
        send_to_telegram(debug_report)

if __name__ == "__main__":
    main()
