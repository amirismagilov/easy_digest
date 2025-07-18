import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import os
import sys
import django

# --- Django setup: подключаем Django и настройки проекта ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from admin_panel.models import Channel, Post

def collect_html_posts(channel_username: str) -> list[dict]:
    """
    Парсит публичную HTML-страницу Telegram-канала t.me/s/<username>
    и собирает посты, опубликованные за последние 12 часов.
    
    Args:
        channel_username (str): username Telegram-канала (без @)

    Returns:
        list[dict]: список постов в формате {"text": ..., "date": datetime}
    """
    url = f"https://t.me/s/{channel_username}"
    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception(f"Не удалось загрузить канал {channel_username}: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Находим все блоки текста постов и даты
    raw_posts = soup.select(".tgme_widget_message_text")
    raw_dates = soup.select(".tgme_widget_message_date time")

    posts = []
    now = datetime.now(timezone.utc)
    time_threshold = now - timedelta(hours=12)

    for text_div, date_tag in zip(raw_posts, raw_dates):
        text = text_div.get_text(separator="\\n").strip()
        date_str = date_tag.get("datetime")

        try:
            # Преобразуем ISO-дату в datetime-объект
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            date = None

        # Отбираем только свежие посты (12 часов)
        if date and date >= time_threshold:
            posts.append({
                "text": text,
                "date": date
            })

    return posts

def save_posts_to_db(channel_username: str):
    """
    Сохраняет собранные посты в базу данных (модель Post).
    Привязывает к существующему или новому Channel.

    Args:
        channel_username (str): username Telegram-канала
    """
    posts = collect_html_posts(channel_username)

    # Получаем или создаем канал
    channel, _ = Channel.objects.get_or_create(
        username=channel_username,
        defaults={"title": channel_username}
    )

    saved_count = 0
    for post in posts:
        if post["text"] and post["date"]:
            # Проверка: такой пост уже сохранен?
            exists = Post.objects.filter(
                channel=channel,
                text=post["text"],
                date=post["date"]
            ).exists()
            if not exists:
                # Сохраняем в базу данных
                Post.objects.create(
                    channel=channel,
                    text=post["text"],
                    date=post["date"]
                )
                saved_count += 1

    print(f"✅ Сохранено {saved_count} постов за последние 12 часов из @{channel_username}")
    return saved_count

# --- Пример запуска для локального теста ---
if __name__ == "__main__":
    save_posts_to_db("bbbreaking")