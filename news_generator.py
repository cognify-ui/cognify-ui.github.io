#!/usr/bin/env python3
import json
import os
import hashlib
import requests
from datetime import datetime
from google import generativeai as genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

# Берём ключ из переменной окружения (GitHub Secrets)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден в переменных окружения")
    print("Добавьте секрет в GitHub: Settings → Secrets and variables → Actions")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def generate_news():
    """Генерирует одну новость с помощью Gemini"""
    prompt = """
Ты — журналист AI новостей. Сгенерируй ОДНУ свежую, правдоподобную новость из мира искусственного интеллекта.

Требования:
1. Новость должна звучать как реальная (можно выдуманную, но правдоподобную)
2. Дата: сегодня или вчера
3. Источник: реальное СМИ (The Verge, TechCrunch, Wired, VentureBeat, MIT Tech Review)
4. Язык: русский

Ответ должен быть строго в формате JSON:
{
    "title": "Заголовок новости (до 80 символов)",
    "summary": "Краткое описание (2-3 предложения, до 300 символов)",
    "content": "Полный текст новости (3-5 предложений, до 1000 символов)",
    "source": "Название источника",
    "tags": ["тег1", "тег2", "тег3"]
}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # Извлекаем JSON из ответа
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = text[start:end]
            article = json.loads(json_str)
            return article
        else:
            print("⚠️ Не удалось извлечь JSON из ответа")
            print(f"Ответ: {text[:200]}...")
            return None
    except Exception as e:
        print(f"❌ Ошибка генерации новости: {e}")
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
        except:
            pass
    
    article_id = hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:12]
    
    new_article = {
        "id": article_id,
        "title": article['title'],
        "summary": article['summary'],
        "content": article['content'],
        "source": article.get('source', 'AI News'),
        "source_url": f"https://cognify-ui.github.io/news/{article_id}",
        "published_at": datetime.now().isoformat(),
        "tags": article.get('tags', ['ai', 'news']),
        "image_url": generate_image_url(article['title'])
    }
    
    existing['articles'].insert(0, new_article)
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Добавлена новость: {article['title']}")
    return True

def main():
    print(f"🚀 Запуск генератора новостей Gemini: {datetime.now()}")
    print(f"🔑 API ключ: {'✅ найден' if GEMINI_API_KEY else '❌ не найден'}")
    print("-" * 50)
    
    print("🧠 Генерация новости через Gemini...")
    article = generate_news()
    
    if article:
        save_news_article(article)
        print(f"📰 Заголовок: {article['title']}")
        print(f"📝 Кратко: {article['summary'][:100]}...")
    else:
        print("❌ Не удалось сгенерировать новость")
        
        if not os.path.exists(NEWS_FILE):
            demo_article = {
                "title": "Добро пожаловать в Cognify AI!",
                "summary": "Бесплатный доступ к 4 AI моделям: Groq, Cerebras, Cloudflare и Gemini",
                "content": "Cognify AI — это бесплатный сервис с 4 мощными AI моделями. Без лимитов, с историей чатов и системой аккаунтов.",
                "source": "Cognify AI",
                "tags": ["cognify", "ai", "бесплатно"]
            }
            save_news_article(demo_article)
    
    print("✅ Готово!")

if __name__ == "__main__":
    main()
