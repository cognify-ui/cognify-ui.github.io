#!/usr/bin/env python3
import json
import os
import hashlib
import re
import time
import random
from datetime import datetime
from google import genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден")
    exit(1)

print(f"✅ API ключ найден: {GEMINI_API_KEY[:15]}...")

client = genai.Client(api_key=GEMINI_API_KEY)

# Модели для генерации
FIXED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]

# Темы новостей
TOPICS = [
    "искусственный интеллект", "нейросети", "chatgpt", "openai", "google gemini",
    "робототехника", "квантовые вычисления", "биотехнологии", "космос", "IT инновации"
]

def generate_news_article():
    """Генерирует одну новость"""
    
    topic = random.choice(TOPICS)
    
    prompt = f"""Ты - профессиональный журналист. Напиши уникальную новость на тему "{topic}".

Требования:
- Язык: русский
- Длина: 2000-4000 символов
- Дата: сегодняшняя
- Добавь цитаты экспертов и конкретные цифры
- Источник: любое известное техно-издание

Ответ дай ТОЛЬКО в формате JSON:
{{
    "title": "Заголовок новости (до 100 символов)",
    "summary": "Краткое описание (до 300 символов)",
    "content": "Полный текст новости (2000-4000 символов с абзацами)...",
    "source": "Название источника",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5"]
}}
"""
    
    for model in FIXED_MODELS:
        try:
            print(f"   🧠 Пробуем {model}...")
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            
            text = response.text
            # Очищаем от markdown
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # Ищем JSON
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            
            article = json.loads(text)
            
            # Проверяем поля
            required = ['title', 'summary', 'content', 'source', 'tags']
            if all(k in article for k in required):
                print(f"   ✅ Успех! Длина: {len(article['content'])} символов")
                article['seo_topic'] = topic
                article['used_model'] = model
                return article
                
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)[:50]}")
            continue
        
        time.sleep(2)
    
    return None

def load_existing_news():
    """Загружает существующие новости"""
    if not os.path.exists(NEWS_FILE):
        return {"articles": []}
    
    try:
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"articles": []}

def generate_sitemap(articles):
    """Генерирует sitemap.xml"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += '  <url>\n'
    sitemap += '    <loc>https://cognify-ui.github.io/</loc>\n'
    sitemap += f'    <lastmod>{today}</lastmod>\n'
    sitemap += '    <changefreq>daily</changefreq>\n'
    sitemap += '    <priority>1.0</priority>\n'
    sitemap += '  </url>\n'
    
    for article in articles[:20]:
        pub_date = article.get('published_at', today)[:10]
        sitemap += '  <url>\n'
        sitemap += f'    <loc>https://cognify-ui.github.io/news/{article["id"]}.html</loc>\n'
        sitemap += f'    <lastmod>{pub_date}</lastmod>\n'
        sitemap += '    <changefreq>weekly</changefreq>\n'
        sitemap += '    <priority>0.8</priority>\n'
        sitemap += '  </url>\n'
    
    sitemap += '</urlset>'
    
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap)
    
    print(f"   ✅ Sitemap создан: {len(articles[:20]) + 1} URL")

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
    print("   ✅ robots.txt создан")

def generate_news_html(article):
    """Генерирует HTML страницу для новости"""
    import html
    os.makedirs('news', exist_ok=True)
    
    title = html.escape(article.get('title', 'Новость'))
    summary = html.escape(article.get('summary', ''))
    content = html.escape(article.get('content', '')).replace('\n', '<br>')
    source = html.escape(article.get('source', 'Cognify AI'))
    article_id = article.get('id', '')
    image_url = article.get('image_url', '')
    published_at = article.get('published_at', '')
    tags = article.get('tags', [])
    
    if published_at:
        pub_date = published_at.split('T')[0]
    else:
        pub_date = datetime.now().strftime('%Y-%m-%d')
    
    tags_html = ''.join([f'<a href="/?tag={html.escape(tag)}" class="tag">#{html.escape(tag)}</a>' for tag in tags[:5]])
    
    image_html = ''
    if image_url:
        image_html = f'<img class="article-image" src="{html.escape(image_url)}" alt="{title}">'
    
    html_content = f'''<!DOCTYPE html>
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
    <link rel="canonical" href="https://cognify-ui.github.io/news/{article_id}.html">
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
        }}
        .article-content {{ padding: 40px; }}
        h1 {{ font-size: 32px; margin-bottom: 20px; }}
        .meta {{
            display: flex;
            gap: 20px;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .content {{ font-size: 18px; line-height: 1.8; margin-bottom: 30px; }}
        .tags {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 30px 0; }}
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
        }}
        @media (max-width: 768px) {{
            .article-content {{ padding: 20px; }}
            h1 {{ font-size: 24px; }}
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
            <div class="content">{content}</div>
            <div class="tags">{tags_html}</div>
            <a href="/" class="back-link">← Назад к новостям</a>
        </div>
    </div>
</body>
</html>'''
    
    html_path = f"news/{article_id}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ Создана страница: {html_path}")
    return html_path

def save_news_article(article):
    """Сохраняет новость"""
    data = load_existing_news()
    
    article_id = hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:12]
    image_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={article_id}&backgroundColor=6366f1&radius=50"
    
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
        "seo_metadata": {
            "meta_title": f"{article.get('title')} | Cognify AI News",
            "meta_description": article.get('summary', '')[:160],
            "meta_keywords": ", ".join(article.get('tags', [])),
        }
    }
    
    # Проверяем дубликаты
    existing_titles = [a.get('title') for a in data.get('articles', [])]
    if new_article['title'] in existing_titles:
        print(f"   ⚠️ Дубликат, пропускаем")
        return False
    
    # Добавляем в начало
    if 'articles' not in data:
        data['articles'] = []
    
    data['articles'].insert(0, new_article)
    data['articles'] = data['articles'][:MAX_ARTICLES]
    data['last_updated'] = datetime.now().isoformat()
    data['total_articles'] = len(data['articles'])
    
    # Сохраняем JSON
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Генерируем HTML
    generate_news_html(new_article)
    
    # Обновляем sitemap и robots.txt
    generate_sitemap(data['articles'])
    generate_robots_txt()
    
    print(f"\n✅ Сохранено! Всего: {len(data['articles'])}")
    print(f"📰 {new_article['title'][:80]}...")
    
    return True

def main():
    print("=" * 60)
    print(f"🚀 ЗАПУСК ГЕНЕРАТОРА НОВОСТЕЙ")
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Генерируем новость
    print("\n📝 Генерируем новость...")
    article = generate_news_article()
    
    if article:
        success = save_news_article(article)
        if not success:
            print("\n⚠️ Дубликат, пробуем ещё раз...")
            article = generate_news_article()
            if article:
                save_news_article(article)
    else:
        print("\n❌ Не удалось сгенерировать новость")
        
        # Если файл пустой, создаем демо
        data = load_existing_news()
        if len(data.get('articles', [])) == 0:
            print("\n📝 Создаём демо-новость...")
            demo = {
                "title": "Cognify AI: Бесплатный доступ к 4 AI моделям",
                "summary": "Откройте мир искусственного интеллекта бесплатно! Cognify AI предоставляет доступ к Groq, Cerebras, Cloudflare AI и Google Gemini.",
                "content": "Cognify AI — инновационная платформа, объединяющая 4 передовые AI модели. Пользователи могут общаться с Groq, Cerebras, Cloudflare AI и Google Gemini абсолютно бесплатно.",
                "source": "Cognify AI",
                "tags": ["cognify", "бесплатный ai", "groq", "cerebras", "gemini"],
                "seo_topic": "free ai",
                "used_model": "demo"
            }
            save_news_article(demo)
    
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)

if __name__ == "__main__":
    main()
