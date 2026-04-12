#!/usr/bin/env python3
import json
import os
import hashlib
import re
import time
import random
from datetime import datetime, timedelta
from google import genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50
MAX_RETRIES = 3

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден")
    print("Добавьте секрет в GitHub: Settings → Secrets and variables → Actions")
    exit(1)

print(f"✅ API ключ найден: {GEMINI_API_KEY[:15]}...")

client = genai.Client(api_key=GEMINI_API_KEY)

# Фиксированный список моделей для генерации
FIXED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
]

# ========== РАСШИРЕННЫЕ ТЕМЫ ДЛЯ НОВОСТЕЙ ==========
SEO_TOPICS = [
    # AI
    "chatgpt", "openai", "google gemini", "microsoft copilot", "claude ai",
    "midjourney", "stable diffusion", "dall-e 3", "ai art", "neural networks",
    "deep learning", "machine learning", "nvidia h100", "ai startup", "ai funding",
    "ai safety", "generative ai", "llm", "ai agents", "agi", "ai chip", "gpu",
    "quantum ai", "edge ai", "ai healthcare", "ai medicine", "ai finance",
    "ai education", "humanoid robot", "self-driving car", "computer vision",
    "ai video generation", "sora ai", "ai coding", "github copilot", "ai cybersecurity",
    "deepseek", "llama 3", "mistral ai", "perplexity ai",
    # Технологии
    "iphone", "samsung galaxy", "google pixel", "playstation", "xbox",
    "nintendo switch", "windows", "macos", "android", "ios", "telegram update",
    "whatsapp new features", "instagram updates", "tiktok news", "youtube new features",
    "spotify", "netflix", "cybersecurity", "5g", "6g", "wifi 7", "foldable phone",
    "smartwatch", "smart home", "iot", "electric car", "tesla", "spacex", "nasa",
    # Наука
    "physics discovery", "quantum computing", "biology breakthrough", "medical research",
    "cancer treatment", "gene editing", "crispr", "james webb", "mars mission",
    "climate change", "renewable energy", "fusion energy", "battery technology",
    # Бизнес
    "stock market", "cryptocurrency", "bitcoin", "ethereum", "blockchain",
    "inflation", "interest rates", "global economy", "startup funding", "ipo",
    "elon musk", "jeff bezos", "mark zuckerberg",
    # Здоровье
    "health news", "fitness trends", "mental health", "covid update", "longevity",
    # Спорт
    "football news", "premier league", "champions league", "nba finals",
    "tennis grand slam", "formula 1", "olympics",
    # Развлечения
    "hollywood news", "netflix series", "marvel movie", "star wars", "stranger things",
    "kpop news", "taylor swift", "beyonce",
]

# Конфигурация изображений по темам
IMAGE_THEMES = {
    'chatgpt': {'style': 'bottts', 'color': '10a37f'},
    'openai': {'style': 'bottts', 'color': '10a37f'},
    'google': {'style': 'identicon', 'color': '4285f4'},
    'gemini': {'style': 'identicon', 'color': '8e6ced'},
    'microsoft': {'style': 'micah', 'color': '00a4ef'},
    'claude': {'style': 'adventurer', 'color': 'd97757'},
    'meta': {'style': 'lorelei', 'color': '0064e1'},
    'midjourney': {'style': 'pixel-art', 'color': 'ff6b35'},
    'nvidia': {'style': 'bottts', 'color': '76b900'},
    'robot': {'style': 'bottts', 'color': '6b7280'},
    'autonomous': {'style': 'bottts', 'color': 'ef4444'},
    'iphone': {'style': 'bottts', 'color': '34c759'},
    'samsung': {'style': 'bottts', 'color': '1428a0'},
    'playstation': {'style': 'bottts', 'color': '003791'},
    'xbox': {'style': 'bottts', 'color': '107c10'},
    'tesla': {'style': 'bottts', 'color': 'e82127'},
    'spacex': {'style': 'bottts', 'color': '005288'},
    'bitcoin': {'style': 'identicon', 'color': 'f7931a'},
    'health': {'style': 'adventurer', 'color': '2ecc71'},
    'sport': {'style': 'micah', 'color': 'e67e22'},
    'movie': {'style': 'pixel-art', 'color': '9b59b6'},
    'default': {'style': 'bottts', 'color': '6366f1'}
}

def get_available_models():
    """Возвращает фиксированный список моделей для генерации"""
    print("\n📋 Загружаем список моделей для генерации...")
    
    available_models = []
    api_models = []
    
    try:
        for model in client.models.list():
            if 'generateContent' in str(model.supported_methods):
                model_name = model.name.replace('models/', '')
                api_models.append(model_name)
        
        print(f"   📡 Найдено моделей в API: {len(api_models)}")
        
        for model in FIXED_MODELS:
            if model in api_models:
                available_models.append(model)
                print(f"   ✅ {model} - доступна")
            else:
                print(f"   ⚠️ {model} - не найдена в API, пропускаем")
        
        if not available_models and api_models:
            available_models = api_models[:3]
            print(f"   📌 Используем первые 3 доступные модели: {available_models}")
            
    except Exception as e:
        print(f"   ⚠️ Ошибка проверки API: {e}")
        available_models = FIXED_MODELS.copy()
        print(f"   📌 Используем фиксированный список из {len(available_models)} моделей")
    
    print(f"\n📊 Итоговый список для генерации ({len(available_models)} моделей):")
    for i, model in enumerate(available_models, 1):
        print(f"   {i}. {model}")
    
    return available_models

def get_seo_prompt(topic=None):
    """Генерирует SEO-оптимизированный промпт для новости"""
    if not topic:
        topic = random.choice(SEO_TOPICS)
    
    target_length = random.randint(1500, 10000)
    
    sources = [
        "The Verge", "TechCrunch", "Wired", "VentureBeat", "Ars Technica",
        "MIT Technology Review", "IEEE Spectrum", "Reuters", "BBC News",
        "CNN", "The Guardian", "Forbes", "Bloomberg"
    ]
    
    seo_keywords = [
        "искусственный интеллект", "AI", "нейросети", "машинное обучение",
        "технологии будущего", "инновации", "цифровая трансформация"
    ]
    
    prompt = f"""
Ты — профессиональный журналист. Сгенерируй УНИКАЛЬНУЮ, ДЕТАЛЬНУЮ новость на тему: {topic}

ТРЕБОВАНИЯ:
1. Дата: сегодня или вчера
2. Источник: {random.choice(sources)}
3. Язык: русский
4. ДЛИНА ТЕКСТА: {target_length} символов
5. Добавь цитаты экспертов, цифры, статистику

СТРУКТУРА:
- Заголовок (до 100 символов)
- Краткое описание (до 350 символов)
- Полный текст (1500-10000 символов) с подзаголовками
- Теги: 5-7 штук

ФОРМАТ - ТОЛЬКО JSON:
{{
    "title": "Заголовок",
    "summary": "Краткое описание",
    "content": "Полный текст новости...",
    "source": "Источник",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5"]
}}
"""
    return prompt, topic

def generate_news_with_model(model_name, prompt, retry_count=0):
    """Генерирует новость с указанной моделью"""
    try:
        print(f"   🧠 Пробуем модель: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        text = response.text
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
        
        article = json.loads(text)
        
        required_fields = ['title', 'summary', 'content', 'source', 'tags']
        if all(field in article for field in required_fields):
            content_length = len(article.get('content', ''))
            print(f"   ✅ УСПЕШНО! Длина текста: {content_length} символов")
            return article
        else:
            print(f"   ⚠️ Не все поля заполнены")
            return None
            
    except json.JSONDecodeError as e:
        print(f"   ❌ Ошибка парсинга JSON: {e}")
        if retry_count < MAX_RETRIES:
            print(f"   🔄 Повторная попытка ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(5)
            return generate_news_with_model(model_name, prompt, retry_count + 1)
        return None
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            print(f"   ⏳ Превышен лимит, ждём 30 сек...")
            time.sleep(30)
            if retry_count < MAX_RETRIES:
                return generate_news_with_model(model_name, prompt, retry_count + 1)
        elif "404" in error_msg:
            print(f"   ❌ Модель {model_name} не найдена")
        else:
            print(f"   ❌ Ошибка: {error_msg[:100]}")
        return None

def generate_news():
    """Генерирует новость, перебирая все модели"""
    available_models = get_available_models()
    
    if not available_models:
        print("❌ Нет доступных моделей")
        return None
    
    print(f"\n🔄 Начинаем перебор {len(available_models)} моделей...")
    print("=" * 60)
    
    for attempt in range(3):
        print(f"\n🎯 Попытка {attempt + 1}/3 - выбор темы...")
        
        topic = random.choice(SEO_TOPICS)
        prompt, selected_topic = get_seo_prompt(topic)
        print(f"📌 Тема: {selected_topic.upper()}")
        
        for i, model_name in enumerate(available_models, 1):
            print(f"\n[{i}/{len(available_models)}] Тестируем модель {model_name}...")
            
            article = generate_news_with_model(model_name, prompt)
            
            if article:
                article['seo_topic'] = selected_topic
                article['used_model'] = model_name
                article['generation_time'] = datetime.now().isoformat()
                print(f"\n🎉 Успех! Модель: {model_name}, Тема: {selected_topic}")
                return article
            
            if i < len(available_models):
                time.sleep(random.randint(3, 7))
        
        if attempt < 2:
            print(f"\n⏰ Пауза 20 сек...")
            time.sleep(20)
    
    print("\n❌ Не удалось сгенерировать новость")
    return None

def generate_image_url(title, tags):
    """Генерирует изображение под тему новости"""
    import hashlib
    
    title_lower = title.lower()
    tags_lower = [t.lower() for t in tags]
    
    theme = 'default'
    for key, config in IMAGE_THEMES.items():
        if key in title_lower or any(key in tag for tag in tags_lower):
            theme = key
            break
    
    config = IMAGE_THEMES[theme]
    seed = hashlib.md5(f"{title}{datetime.now().strftime('%Y%m%d')}".encode()).hexdigest()[:10]
    
    return f"https://api.dicebear.com/7.x/{config['style']}/svg?seed={seed}&backgroundColor={config['color']}&radius=50"

def generate_seo_metadata(article):
    """Генерирует SEO-метаданные"""
    return {
        "meta_title": f"{article['title']} | Cognify AI News",
        "meta_description": article['summary'][:160],
        "meta_keywords": ", ".join(article.get('tags', []) + [article.get('seo_topic', 'news')]),
        "og_title": article['title'],
        "og_description": article['summary'][:200],
        "twitter_card": "summary_large_image"
    }

def generate_news_html(article):
    """Генерирует отдельную HTML-страницу для новости (ИСПРАВЛЕНО)"""
    os.makedirs('news', exist_ok=True)
    
    content_html = article.get('content', '').replace('\n', '<br>')
    article_id = article.get('id', '')
    title = article.get('title', 'Новость')
    summary = article.get('summary', '')
    image_url = article.get('image_url', '')
    source = article.get('source', 'Cognify AI')
    published_at = article.get('published_at', '')
    tags = article.get('tags', [])
    
    if published_at:
        pub_date = published_at.split('T')[0]
    else:
        pub_date = 'Дата неизвестна'
    
    tags_html = ''.join([f'<a href="/?tag={tag}" class="tag">#{tag}</a>' for tag in tags[:5]])
    
    image_html = ''
    if image_url:
        image_html = f'<img class="article-image" src="{image_url}" alt="{title}">'
    
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Cognify AI News</title>
    <meta name="description" content="{summary[:160]}">
    <meta name="keywords" content="{', '.join(tags)}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{summary[:200]}">
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="https://cognify-ui.github.io/news/{article_id}.html">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="https://cognify-ui.github.io/news/{article_id}.html">
    <link rel="icon" type="image/png" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        .article-image {{
            width: 100%;
            height: 400px;
            object-fit: cover;
            background: #f0f0f0;
        }}
        .article-content {{ padding: 40px; }}
        h1 {{ font-size: 32px; color: #1a1a2e; margin-bottom: 20px; line-height: 1.3; }}
        .meta {{
            display: flex;
            gap: 20px;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
            flex-wrap: wrap;
        }}
        .content {{ font-size: 18px; line-height: 1.8; color: #333; margin-bottom: 30px; }}
        .tags {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 30px 0;
        }}
        .tag {{
            background: #f0f0f0;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            color: #667eea;
            text-decoration: none;
        }}
        .back-link {{
            display: inline-block;
            margin-top: 30px;
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .article-content {{ padding: 20px; }}
            h1 {{ font-size: 24px; }}
            .article-image {{ height: 250px; }}
            .content {{ font-size: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {image_html}
        <div class="article-content">
            <h1>{title}</h1>
            <div class="meta">
                <span>📅 {pub_date}</span>
                <span>🔗 {source}</span>
                <span>📖 {len(article.get('content', ''))} символов</span>
            </div>
            <div class="content">
                {content_html}
            </div>
            <div class="tags">
                {tags_html}
            </div>
            <a href="/" class="back-link">← Назад к новостям</a>
        </div>
    </div>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "{title.replace('"', '\\"')}",
        "description": "{summary[:200].replace('"', '\\"')}",
        "datePublished": "{published_at}",
        "author": {{ "@type": "Organization", "name": "Cognify AI" }},
        "publisher": {{ "@type": "Organization", "name": "Cognify AI" }}
    }}
    </script>
</body>
</html>
    
    html_path = f"news/{article_id}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ Создана страница: {html_path}")
    return html_path

def generate_sitemap():
    """Генерирует sitemap.xml"""
    existing = {"articles": []}
    
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    articles = existing.get('articles', [])
    today = datetime.now().strftime("%Y-%m-%d")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += f'''  <url>
    <loc>https://cognify-ui.github.io/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
'''
    
    for article in articles:
        pub_date = article.get('published_at', today)[:10]
        sitemap += f'''  <url>
    <loc>https://cognify-ui.github.io/news/{article['id']}.html</loc>
    <lastmod>{pub_date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
'''
    
    sitemap += '</urlset>'
    
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap)
    
    print(f"✅ Sitemap создан: {len(articles) + 1} URL")

def generate_robots_txt():
    """Создает robots.txt"""
    robots = '''User-agent: *
Allow: /
Sitemap: https://cognify-ui.github.io/sitemap.xml
Disallow: /news.json
Disallow: /news_generator.py
'''
    with open('robots.txt', 'w', encoding='utf-8') as f:
        f.write(robots)
    print("✅ robots.txt создан")

def generate_all_news_pages():
    """Генерирует HTML для всех новостей"""
    if not os.path.exists(NEWS_FILE):
        print("❌ news.json не найден")
        return
    
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    print(f"\n📄 Генерация HTML для {len(articles)} новостей...")
    
    for article in articles:
        generate_news_html(article)
    
    generate_sitemap()
    generate_robots_txt()
    print(f"✅ Создано {len(articles)} HTML страниц")

def save_news_article(article):
    """Сохраняет новость и генерирует HTML"""
    existing = {"last_updated": "", "articles": []}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                print(f"\n📖 Загружено {len(existing.get('articles', []))} новостей")
        except Exception as e:
            print(f"⚠️ Ошибка чтения: {e}")
    
    article_id = hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:12]
    image_url = generate_image_url(article['title'], article.get('tags', []))
    
    new_article = {
        "id": article_id,
        "title": article.get('title'),
        "summary": article.get('summary'),
        "content": article.get('content'),
        "source": article.get('source'),
        "source_url": f"https://cognify-ui.github.io/news/{article_id}.html",
        "published_at": datetime.now().isoformat(),
        "tags": article.get('tags', ['news']),
        "seo_topic": article.get('seo_topic', 'news'),
        "used_model": article.get('used_model', 'unknown'),
        "image_url": image_url,
        "seo_metadata": generate_seo_metadata(article)
    }
    
    existing_titles = [a.get('title') for a in existing.get('articles', [])]
    if new_article['title'] in existing_titles:
        print("⚠️ Такая новость уже существует, пропускаем...")
        return False
    
    existing['articles'].insert(0, new_article)
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    existing['total_articles'] = len(existing['articles'])
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    generate_news_html(new_article)
    generate_sitemap()
    generate_robots_txt()
    
    print(f"\n✅ Сохранено. Всего новостей: {len(existing['articles'])}")
    print(f"📏 Длина текста: {len(article.get('content', ''))} символов")
    return True

def create_seo_demo_news():
    """Создаёт демо-новость"""
    demo_article = {
        "title": "Cognify AI: Бесплатный доступ к 4 мощным AI моделям",
        "summary": "Откройте мир искусственного интеллекта бесплатно! Cognify AI предоставляет доступ к Groq, Cerebras, Cloudflare AI и Google Gemini без ограничений.",
        "content": "Cognify AI — это инновационная платформа, объединяющая 4 передовые AI модели. Пользователи могут общаться с Groq, Cerebras, Cloudflare AI и Google Gemini абсолютно бесплатно. Сервис предлагает историю чатов, систему аккаунтов и интуитивный интерфейс.",
        "source": "Cognify AI",
        "tags": ["cognify", "бесплатный ai", "groq", "cerebras", "gemini"],
        "seo_topic": "free ai",
        "used_model": "demo"
    }
    print("📝 Создаём демо-новость...")
    return save_news_article(demo_article)

def main():
    print("=" * 60)
    print(f"🚀 ЗАПУСК ГЕНЕРАТОРА НОВОСТЕЙ")
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Моделей: {len(FIXED_MODELS)}")
    print(f"🎨 Всего тем: {len(SEO_TOPICS)}")
    print("=" * 60)
    
    article = generate_news()
    
    if article:
        success = save_news_article(article)
        if success:
            print("\n" + "=" * 60)
            print("📰 СГЕНЕРИРОВАННАЯ НОВОСТЬ:")
            print(f"   📌 Заголовок: {article.get('title')}")
            print(f"   📰 Источник: {article.get('source')}")
            print(f"   🏷️  Тема: {article.get('seo_topic')}")
            print(f"   🤖 Модель: {article.get('used_model')}")
            print(f"   📏 Длина: {len(article.get('content', ''))} символов")
            print("=" * 60)
        else:
            print("⚠️ Новость не сохранена (дубликат)")
    else:
        print("\n❌ Не удалось сгенерировать новость")
        
        if not os.path.exists(NEWS_FILE) or os.path.getsize(NEWS_FILE) < 100:
            create_seo_demo_news()
        else:
            generate_all_news_pages()
            print("📁 Обновлены HTML страницы")
    
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)

if __name__ == "__main__":
    main()
