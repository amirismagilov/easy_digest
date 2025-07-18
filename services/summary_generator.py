import httpx
import os

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # пример, уточни в документации
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # желательно хранить в переменных окружения

HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def generate_digest(posts: list[str]) -> str:
    """
    Отправляет список постов в DeepSeek и получает дайджест.
    """
    content = "\n\n".join(posts)
    prompt = f"Составь краткий информативный дайджест по следующим новостным постам:\n\n{content}"

    payload = {
        "model": "deepseek-chat",  # Уточни имя модели по документации
        "messages": [
            {"role": "system", "content": "Ты журналист, пишущий утренние дайджесты новостей."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = httpx.post(DEEPSEEK_API_URL, headers=HEADERS, json=payload, timeout=60)
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]