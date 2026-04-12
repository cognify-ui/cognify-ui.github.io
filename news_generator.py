#!/usr/bin/env python3
import json
import os
import hashlib
import re
from datetime import datetime
import google.generativeai as genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден")
    exit(1)

print(f"✅ API ключ найден: {GEMINI_API_KEY[:10]}...")

# Используем доступную модель
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')  # ✅ Изменено!

def generate_news():
    """Генерирует одну новость с помощью Gemini"""
    prompt = """
Ты — журналист AI новостей. Сгенерируй ОДНУ свежую новость из мира искусственного интеллекта.

Требования:
1. Новость должна звучать как реальная
2. Дата: сегодня или вчера
3. Источник: The Verge, TechCrunch, Wired или VentureBeat
4. Язык: русский

Ответ должен быть строго в формате JSON. НИКАКОГО дополнительного текста, только JSON:
{
    "title": "Заголовок новости (до 80 символов)",
    "summary": "Краткое описание (2-3 предложения, до 300 символов)",
    "content": "Полный текст новости (3-5 предложений, до 1000 символов)",
    "source": "Название источника",
    "tags": ["тег1", "тег2", "тег3"]
}
"""
    try:
        print("🧠 Запрос к Gemini...")
        response = model.generate_content(prompt)
        
        # Ищем JSON в ответе
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            article = json.loads(json_match.group())
            print(f"✅ Получена новость: {article.get('title', 'Без заголовка')[:50]}...")
            return article
        else:
            print(f"⚠️ Не найден JSON. Ответ: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
        return None

def generate_image_url(title):
    """Генерирует URL картинки через Unsplash"""
    query = title.replace(' ', '+')[:50]
    return f"https://source.unsplash.com/800x400/?{query},ai,technology"

def save_news_article(article):
    """Сохраняет новость в news.json"""
    existing = {"last_updated": "", "articles": []}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                print(f"📖 Загружено {len(existing.get('articles', []))} существующих новостей")
        except Exception as e:
            print(f"⚠️ Ошибка чтения: {e}")
    
    # Создаём ID
    article_id = hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:12]
    
    new_article = {
        "id": article_id,
        "title": article.get('title', 'AI Новость'),
        "summary": article.get('summary', ''),
        "content": article.get('content', ''),
        "source": article.get('source', 'AI News'),
        "source_url": f"https://cognify-ui.github.io/news/{article_id}",
        "published_at": datetime.now().isoformat(),
        "tags": article.get('tags', ['ai', 'news']),
        "image_url": generate_image_url(article.get('title', 'ai'))
    }
    
    # Добавляем в начало
    existing['articles'].insert(0, new_article)
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Сохранено. Всего новостей: {len(existing['articles'])}")
    return True

def main():
    print(f"🚀 Запуск генератора новостей Gemini: {datetime.now()}")
    print("-" * 50)
    
    # Генерируем новость
    article = generate_news()
    
    if article:
        save_news_article(article)
        print(f"📰 Заголовок: {article.get('title', 'Без заголовка')}")
        print(f"📝 Кратко: {article.get('summary', '')[:100]}...")
    else:
        print("❌ Не удалось сгенерировать новость")
        
        # Создаём демо-новость, если файла нет
        if not os.path.exists(NEWS_FILE) or os.path.getsize(NEWS_FILE) < 100:
            print("📝 Создаём демо-новость...")
            demo_article = {
                "title": "Добро пожаловать в Cognify AI!",
                "summary": "Бесплатный доступ к 4 AI моделям: Groq, Cerebras, Cloudflare и Gemini",
                "content": "Cognify AI — это бесплатный сервис с 4 мощными AI моделями. Без лимитов, с историей чатов и системой аккаунтов. Просто откройте сайт и начните общение!",
                "source": "Cognify AI",
                "tags": ["cognify", "ai", "бесплатно"]
            }
            save_news_article(demo_article)
    
    print("✅ Готово!")

if __name__ == "__main__":
    main()
