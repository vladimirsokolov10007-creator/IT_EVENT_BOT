import feedparser
import requests
import re
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

RSS_FEEDS = [
    ('IT-events.com', 'https://it-events.com/ru/events/rss'),
    ('Habr Митапы', 'https://habr.com/ru/rss/hub/meetups/'),
    ('Habr Карьера', 'https://habr.com/ru/rss/hub/career/'),
    ('Habr Обучение', 'https://habr.com/ru/rss/hub/education/'),
]

KEYWORDS = [
    'хакатон', 'олимпиада', 'конкурс', 'митап', 'соревнован', 'чемпионат', 
    'воркшоп', 'квиз', 'hackathon', 'meetup', 'contest', 'coding'
]

LOCATION_KEYWORDS = [
    'москва', 'moscow', 'онлайн', 'online', 'россия', 'russia', 'мск', 
    'спб', 'санкт-петербург', 'удалённ', 'remote'
]

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"  # Используем HTML вместо Markdown
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Сообщение отправлено в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def escape_html(text):
    """Экранирует специальные HTML-символы"""
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
    report = "<b>🗓 ИТ-мероприятия в России (Москва/Онлайн)</b>\n"
    report += f"<i>{datetime.now().strftime('%d.%m.%Y')}</i>\n\n"
    
    events_found = 0
    today = datetime.now()
    next_week = today + timedelta(days=14)
    
    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:30]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                full_text = (title + " " + summary).lower()
                
                has_keyword = any(k in full_text for k in KEYWORDS)
                has_location = any(l in full_text for l in LOCATION_KEYWORDS)
                
                if has_keyword and has_location:
                    parsed_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    
                    if parsed_date:
                        event_date = datetime(*parsed_date[:6])
                        if not (today <= event_date <= next_week):
                            continue
                        date_display = event_date.strftime('%d.%m.%Y')
                    else:
                        date_display = "Дата уточняется"
                    
                    org = entry.get('author', feed_name)
                    link = entry.get('link', '#')
                    prize = extract_prize(summary)
                    theme = extract_theme(full_text)
                    
                    # Экранируем HTML и формируем сообщение
                    safe_title = escape_html(title)
                    safe_org = escape_html(org)
                    
                    report += f"<b>🔹 {safe_title}</b>\n"
                    report += f"📅 <b>Срок проведения:</b> {date_display}\n"
                    report += f"🏢 <b>Организатор:</b> {safe_org}\n"
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
        report = "🔍 <b>На ближайшие 2 недели подходящих событий не найдено.</b>\n\n"
        report += "<i>Попробуйте расширить списки KEYWORDS и LOCATION_KEYWORDS в main.py</i>"
    
    send_to_telegram(report)

if __name__ == "__main__":
    main()
