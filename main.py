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
        r'от[:\s]*([^,\n]+?)(?:\n|,|$)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            org = m.group(1).strip()
            if len(org) < 100:
                return org
    return None


def extract_location(text: str) -> str:
    """Пробует извлечь место проведения из текста."""
    patterns = [
        r'место[:\s]*([^,\n]+)',
        r'адрес[:\s]*([^,\n]+)',
        r'город[:\s]*([^,\n]+)',
        r'формат[:\s]*([^,\n]+)',
        r'отель[:\s]*([^,\n]+)',
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
        r'регистрац[^:]*[:\s]*до\s+(\d{1,2}[а-яё]*\s+\d{4})',
        r'до\s+(\d{1,2}[а-яё\s]*\d{4})\s*(?:года|г\.)',
        r'регистрация[^:]*до\s+(\d{1,2})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            deadline = m.group(1).strip()
            return deadline
    return None


def is_competition(title: str, summary: str) -> bool:
    """
    Проверяет, является ли запись реальным конкурсом/олимпиадой с возможностью регистрации.
    Требует:
    1. Наличие основного соревновательного слова (хакатон, олимпиада, чемпионат, турнир и т.д.)
    2. Признаки регистрации (регистр, участие, заявка и т.д.)
    3. Отсутствие слов-исключений (вебинар, лекция, курс и т.д.)
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
    # Если есть основное соревновательное слово + признаки регистрации
    if has_core_keyword and has_registration:
        return True
    
    # Или известный российский конкурс с регистрацией
    if has_russian_competition and has_registration:
        return True
    
    # Для очень явных соревнований (хакатон, олимпиада) — даже без явного слова "регистр"
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

                # Дата публикации
                parsed_date = entry.get('published_parsed') or entry.get('updated_parsed')
                if parsed_date:
                    pub_date = datetime(*parsed_date[:6])
                    pub_date_str = pub_date.strftime('%d.%m.%Y')
                else:
                    pub_date_str = "Дата уточняется"

                # Попытка найти дату мероприятия в тексте
                event_date = extract_date_from_text(summary) or extract_date_from_text(title)
                if event_date:
                    event_date_str = event_date.strftime('%d.%m.%Y')
                else:
                    event_date_str = pub_date_str

                prize = extract_prize((title + " " + summary).lower())
                link = entry.get('link', '')
                organizer = extract_organizer(summary)
                location = extract_location(summary)
                registration_deadline = extract_registration_deadline(summary)

                events.append({
                    'title': title,
                    'date': event_date_str,
                    'prize': prize,
                    'link': link,
                    'source': feed_name,
                    'summary': summary[:300],
                    'organizer': organizer,
                    'location': location,
                    'registration_deadline': registration_deadline,
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

            # Проверяем, что это реальный хакатон/конкурс
            text = card.get_text(separator=' ')
            if not is_competition(title, text):
                continue

            link_el = card.find('a', href=True)
            link = link_el['href'] if link_el else url
            if link.startswith('/'):
                link = "https://www.xn--80aa3anexr8c.xn--p1ai" + link

            prize = extract_prize(text)
            event_date = extract_date_from_text(text)
            date_str = event_date.strftime('%d.%m.%Y') if event_date else "Уточняется"
            organizer = extract_organizer(text)
            location = extract_location(text)
            registration_deadline = extract_registration_deadline(text)

            events.append({
                'title': title,
                'date': date_str,
                'prize': prize,
                'link': link,
                'source': 'Хакатоны.рф',
                'summary': text[:200],
                'organizer': organizer,
                'location': location,
                'registration_deadline': registration_deadline,
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

            event_date = extract_date_from_text(text)
            date_str = event_date.strftime('%d.%m.%Y') if event_date else "Уточняется"
            prize = extract_prize(text)
            organizer = extract_organizer(text)
            location = extract_location(text)
            registration_deadline = extract_registration_deadline(text)

            events.append({
                'title': title,
                'date': date_str,
                'prize': prize,
                'link': link,
                'source': 'Россия — страна возможностей',
                'summary': text[:200],
                'organizer': organizer,
                'location': location,
                'registration_deadline': registration_deadline,
            })

    except Exception as e:
        print(f"⚠️ Ошибка при парсинге RSV: {e}")

    return events


def build_report(events: list) -> str:
    """Строит красивый отчет с событиями в формате карточек."""
    today_str = datetime.now().strftime('%d.%m.%Y')
    report = f"<b>🏆 ИТ-соревнования, олимпиады и конкурсы</b>\n"
    report += f"<i>Подборка на {today_str}</i>\n"
    report += f"<i>Только события с возможностью регистрации</i>\n"
    report += "\n"

    if not events:
        report += "😔 <b>Активных конкурсов/олимпиад не найдено</b>\n\n"
        report += "Попробуйте запустить позже или проверьте источники."
        return report

    for i, ev in enumerate(events[:15], 1):
        title = escape_html(ev['title'])
        date = ev['date']
        link = ev['link']
        source = escape_html(ev['source'])
        prize = ev.get('prize')
        organizer = ev.get('organizer')
        location = ev.get('location')
        registration_deadline = ev.get('registration_deadline')

        # Строим карточку события
        report += f"<b>{i}. {title}</b>\n"
        
        # Дата проведения
        report += f"📅 {date}\n"
        
        # Deadline регистрации
        if registration_deadline:
            report += f"🔔 Регистрация: до {escape_html(registration_deadline)}\n"
        
        # Организатор
        if organizer:
            report += f"📌 Организатор: {escape_html(organizer)}\n"
        
        # Место проведения
        if location:
            report += f"📍 {escape_html(location)}\n"
        
        # Призовой фонд
        if prize:
            report += f"💰 Призовой фонд: {escape_html(prize)}\n"
        
        # Источник
        report += f"🔗 Источник: <b>{source}</b>\n"
        
        # Ссылка на регистрацию
        if link:
            report += f"<a href='{link}'>→ Подробнее и регистрация</a>\n"
        
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
