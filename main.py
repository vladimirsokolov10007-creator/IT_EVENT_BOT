import requests
import re
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

# Российские RSS-источники (работают без авторизации)
RSS_FEEDS = [
    ('IT-events.com', 'https://it-events.com/ru/events/rss'),
    ('Habr Митапы', 'https://habr.com/ru/rss/hub/meetups/'),
    ('Habr Карьера', 'https://habr.com/ru/rss/hub/career/'),
    ('Habr Обучение', 'https://habr.com/ru/rss/hub/education/'),
]

# Ключевые слова для фильтрации событий
KEYWORDS = [
    'хакатон', 'олимпиада', 'конкурс', 'митап', 'соревнован', 'чемпионат', 
    'воркшоп', 'квиз', 'hackathon', 'meetup', 'contest', 'coding'
]

# Ключевые слова для фильтрации по локации (Москва, онлайн, Россия)
LOCATION_KEYWORDS = [
    'москва', 'moscow', 'онлайн', 'online', 'россия', 'russia', 'мск', 
    'спб', 'санкт-петербург', 'удалённ', 'remote'
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
        print("✅ Сообщение отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def extract_prize(text):
    """Извлекает призовой фонд из текста"""
    if not text: return "Не указан"
    # Ищем паттерны типа "500 000 рублей", "1млн руб", "300к"
    patterns = [
        r'призовой\s+фонд[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)',
        r'выигрыш[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m: return f"💰 {m.group(1).strip()} руб"
    return "Не указан"

def extract_theme(text):
    """Определяет тематику события"""
    themes = {
        'AI/ML': ['искусственн', 'нейросет', 'machine learning', 'ai ', 'chatgpt', 'llm', 'gpt'],
        'Data Science': ['data science', 'анализ данных', 'big data', 'дата сайенс'],
        'Web': ['web', 'веб', 'frontend', 'backend', 'react', 'vue', 'angular'],
        'Mobile': ['mobile', 'мобильн', 'ios', 'android', 'flutter'],
        'GameDev': ['gamedev', 'игров', 'game', 'unity', 'unreal'],
        'Cybersecurity': ['кибербезопас', 'cybersecurity', 'ctf', 'безопас', 'hacking'],
        'FinTech': ['fintech', 'финтех', 'банков', 'платеж'],
        'EdTech': ['edtech', 'образование', 'обучен', 'edu'],
        'IoT': ['iot', 'интернет вещей', 'embedded', 'arduino']
    }
    t = (text or "").lower()
    for theme, kws in themes.items():
        if any(k in t for k in kws): return theme
    return "IT (общая)"

def main():
    report = " *ИТ-мероприятия в России (Москва/Онлайн)*\n"
    report += f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
    
    events_found = 0
    today = datetime.now()
    next_week = today + timedelta(days=14)  # Ищем на 2 недели вперёд
    
    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:30]:  # Проверяем последние 30 записей
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                full_text = (title + " " + summary).lower()
                
                # Проверяем ключевые слова И локацию
                has_keyword = any(k in full_text for k in KEYWORDS)
                has_location = any(l in full_text for l in LOCATION_KEYWORDS)
                
                if has_keyword and has_location:
                    # Извлекаем дату события
                    parsed_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    
                    if parsed_date:
                        event_date = datetime(*parsed_date[:6])
                        # Фильтруем по дате (только будущие события в пределах 2 недель)
                        if not (today <= event_date <= next_week):
                            continue
                        date_display = event_date.strftime('%d.%m.%Y')
                    else:
                        date_display = "Дата уточняется"
                    
                    # Организатор (автор поста или название ленты)
                    org = entry.get('author', feed_name)
                    link = entry.get('link', '#')
                    
                    # Призовой фонд и тематика
                    prize = extract_prize(summary)
                    theme = extract_theme(full_text)
                    
                    # Формируем блок события
                    report += f"🔹 *{title}*\n"
                    report += f" *Срок проведения:* {date_display}\n"
                    report += f"🏢 *Организатор:* {org}\n"
                    report += f"💰 *Призовой фонд:* {prize}\n"
                    report += f" *Тематика:* {theme}\n"
                    report += f"🔗 [Подробнее]({link})\n\n"
                    report += "━" * 15 + "\n\n"
                    
                    events_found += 1
                    if events_found >= 10:  # Ограничение в 10 событий
                        break
                        
        except Exception as e:
            print(f"️ Ошибка при чтении {feed_name}: {e}")
        
        if events_found >= 10:
            break
    
    if events_found > 0:
        report += f"_✅ Найдено событий: {events_found}_"
    else:
        report = "🔍 *На ближайшие 2 недели подходящих событий не найдено.*\n\n"
        report += "_Возможно, в выбранных лентах нет анонсов с ключевыми словами (хакатон, олимпиада, митап) и локацией (Москва, онлайн). Попробуйте расширить списки KEYWORDS и LOCATION_KEYWORDS в main.py._"
    
    send_to_telegram(report)

if __name__ == "__main__":
    main()
