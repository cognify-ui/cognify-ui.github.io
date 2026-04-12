#!/usr/bin/env python3
import json
import os
import hashlib
import re
import time
from datetime import datetime
from google import genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден")
    print("Добавьте секрет в GitHub: Settings → Secrets and variables → Actions")
    exit(1)

print(f"✅ API ключ найден: {GEMINI_API_KEY[:15]}...")

client = genai.Client(api_key=GEMINI_API_KEY)

def get_available_models():
    """Получает список доступных моделей для generateContent"""
    available = []
    print("\n📋 Проверка доступных моделей...")
    try:
        for model in client.models.list():
            if 'generateContent' in str(model.supported_methods):
                model_name = model.name
                # Убираем префикс "models/"
                if model_name.startswith('models/'):
                    model_name = model_name[7:]
                available.append(model_name)
                print(f"   ✅ {model_name}")
    except Exception as e:
        print(f"   ⚠️ Ошибка получения списка моделей: {e}")
        # Если не удалось получить список, используем стандартный
        available = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-001",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash-lite-001",
        ]
        print(f"   📌 Используем стандартный список")
    
    return available

def generate_news_with_model(model_name, prompt):
    """Пытается сгенерировать новость с указанной моделью"""
    try:
        print(f"   🧠 Пробуем модель: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        text = response.text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            article = json.loads(json_match.group())
            print(f"   ✅ УСПЕШНО! Новость сгенерирована")
            return article
        else:
            print(f"   ⚠️ Не найден JSON в ответе")
            return None
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"   ❌ Модель не найдена")
        elif "429" in error_msg:
            print(f"   ⏳ Превышен лимит запросов")
        elif "403" in error_msg:
            print(f"   🔒 Нет доступа к модели")
        else:
            print(f"   ❌ Ошибка: {error_msg[:100]}")
        return None

def generate_news():
    """Перебирает все доступные модели с задержкой 10 секунд"""
    
    # Получаем список доступных моделей
    available_models = get_available_models()
    
    if not available_models:
        print("❌ Нет доступных моделей для генерации")
        return None
    
    print(f"\n📊 Всего доступно моделей: {len(available_models)}")
    print("=" * 60)
    
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
    
    for i, model_name in enumerate(available_models, 1):
        print(f"\n[{i}/{len(available_models)}] Тестируем модель...")
        
        article = generate_news_with_model(model_name, prompt)
        
        if article:
            print(f"\n🎉 Найдена рабочая модель: {model_name}")
            return article
        
        # Если это не последняя модель, ждём 10 секунд
        if i < len(available_models):
            print(f"   ⏳ Ждём 10 секунд перед следующей моделью...")
            time.sleep(10)
    
    print("\n❌ Все модели не сработали")
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
                print(f"\n📖 Загружено {len(existing.get('articles', []))} существующих новостей")
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
    
    print(f"\n✅ Сохранено. Всего новостей: {len(existing['articles'])}")
    return True

def create_demo_news():
    """Создаёт демо-новость, если ничего не работает"""
    demo_article = {
        "title": "Добро пожаловать в Cognify AI!",
        "summary": "Бесплатный доступ к 4 AI моделям: Groq, Cerebras, Cloudflare и Gemini",
        "content": "Cognify AI — это бесплатный сервис с 4 мощными AI моделями. Без лимитов, с историей чатов и системой аккаунтов. Просто откройте сайт и начните общение!",
        "source": "Cognify AI",
        "tags": ["cognify", "ai", "бесплатно"]
    }
    print("📝 Создаём демо-новость...")
    save_news_article(demo_article)

def main():
    print("=" * 60)
    print(f"🚀 ЗАПУСК ГЕНЕРАТОРА НОВОСТЕЙ GEMINI")
    print(f"🕐 Время: {datetime.now()}")
    print("=" * 60)
    
    # Пытаемся сгенерировать новость
    article = generate_news()
    
    if article:
        save_news_article(article)
        print("\n" + "=" * 60)
        print("📰 СГЕНЕРИРОВАННАЯ НОВОСТЬ:")
        print(f"   Заголовок: {article.get('title', 'Без заголовка')}")
        print(f"   Источник: {article.get('source', 'Неизвестен')}")
        print(f"   Теги: {', '.join(article.get('tags', []))}")
        print(f"   Кратко: {article.get('summary', '')[:100]}...")
    else:
        print("\n❌ Не удалось сгенерировать новость через API")
        
        # Создаём демо-новость, если файла нет
        if not os.path.exists(NEWS_FILE) or os.path.getsize(NEWS_FILE) < 100:
            create_demo_news()
    
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)

if __name__ == "__main__":
    main()
