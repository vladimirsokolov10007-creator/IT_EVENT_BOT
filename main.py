import feedparser
import requests
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U'
CHAT_ID = '-1004445860179'

# --- ОСНОВНЫЕ СОРЕВНОВАТЕЛЬНЫЕ КЛЮЧЕВЫЕ СЛОВА ---
# События ДОЛЖНЫ содержать хотя бы одно из них
CORE_COMPETITION_KEYWORDS = [
    "хакатон", "hackathon",
    "олимпиада", "olympiad",
    "чемпионат", "championship",
    "турнир", "tournament",
    "ctf", "capture the flag",
    "gamejam", "game jam",
]

# Всероссийские и известные ИТ конкурсы
RUSSIAN_COMPETITIONS = [
    "цифровой прорыв",
    "лидеры цифровой трансформации",
    "it-планета",
    "россия — страна возможностей",
]

# Признаки возможности регистрации
REGISTRATION_KEYWORDS = [
    "регистр", "register", "signup", "sign-up",
    "участие", "submit", "apply", "заявка", "подать",
    "участвуй", "join", "зарегистриров", "приём",
]

# Слова-исключения: если они есть в заголовке — скипаем
EXCLUDE_KEYWORDS = [
    "вебинар", "webinar",
    "лекция", "lecture",
    "курс", "course",
    "мастер-класс", "workshop",
    "митап", "meetup",
    "конференция", "conference",
    "подкаст", "podcast",
    "стрим", "stream",
    "трансляция",
    "как стать",
    "обучение",
    "семинар", "семёнар",
]

# Ключевые слова для определения тематики
THEME_KEYWORDS = {
    "Web": ["web", "вебсайт", "фронтенд", "backend", "fullstack"],
    "AI/ML": ["ai", "ml", "нейросеть", "искусственный интеллект", "machine learning", "deep learning"],
    "Блокчейн": ["блокчейн", "blockchain", "crypto", "крипто", "web3"],
    "Мобильное приложение": ["android", "ios", "мобильное приложение", "мобильн"],
    "Киберспорт": ["киберспорт", "esports", "gaming"],
    "IoT": ["iot", "интернет вещей", "embedded"],
    "DevOps": ["devops", "cloud", "облачн", "kubernetes", "docker"],
    "Кибербезопасность": ["кибербезопасность", "security", "безопасность", "ctf"],
    "Data Science": ["data science", "big data", "данные", "анализ данных"],
    "Разработка ПО": ["разработка", "программирование", "разработка ПО"],
}

# RSS-ленты — только профильные источники
RSS_FEEDS = [
    ('Habr Хакатоны', 'https://habr.com/ru/rss/hub/hackathons/'),
    ('IT-events.com', 'https://it-events.com/ru/events/rss'),
]


def send_to_telegram(message: str):
    """Отправляет сообщение в Telegram, разбивая на части если > 4096 символов."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Telegram лимит — 4096 символов
    max_len = 4000
    parts = []
    while len(message) > max_len:
        split_at = message.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(message[:split_at])
        message = message[split_at:]
    parts.append(message)

    for part in parts:
        payload = {
            "chat_id": CHAT_ID,
            "text": part,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Часть сообщения отправлена в Telegram!")
        except Exception as e:
            print(f"❌ Ошибка Telegram: {e}")


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def extract_prize(text: str) -> str:
    """Ищет упоминание призового фонда в тексте."""
    if not text:
        return None
    patterns = [
        r'призовой\s+фонд[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'фонд[:\s]*([\d\s]+(?:тыс|млн)?)\s*(?:руб|₽)',
        r'([\d\s]{3,}(?:тыс|млн)?)\s*(?:руб|₽)',
        r'prize[:\s]*([\d\s]+(?:k|m)?)\s*(?:rub|₽|rur)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount = m.group(1).strip()
            return f"{amount} руб."
    return None


def extract_date_from_text(text: str):
    """Пробует найти дату мероприятия прямо в тексте."""
    months = {
        'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4,
        'май': 5, 'ма': 5, 'июн': 6, 'июл': 7, 'август': 8,
        'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
    }
    # Пример: "15 июня 2025" или "15-17 июня"
    pattern = r'(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s+([а-яё]+)\s*(\d{4})?'
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()[:5]
        year = int(m.group(3)) if m.group(3) else datetime.now().year
        for key, num in months.items():
            if month_str.startswith(key[:3]):
                try:
                    return datetime(year, num, day)
                except ValueError:
                    pass
    return None


def extract_organizer(text: str) -> str:
    """Пробует извлечь организатора из текста."""
    patterns = [
        r'организатор[:\s]*([^,\n]+)',
        r'организ[\.а-яё]*[:\s]*([^,\n]+)',
        r'от[:\s]*([^,\n]+?)(?:\n|,|$)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            org = m.group(1).strip()
            if len(org) < 100 and org.strip():
                return org
    return "Не указан"


def extract_location(text: str) -> str:
    """Пробует извлечь место проведения из текста."""
    patterns = [
        r'место[:\s]*([^,\n]+)',
        r'адрес[:\s]*([^,\n]+)',
        r'город[:\s]*([^,\n]+)',
        r'формат[:\s]*([^,\n]+)',
        r'отель[:\s]*([^,\n]+)',
        r'(онлайн|очно|гибридно|дистанционно)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            loc = m.group(1).strip()
            if len(loc) < 100:
                return loc
    return None


def extract_registration_deadline(text: str) -> str:
    """Пробует найти deadline регистрации в тексте."""
    patterns = [
        r'регистрац[^:]*[:\s]*до\s+(\d{1,2}\s+[а-яё]+\s+\d{4})',
        r'регистрация[:\s]*до\s+(\d{1,2}\s+[а-яё]+)',
        r'срок\s+регистр[^:]*[:\s]*(\d{1,2}\s+[а-яё]+)',
        r'до\s+(\d{1,2}\s+[а-яё]+\s*\d{4}?)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            deadline = m.group(1).strip()
            if deadline:
                return deadline
    return "Уточняется"


def extract_theme(title: str, text: str) -> str:
    """Определяет тематику конкурса на основе ключевых слов."""
    full = (title + " " + text).lower()
    
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in full:
                return theme
    
    return "Общая тематика"


def is_competition(title: str, summary: str) -> bool:
    """
    Проверяет, является ли запись реальным конкурсом/олимпиадой с возможностью регистрации.
    """
    full = (title + " " + summary).lower()
    title_lower = title.lower()
    
    # 1️⃣ ОБЯЗАТЕЛЬНО исключаем события, которые НЕ соревнования
    if any(excl in title_lower for excl in EXCLUDE_KEYWORDS):
        return False
    
    # 2️⃣ Проверяем основные соревновательные ключевые слова
    has_core_keyword = any(kw in full for kw in CORE_COMPETITION_KEYWORDS)
    
    # 3️⃣ ИЛИ известные всероссийские конкурсы
    has_russian_competition = any(kw in full for kw in RUSSIAN_COMPETITIONS)
    
    # 4️⃣ Проверяем признаки регистрации
    has_registration = any(kw in full for kw in REGISTRATION_KEYWORDS)
    
    # ИТОГОВАЯ ЛОГИКА:
    if has_core_keyword and has_registration:
        return True
    
    if has_russian_competition and has_registration:
        return True
    
    if has_core_keyword and ('участи' in full or 'заявк' in full or 'приём' in full):
        return True
    
    return False


def parse_rss_feeds():
    """Парсит RSS-ленты и возвращает список мероприятий."""
    events = []
    seen_titles = set()

    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url, request_headers={
                'User-Agent': 'Mozilla/5.0 (compatible; IT-Event-Bot/1.0)'
            })
            print(f"📡 {feed_name}: получено {len(feed.entries)} записей")

            for entry in feed.entries[:30]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '')

                # Убираем HTML-теги из summary
                if summary:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary = soup.get_text(separator=' ')

                if not title or title in seen_titles:
                    continue

                if not is_competition(title, summary):
                    continue

                seen_titles.add(title)

                full_text = title + " " + summary

                # Базовая информация
                link = entry.get('link', '')
                organizer = extract_organizer(full_text)
                prize = extract_prize(full_text)
                if not prize:
                    prize = "Без призового фонда"
                registration_deadline = extract_registration_deadline(full_text)
                theme = extract_theme(title, full_text)

                events.append({
                    'title': title,
                    'organizer': organizer,
                    'prize': prize,
                    'registration_deadline': registration_deadline,
                    'theme': theme,
                    'link': link,
                })

        except Exception as e:
            print(f"⚠️ Ошибка при чтении {feed_name}: {e}")

    return events


def parse_hackathons_rfc():
    """Парсит сайт хакрус (хакатоны.рф) через HTTP."""
    events = []
    try:
        url = "https://www.xn--80aa3anexr8c.xn--p1ai/"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; IT-Event-Bot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем карточки мероприятий
        cards = soup.find_all(['div', 'article'], class_=re.compile(r'event|card|item|hack', re.I))
        print(f"📡 Хакатоны.рф: найдено {len(cards)} карточек")

        for card in cards[:15]:
            title_el = card.find(['h2', 'h3', 'h4', 'a'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            text = card.get_text(separator=' ')
            if not is_competition(title, text):
                continue

            link_el = card.find('a', href=True)
            link = link_el['href'] if link_el else url
            if link.startswith('/'):
                link = "https://www.xn--80aa3anexr8c.xn--p1ai" + link

            full_text = title + " " + text
            organizer = extract_organizer(full_text)
            prize = extract_prize(full_text)
            if not prize:
                prize = "Без призового фонда"
            registration_deadline = extract_registration_deadline(full_text)
            theme = extract_theme(title, full_text)

            events.append({
                'title': title,
                'organizer': organizer,
                'prize': prize,
                'registration_deadline': registration_deadline,
                'theme': theme,
                'link': link,
            })

    except Exception as e:
        print(f"⚠️ Ошибка при парсинге Хакатоны.рф: {e}")

    return events


def parse_rsv():
    """Парсит раздел конкурсов с rsv.ru (Россия — страна возможностей)."""
    events = []
    try:
        url = "https://rsv.ru/competitions/"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; IT-Event-Bot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        cards = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'card|item|competi|event', re.I))
        print(f"📡 RSV.ru: найдено {len(cards)} карточек")

        for card in cards[:10]:
            title_el = card.find(['h2', 'h3', 'h4', 'a', 'span'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            text = card.get_text(separator=' ')
            text_lower = text.lower()

            # 1️⃣ Фильтр — только ИТ тематика
            if not any(kw in text_lower for kw in [
                'ит', 'it', 'цифров', 'программ', 'разработ', 'техно', 'данн',
                'конкурс', 'олимпиад', 'чемпион', 'хакатон'
            ]):
                continue

            # 2️⃣ Обязательно — признаки регистрации/участия
            if not any(kw in text_lower for kw in REGISTRATION_KEYWORDS):
                continue

            # 3️⃣ Применяем основной фильтр соревнований
            if not is_competition(title, text):
                continue

            link_el = card.find('a', href=True)
            link = link_el['href'] if link_el else url
            if link.startswith('/'):
                link = "https://rsv.ru" + link

            full_text = title + " " + text
            organizer = extract_organizer(full_text)
            prize = extract_prize(full_text)
            if not prize:
                prize = "Без призового фонда"
            registration_deadline = extract_registration_deadline(full_text)
            theme = extract_theme(title, full_text)

            events.append({
                'title': title,
                'organizer': organizer,
                'prize': prize,
                'registration_deadline': registration_deadline,
                'theme': theme,
                'link': link,
            })

    except Exception as e:
        print(f"⚠️ Ошибка при парсинге RSV: {e}")

    return events


def build_report(events: list) -> str:
    """Строит отчет в едином формате для всех событий."""
    today_str = datetime.now().strftime('%d.%m.%Y')
    report = f"<b>🏆 ИТ-соревнования, олимпиады и конкурсы</b>\n"
    report += f"<i>Подборка на {today_str}</i>\n"
    report += f"<i>Только события с возможностью регистрации</i>\n\n"

    if not events:
        report += "😔 <b>Активных конкурсов/олимпиад не найдено</b>\n\n"
        report += "Попробуйте запустить позже или проверьте источники."
        return report

    for i, ev in enumerate(events[:15], 1):
        title = escape_html(ev['title'])
        organizer = escape_html(ev.get('organizer', 'Не указан'))
        prize = escape_html(ev.get('prize', 'Без призового фонда'))
        registration_deadline = escape_html(ev.get('registration_deadline', 'Уточняется'))
        theme = escape_html(ev.get('theme', 'Общая тематика'))
        link = ev.get('link', '')

        # Единая структура для всех событий
        report += f"<b>{i}. {title}</b>\n"
        report += f"👤 Организатор: {organizer}\n"
        report += f"💰 Призовой фонд: {prize}\n"
        report += f"📌 Срок регистрации: {registration_deadline}\n"
        report += f"🎯 Тематика: {theme}\n"
        
        if link:
            report += f"<a href='{link}'>→ Ссылка на регистрацию</a>\n"
        
        report += "\n"

    report += f"<i>Всего найдено: {len(events)} соревнований</i>"
    return report


def main():
    print(f"🚀 Запуск бота {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    all_events = []

    # 1. RSS-ленты (Habr хакатоны + it-events)
    print("\n1️⃣ Парсим RSS-ленты...")
    all_events += parse_rss_feeds()

    # 2. Хакатоны.рф
    print("\n2️⃣ Парсим Хакатоны.рф...")
    all_events += parse_hackathons_rfc()

    # 3. Россия — страна возможностей (конкурсы)
    print("\n3️⃣ Парсим RSV.ru...")
    all_events += parse_rsv()

    # Дедупликация по заголовку
    seen = set()
    unique_events = []
    for ev in all_events:
        key = ev['title'].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    print(f"\n✅ Найдено уникальных мероприятий: {len(unique_events)}")

    report = build_report(unique_events)
    send_to_telegram(report)


if __name__ == "__main__":
    main()
