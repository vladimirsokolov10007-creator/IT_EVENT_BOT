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

# Слова-исключения: если они есть в заголовке — пропускаем
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
    "Разработка ПО": ["разработка", "программирование", "разработка по"],
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
    """Экранирует HTML-символы в тексте."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def clean_text(text: str, max_length: int = 80) -> str:
    """Очищает текст от лишних символов и обрезает до нужной длины."""
    if not text:
        return "—"
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text.strip())
    # Удаляем специальные символы в начале и конце
    text = re.sub(r'^[\s\.,;:\-–—]+|[\s\.,;:\-–—]+$', '', text)
    # Обрезаем по длине и добавляем многоточие если нужно
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    return text.strip() if text.strip() else "—"


def extract_prize(text: str) -> str:
    """Ищет упоминание призового фонда в тексте. Возвращает строку с суммой/упоминанием или '—'."""
    if not text:
        return "—"
    # Шаблоны, ищущие числа и валюту
    patterns = [
        r'призовой\s+фонд[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'(?:фонд|награда)[:\s]*([\d\s]+(?:тыс|млн)?)\s*(?:руб|₽)',
        r'([\d\s]{3,}(?:тыс|млн)?)\s*(?:руб|₽)',
        r'prize[:\s]*([\d\s]+(?:k|m)?)\s*(?:rub|₽|rur)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount = m.group(1).strip()
            if amount:
                return clean_text(f"{amount} руб.", max_length=50)

    # Ищем сочетания числа + символа валюты ($, €, ₽ и т.п.)
    m = re.search(r'(\d[\d\s,\.]*\d)\s*(?:₽|руб|rur|rub|\$|usd|€|eur|£)', text)
    if m:
        return clean_text(f"{m.group(1)}", max_length=50)

    # Ищем символ валюты перед числом: $1000, € 2 000
    m = re.search(r'(?:₽|руб|rur|rub|\$|usd|€|eur|£)\s*(\d[\d\s,\.]*)', text)
    if m:
        return clean_text(f"{m.group(1)}", max_length=50)

    # Если явно написано "денежный приз" или "cash prize" — считаем наличием денежного приза
    if re.search(r'денежн.*приз|cash\s+prize|cash-prize', text, re.IGNORECASE):
        return clean_text("денежный приз", max_length=50)

    return "—"


def extract_organizer(text: str) -> str:
    """Пробует извлечь организатора из текста."""
    if not text:
        return "—"
    
    # Очищаем текст от лишнего
    text = re.sub(r'\s+', ' ', text.strip())
    
    patterns = [
        r'организатор[:\s]+([а-яа-яё\w\s\-\.]+?)(?:\n|$)',
        r'от[:\s]+([а-яё\w\s\-\.]{5,50})(?:\n|,|;|$)',
    ]
    
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            org = m.group(1).strip()
            # Проверяем, что текст разумной длины и не содержит числовых цепочек
            if 3 < len(org) < 100 and not re.search(r'\d{3,}', org):
                return clean_text(org, max_length=60)
    
    return "—"


def extract_location(text: str) -> str:
    """Пробует извлечь место проведения из текста."""
    if not text:
        return "—"
    
    patterns = [
        r'место[:\s]+([а-яё\w\s\-\.]+?)(?:\n|,|;|$)',
        r'адрес[:\s]+([а-яё\w\s\-\.]+?)(?:\n|,|;|$)',
        r'город[:\s]+([а-яё\w\s\-\.]+?)(?:\n|,|;|$)',
        r'(онлайн|очно|гибридно|дистанционно)',
    ]
    
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            loc = m.group(1).strip()
            if loc and len(loc) < 100:
                return clean_text(loc, max_length=60)
    
    return "—"


extract_registration_deadline

def extract_theme(title: str, text: str) -> str:
    """Определяет тематику конкурса на основе ключевых слов."""
    if not title and not text:
        return "—"
    
    full = (title + " " + text).lower()
    
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in full:
                return theme
    
    return "—"


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
    """Парсит сайт Хакатоны.рф через HTTP."""
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
    """Парсит раздел конкурсов на RSV.ru (Россия — страна возможностей)."""
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
        print(f"⚠️ Ошибка при парсинге RSV.ru: {e}")

    return events


def build_report(events: list) -> str:
    """Строит отчет в едином формате для всех событий с укороченными заголовками."""
    today_str = datetime.now().strftime('%d.%m.%Y')
    report = f"<b>🏆 ИТ-соревнования, олимпиады и конкурсы</b>\n"
    report += f"<i>Подборка на {today_str}</i>\n"
    report += f"<i>Только конкурсы с денежными призами</i>\n\n"

    if not events:
        report += "😔 <b>Активных конкурсов и олимпиад не найдено.</b>\n\n"
        report += "Попробуйте запустить позже или проверьте источники."
        return report

    for i, ev in enumerate(events[:15], 1):
        # Ограничиваем длину заголовка до 85 символов, чтобы не перегружать интерфейс
        title = escape_html(clean_text(ev['title'], max_length=85))
        
        organizer = escape_html(ev.get('organizer', '—'))
        prize = escape_html(ev.get('prize', '—'))
        registration_deadline = escape_html(ev.get('registration_deadline', '—'))
        theme = escape_html(ev.get('theme', '—'))
        link = ev.get('link', '')

        # Выводим красивый укороченный заголовок
        report += f"<b>{i}. {title}</b>\n"
        report += f"👤 {organizer}\n"
        report += f"💰 {prize}\n"
        report += f"📌 {registration_deadline}\n"
        report += f"🎯 {theme}\n"
        
        if link:
            report += f"<a href='{link}'>→ Ссылка на регистрацию</a>\n"
        
        report += "\n"

    report += f"<i>Всего найдено: {len(events)} соревнований.</i>"
    return report


def main():
    print(f"🚀 Запуск бота {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    all_events = []

    # 1. RSS-ленты (Habr Хакатоны + IT-events.com)
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

    # Фильтруем — оставляем только конкурсы с денежными призами
    filtered_events = [ev for ev in unique_events if ev.get('prize') and ev.get('prize') != '—']
    print(f"✅ После фильтрации по наличию денежного приза: {len(filtered_events)}")

    report = build_report(filtered_events)
    send_to_telegram(report)


if __name__ == "__main__":
    main()
