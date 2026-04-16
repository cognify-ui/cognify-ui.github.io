#!/usr/bin/env python3
"""
Реальный агрегатор новостей из RSS-лент
Работает с feedparser + requests
"""

import json
import os
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any

import feedparser
import requests
from bs4 import BeautifulSoup

NEWS_FILE = "news.json"
MAX_ARTICLES = 500

# Реальные RSS-источники
RSS_FEEDS = {
    "Habr (IT новости)": "https://habr.com/ru/rss/hub/it_news/",
    "Habr (все)": "https://habr.com/ru/rss/hub/all/",
    "РИА Новости": "https://ria.ru/export/rss2/index.xml",
    "РИА Наука": "https://ria.ru/export/rss2/science/index.xml",
    "РИА Технологии": "https://ria.ru/export/rss2/technology/index.xml",
    "Lenta.ru": "https://lenta.ru/rss",
    "TechCrunch": "https://feeds.feedburner.com/TechCrunch",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Wired": "https://www.wired.com/feed/rss",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
}

def get_tags(title: str, summary: str) -> List[str]:
    """Автоматическое тегирование по ключевым словам"""
    text = (title + " " + summary).lower()
    tags = []
    
    if any(w in text for w in ['ai', 'ии', 'нейросеть', 'gpt', 'chatgpt', 'gemini', 'llm']):
        tags.append('AI')
    if any(w in text for w in ['космос', 'spacex', 'nasa', 'марс', 'луна', 'мкс']):
        tags.append('космос')
    if any(w in text for w in ['технологии', 'гаджет', 'apple', 'google', 'iphone', 'android']):
        tags.append('технологии')
    if any(w in text for w in ['наука', 'ученые', 'исследование', 'открытие', 'лаборатория']):
        tags.append('наука')
    if any(w in text for w in ['медицина', 'здоровье', 'болезнь', 'лекарство', 'вакцина']):
        tags.append('медицина')
    if any(w in text for w in ['хакер', 'утечка', 'безопасность', 'вирус', 'взлом']):
        tags.append('безопасность')
    
    return tags if tags else ['новости']

def fetch_articles() -> List[Dict[str, Any]]:
    """Собирает статьи из всех RSS-лент"""
    all_articles = []
    
    print("📡 Сбор новостей из RSS-лент...")
    print("-" * 40)
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"   📰 {source_name}...")
        
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                print(f"      ⚠️ Ошибка парсинга, пропускаем")
                continue
            
            for entry in feed.entries[:8]:  # 8 свежих с каждого источника
                # Извлекаем дату
                pub_date = datetime.now().isoformat()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                
                # Очищаем HTML из описания
                summary = entry.get('summary', '')
                summary_clean = BeautifulSoup(summary, 'html.parser').get_text()[:300]
                
                article = {
                    "title": entry.get('title', '').strip(),
                    "summary": summary_clean,
                    "content": summary_clean,
                    "link": entry.get('link', ''),
                    "source": source_name,
                    "published_at": pub_date,
                    "tags": get_tags(entry.get('title', ''), summary_clean),
                    "real_sources": [source_name],
                    "image_url": None,
                }
                
                if article['title']:
                    all_articles.append(article)
                    
        except Exception as e:
            print(f"      ❌ Ошибка: {str(e)[:50]}")
        
        time.sleep(0.3)  # Вежливость к серверам
    
    # Удаляем дубликаты по заголовку
    unique = {}
    for article in all_articles:
        title_hash = hashlib.md5(article['title'].encode()).hexdigest()
        if title_hash not in unique:
            unique[title_hash] = article
    
    result = list(unique.values())
    
    # Сортируем по дате (свежие сверху)
    result.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    print("-" * 40)
    print(f"✅ Собрано {len(result)} уникальных новостей из {len(RSS_FEEDS)} источников")
    
    return result

def save_articles(articles: List[Dict[str, Any]]):
    """Сохраняет новости в JSON"""
    
    data = {
        "articles": articles[:MAX_ARTICLES],
        "last_updated": datetime.now().isoformat(),
        "total_articles": len(articles),
        "sources_count": len(RSS_FEEDS)
    }
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Сохранено в {NEWS_FILE}")

def update_html(articles: List[Dict[str, Any]]):
    """Обновляет index.html с новостями"""
    
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Актуальные новости | Cognify AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 40px; }
        .header h1 { font-size: 3rem; margin-bottom: 10px; }
        .stats { display: flex; justify-content: center; gap: 30px; margin-top: 20px; font-size: 0.9rem; }
        .news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 25px; }
        .news-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        .news-card:hover { transform: translateY(-5px); }
        .card-content { padding: 20px; }
        .source {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            margin-bottom: 12px;
        }
        .title { font-size: 1.3rem; font-weight: 600; margin-bottom: 12px; line-height: 1.4; }
        .title a { color: #333; text-decoration: none; }
        .title a:hover { color: #667eea; }
        .summary { color: #666; line-height: 1.5; margin-bottom: 15px; font-size: 0.95rem; }
        .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
        .tag { background: #f0f0f0; padding: 3px 10px; border-radius: 15px; font-size: 0.7rem; color: #666; }
        .meta { font-size: 0.8rem; color: #999; margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; }
        .footer { text-align: center; margin-top: 50px; color: white; opacity: 0.8; }
        @media (max-width: 768px) {
            .news-grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Актуальные новости</h1>
            <div class="stats">
                <span>📊 Новостей: """ + str(len(articles)) + """</span>
                <span>📡 Источников: """ + str(len(RSS_FEEDS)) + """</span>
                <span>🕐 Обновлено: """ + datetime.now().strftime('%d.%m.%Y %H:%M') + """</span>
            </div>
        </div>
        <div class="news-grid">
"""
    
    for article in articles[:50]:
        source = article.get('source', 'Unknown')
        title = article.get('title', '')
        summary = article.get('summary', '')[:200]
        link = article.get('link', '#')
        tags = article.get('tags', [])
        
        try:
            pub_date = datetime.fromisoformat(article.get('published_at', '')).strftime('%d.%m.%Y %H:%M')
        except:
            pub_date = 'Недавно'
        
        html += f"""
            <div class="news-card">
                <div class="card-content">
                    <span class="source">📌 {source}</span>
                    <div class="title">
                        <a href="{link}" target="_blank">{title}</a>
                    </div>
                    <div class="summary">{summary}...</div>
                    <div class="tags">
"""
        for tag in tags[:3]:
            html += f'<span class="tag">#{tag}</span>'
        
        html += f"""
                    </div>
                    <div class="meta">🕐 {pub_date}</div>
                </div>
            </div>
"""
    
    html += """
        </div>
        <div class="footer">
            <p>© 2026 Cognify AI — Реальные новости из RSS-лент</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("🌐 Обновлён index.html")

def main():
    print("=" * 50)
    print("🚀 ЗАПУСК АГРЕГАТОРА РЕАЛЬНЫХ НОВОСТЕЙ")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    articles = fetch_articles()
    
    if articles:
        save_articles(articles)
        update_html(articles)
        print("\n" + "=" * 50)
        print("✅ ГОТОВО!")
        print(f"📁 {NEWS_FILE}")
        print(f"🌐 index.html")
        print("=" * 50)
        
        # Показываем 5 последних
        print("\n📰 Последние новости:")
        for i, art in enumerate(articles[:5], 1):
            print(f"   {i}. {art['title'][:70]}...")
            print(f"      📍 {art['source']}")
    else:
        print("\n❌ Не удалось загрузить новости")

if __name__ == "__main__":
    main()
