#!/usr/bin/env python3
# news_generator.py - Генератор новостей для Cognify AI

import json
import os
import requests
from datetime import datetime
import hashlib
import feedparser

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

RSS_SOURCES = [
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://www.technologyreview.com/feed/ai/",
    "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
]

def fetch_rss(url):
    """Получает новости из RSS"""
    try:
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries[:5]:
            article_id = hashlib.md5(entry.link.encode()).hexdigest()[:12]
            
            articles.append({
                "id": article_id,
                "title": entry.title,
                "summary": clean_html(entry.get('summary', ''))[:300],
                "content": clean_html(entry.get('summary', ''))[:1000],
                "link": entry.link,
                "published": entry.get('published', datetime.now().isoformat()),
                "source": feed.feed.get('title', 'Unknown')
            })
        
        return articles
    except Exception as e:
        print(f"Ошибка RSS {url}: {e}")
        return []

def clean_html(text):
    """Удаляет HTML теги"""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def update_news_json(new_articles):
    """Обновляет файл новостей"""
    existing = {"last_updated": "", "articles": []}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    existing_ids = {a.get('id') for a in existing.get('articles', [])}
    existing_links = {a.get('source_url') for a in existing.get('articles', []) if a.get('source_url')}
    
    new_count = 0
    for article in new_articles:
        if article['id'] in existing_ids:
            continue
        if article['link'] in existing_links:
            continue
        
        formatted = {
            "id": article['id'],
            "title": article['title'][:100],
            "summary": article['summary'][:250],
            "content": article['content'][:1500] if article['content'] else article['summary'],
            "source": article.get('source', 'AI News'),
            "source_url": article.get('link', ''),
            "published_at": article.get('published', datetime.now().isoformat()),
            "tags": generate_tags(article['title'])
        }
        
        existing['articles'].insert(0, formatted)
        new_count += 1
    
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    return new_count

def generate_tags(title):
    """Генерирует теги из заголовка"""
    title_lower = title.lower()
    tags = []
    
    keywords = {
        'groq': 'groq', 'cerebras': 'cerebras', 'gemini': 'gemini',
        'google': 'google', 'openai': 'openai', 'chatgpt': 'chatgpt',
        'claude': 'claude', 'meta': 'meta', 'llama': 'llama',
        'mistral': 'mistral', 'ai': 'ai', 'ml': 'ml'
    }
    
    for key, tag in keywords.items():
        if key in title_lower:
            tags.append(tag)
    
    return tags[:4] if tags else ['ai', 'news']

def main():
    print(f"🚀 Запуск: {datetime.now()}")
    print(f"📡 Источников: {len(RSS_SOURCES)}")
    print("-" * 40)
    
    all_articles = []
    
    for url in RSS_SOURCES:
        print(f"📥 Парсинг: {url.split('/')[2]}...")
        articles = fetch_rss(url)
        print(f"   ✅ {len(articles)} новостей")
        all_articles.extend(articles)
    
    # Удаляем дубликаты
    unique = []
    seen_links = set()
    for a in all_articles:
        if a['link'] not in seen_links:
            seen_links.add(a['link'])
            unique.append(a)
    
    print(f"📊 Уникальных: {len(unique)}")
    
    new_count = update_news_json(unique)
    print(f"✨ Добавлено новых: {new_count}")
    print("✅ Готово!")

if __name__ == "__main__":
    main()
