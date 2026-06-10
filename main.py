import requests
import re
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8925355466:AAFwGby1v-t-JGbCbUnjbt_2aM9JTsnHU_U' 
CHAT_ID = '908014386' 

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

def extract_prize_from_description(description):
    """Извлекает призовой фонд из описания"""
    if not description:
        return "Не указан"
    
    # Ищем паттерны типа "500 000 рублей", "1000000 руб", "призовой фонд 300к"
    patterns = [
        r'призовой\s+фонд[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'приз[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?',
        r'([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)',
        r'выигрыш[:\s]*([\d\s]+(?:тыс|млн|k|m)?)\s*(?:руб|₽|rur)?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            prize = match.group(1).strip()
            return f"💰 {prize} руб"
    
    return "Не указан"

def extract_theme_from_description(description, title):
    """Определяет тематику из описания или названия"""
    themes = {
        'AI': ['искусственн', 'нейросет', 'machine learning', 'ai ', 'chatgpt', 'llm'],
        'Data Science': ['data science', 'анализ данных', 'big data', 'дата сайенс'],
        'Web': ['web', 'веб', 'frontend', 'backend', 'react', 'vue', 'angular'],
        'Mobile': ['mobile', 'мобильн', 'ios', 'android', 'flutter'],
        'Blockchain': ['blockchain', 'блокчейн', 'crypto', 'крипто', 'web3'],
        'GameDev': ['gamedev', 'игров', 'game', 'unity', 'unreal'],
        'Cybersecurity': ['кибербезопас', 'cybersecurity', '信息安全', 'hacking', 'ctf'],
        'IoT': ['iot', 'интернет вещей', 'embedded', 'arduino', 'raspberry'],
        'FinTech': ['fintech', 'финтех', 'банков', 'платеж'],
        'EdTech': ['edtech', 'образование', 'обучен', 'edu']
    }
    
    text = (title + " " + (description or "")).lower()
    
    for theme, keywords in themes.items():
        if any(keyword in text for keyword in keywords):
            return theme
    
    return "IT (общая)"

def main():
    # Timepad API для IT-событий в Москве
    url = "https://api.timepad.ru/api/2/events.json"
    params = {
        'city_id': 1,  # Москва
        'category_ids': 21,  # IT категория
        'limit': 30,
        'status': 'active'
    }
    
    try:
        response = requests.get(url, params=params)
        events = response.json().get('values', [])
        
        report = "🗓 *ИТ-мероприятия в Москве*\n"
        report += f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
        
        count = 0
        today = datetime.now()
        next_week = today + timedelta(days=14)  # Ближайшие 2 недели
        
        for event in events:
            event_date = datetime.strptime(event['start_at'][:10], '%Y-%m-%d')
            
            if today <= event_date <= next_week:
                # Извлекаем данные
                title = event['name']
                link = f"https://timepad.ru/event/{event['id']}/"
                start_date = event_date.strftime('%d.%m.%Y')
                
                # Дата окончания (если есть)
                end_date_str = event.get('end_at', '')
                if end_date_str:
                    end_date = datetime.strptime(end_date_str[:10], '%Y-%m-%d')
                    if end_date != event_date:
                        date_range = f"{start_date} — {end_date.strftime('%d.%m.%Y')}"
                    else:
                        date_range = start_date
                else:
                    date_range = start_date
                
                # Организатор
                org = event.get('organization', {}).get('name', 'Не указан')
                
                # Описание
                description = event.get('description', '')
                
                # Призовой фонд и тематика
                prize = extract_prize_from_description(description)
                theme = extract_theme_from_description(description, title)
                
                # Формируем блок события
                report += f" *{title}*\n"
                report += f"📅 *Срок проведения:* {date_range}\n"
                report += f"🏢 *Организатор:* {org}\n"
                report += f"💰 *Призовой фонд:* {prize}\n"
                report += f"🎯 *Тематика:* {theme}\n"
                report += f"🔗 [Регистрация]({link})\n\n"
                report += "━" * 15 + "\n\n"
                
                count += 1
                
                if count >= 10:
                    break
        
        if count > 0:
            report += f"_✅ Найдено событий: {count}_"
            send_to_telegram(report)
        else:
            send_to_telegram("🔍 На ближайшие 2 недели событий не найдено")
            
    except Exception as e:
        send_to_telegram(f"❌ Ошибка при получении данных: {e}")

if __name__ == "__main__":
    main()
