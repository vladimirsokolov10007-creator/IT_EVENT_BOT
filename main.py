import feedparser
import requests
import re
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

# Расширенный список источников
RSS_FEEDS = [
    ('IT-events.com', 'https://it-events.com/ru/events/rss'),
    ('Habr Митапы', 'https://habr.com/ru/rss/hub/meetups/'),
    ('Habr Карьера', 'https://habr.com/ru/rss/hub/career/'),
    ('Habr Обучение', 'https://habr.com/ru/rss/hub/education/'),
    ('Habr IT', 'https://habr.com/ru/rss/all/'),
    ('АНО «Россия — страна возможностей»', 'https://rsv.ru/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('Timepad', 'https://timepad.ru/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('Aroundo', 'https://aroundo.ru/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('Олимпиада «IT-Планета»', 'https://www.it-planeta.org/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('TAdviser', 'https://www.tadviser.ru/index.php/Article:Календарь_мероприятий?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('CNews', 'https://events.cnews.ru/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
    ('VC.ru', 'https://vc.ru/?spm=a2ty_o01.29997173.0.0.6feb55fb35LYbw'),
]

# Расширенные ключевые слова (теперь ищем ИЛИ, не И)
KEYWORDS = [
    # Типы мероприятий
    "хакатон", "hackathon",
    "олимпиада", "olympiad",
    "чемпионат", "championship", 
    "конкурс", "competition",
    "турнир", "tournament",
    "CTF", "capture the flag",
    "митап", "meetup",
    "конференция", "conference",
    "фестиваль", "festival",
    "GameJam",
    
    # Направления ИТ
    "программирование", "programming",
    "разработка", "development",
    "искусственный интеллект", "AI", "машинное обучение", "ML",
    "кибербезопасность", "cybersecurity", "информационная безопасность",
    "веб-разработка", "web development",
    "мобильная разработка", "mobile development",
    "анализ данных", "data science",
    "блокчейн", "blockchain",
    "робототехника", "robotics",
    "IoT", "интернет вещей",
    
    # Форматы участия
    "онлайн", "online",
    "офлайн", "очный", "offline",
    "гибридный", "hybrid",
    "для студентов", "для школьников",
    "для начинающих", "junior",
    
    # Организаторы и платформы
    "Цифровой прорыв",
    "IT-Планета",
    "Россия — страна возможностей",
    "Codenrock",
    "Timepad",
    
    # Специальные слова
    "призовой фонд",
    "регистрация",
    "дедлайн",
    "старт",
    "начало",
    "анонс",
    "соревнование"
]

# Локация (опционально - если не найдём, всё равно покажем)
LOCATION_KEYWORDS = [
    'москва', 'moscow', 'онлайн', 'online', 'россия', 'russia', 'мск', 
    'спб', 'санкт-петербург', 'удалённ', 'remote', 'дистанцион'
]

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Сообщение отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def escape_html(text):
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

def extract_prize(text):
    if not text: 
        return "Не указан"
    patterns = [
        r'призовой\s+фонд[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)',
        r'выигрыш[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m: 
            return f"💰 {m.group(1).strip()} руб"
    return "Не указан"

def extract_theme(text):
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
        if any(k in t for k in kws): 
            return theme
    return "IT (общая)"

def main():
    report = "<b>🗓 ИТ-мероприятия</b>\n"
    report += f"<i>{datetime.now().strftime('%d.%m.%Y')}</i>\n\n"
    
    events_found = 0
    debug_info = []
    today = datetime.now()
    next_week = today + timedelta(days=30)  # Расширили до 30 дней
    
    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                full_text = (title + " " + summary).lower()
                
                # Проверяем ключевые слова (ОДНО из списка достаточно)
                has_keyword = any(k in full_text for k in KEYWORDS)
                
                # Проверяем локацию (опционально)
                has_location = any(l in full_text for l in LOCATION_KEYWORDS)
                
                # Сохраняем для отладки
                if len(debug_info) < 5:
                    debug_info.append(f"• {title[:80]}")
                
                # Теперь принимаем событие, если есть ключевое слово (локация опциональна)
                if has_keyword:
                    parsed_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    if parsed_date:
                        date_display = datetime(*parsed_date[:6]).strftime('%d.%m.%Y')
                    else:
                        date_display = "Дата уточняется"
    
                    org = entry.get('author', feed_name)
                    link = entry.get('link', '#')
                    prize = extract_prize(summary)
                    theme = extract_theme(full_text)
    
                    safe_title = escape_html(title)
                    safe_org = escape_html(org)
    
                    report += f"<b>🔹 {safe_title}</b>\n"
                    report += f"📅 <b>Дата публикации:</b> {date_display}\n"
                    report += f"🏢 <b>Источник:</b> {safe_org}\n"
                    report += f"💰 <b>Призовой фонд:</b> {prize}\n"
                    report += f"🎯 <b>Тематика:</b> {theme}\n"
                    report += f"🔗 <a href='{link}'>Подробнее</a>\n\n"
                    report += "━━━━━━━━━━━━━━━━\n\n"
    
                    events_found += 1
                    if events_found >= 10:
                        break
                        
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {feed_name}: {e}")
        
        if events_found >= 10:
            break
    
    if events_found > 0:
        report += f"<i>✅ Найдено событий: {events_found}</i>"
    else:
        # Если ничего не найдено, показываем отладочную информацию
        report = "🔍 <b>События не найдены.</b>\n\n"
        report += "<b>Последние заголовки в RSS-лентах:</b>\n\n"
        for item in debug_info:
            report += f"{escape_html(item)}\n"
        report += "\n<i>Попробуйте расширить KEYWORDS в main.py</i>"
    
    send_to_telegram(report)

if __name__ == "__main__":
    main()
