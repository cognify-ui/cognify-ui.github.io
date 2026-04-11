#!/usr/bin/env python3
# news_generator.py - Автоматический сбор и генерация новостей AI
# Запуск: python news_generator.py

import json
import os
import requests
from datetime import datetime
from typing import List, Dict
import hashlib

# ============================================
# КОНФИГУРАЦИЯ
# ============================================
NEWS_FILE = "news.json"
MAX_ARTICLES = 50  # Максимум новостей в файле

# RSS источники (бесплатные, не требуют API)
RSS_SOURCES = [
    {
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "name": "The Verge AI"
    },
    {
        "url": "https://huggingface.co/blog/feed.xml",
        "name": "Hugging Face"
    },
    {
        "url": "https://arxiv.org/rss/cs.AI",
        "name": "arXiv AI"
    },
    {
        "url": "https://www.artificialintelligence-news.com/feed/",
        "name": "AI News"
    },
    {
        "url": "https://www.technologyreview.com/feed/ai/",
        "name": "MIT Tech Review"
    },
    {
        "url": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
        "name": "ScienceDaily AI"
    }
]

# Если есть Groq API ключ (опционально, для улучшения качества)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
USE_AI_ENHANCE = bool(GROQ_API_KEY)

# ============================================
# ФУНКЦИИ
# ============================================

def fetch_rss_feed(url: str) -> List[Dict]:
    """Получает и парсит RSS ленту"""
    try:
        # Используем feedparser
        import feedparser
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries[:5]:  # Берем 5 свежих из каждого источника
            # Получаем дату
            pub_date = entry.get('published', entry.get('updated', datetime.now().isoformat()))
            
            # Генерируем уникальный ID
            article_id = hashlib.md5(entry.link.encode()).hexdigest()[:12]
            
            articles.append({
                "id": article_id,
                "title": entry.title,
                "summary": clean_html(entry.get('summary', entry.get('description', ''))[:300]),
                "content": clean_html(entry.get('summary', entry.get('description', ''))),
                "link": entry.link,
                "published": pub_date,
                "source": feed.feed.get('title', 'Unknown')
            })
        
        return articles
    except Exception as e:
        print(f"❌ Ошибка RSS {url}: {e}")
        return []

def clean_html(text: str) -> str:
    """Очищает HTML теги"""
    import re
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def enhance_with_ai(article: Dict) -> Dict:
    """Улучшает новость через Groq (опционально)"""
    if not USE_AI_ENHANCE:
        return article
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt = f"""
Ты — редактор AI новостей. Перепиши эту новость на русском языке.

Оригинал:
Заголовок: {article['title']}
Текст: {article['summary']}

Сделай:
1. Заголовок короче и кликбейтнее (макс 60 символов)
2. Краткое содержание (2-3 предложения) с ключевыми фактами
3. 2-4 тега (на английском, строчные)

Ответ дай строго в формате JSON:
{{"title": "новый заголовок", "summary": "краткое содержание", "tags": ["tag1", "tag2"]}}
"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        
        result = json.loads(response.choices[0].message.content)
        
        article['title'] = result.get('title', article['title'])
        article['summary'] = result.get('summary', article['summary'])
        article['tags'] = result.get('tags', ['ai', 'news'])
        
    except Exception as e:
        print(f"⚠️ AI enhancement failed: {e}")
        article['tags'] = ['ai', 'news']
    
    return article

def generate_tags_from_title(title: str) -> List[str]:
    """Генерирует теги из заголовка (без AI)"""
    tags = []
    keywords = {
        'groq': 'groq', 'cerebras': 'cerebras', 'gemini': 'gemini',
        'google': 'google', 'openai': 'openai', 'chatgpt': 'chatgpt',
        'claude': 'claude', 'anthropic': 'anthropic', 'meta': 'meta',
        'llama': 'llama', 'mistral': 'mistral', 'ai': 'ai',
        'ml': 'ml', 'machine learning': 'ml', 'deep learning': 'deep-learning'
    }
    
    title_lower = title.lower()
    for key, tag in keywords.items():
        if key in title_lower:
            tags.append(tag)
    
    if not tags:
        tags = ['ai', 'news']
    
    return tags[:4]  # Не больше 4 тегов

def update_news_json(new_articles: List[Dict]) -> int:
    """Обновляет news.json, добавляя новые статьи"""
    # Загружаем существующие новости
    existing = {"last_updated": "", "articles": []}
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    # Собираем существующие ID и ссылки
    existing_ids = {a.get('id') for a in existing.get('articles', [])}
    existing_links = {a.get('source_url') for a in existing.get('articles', []) if a.get('source_url')}
    
    new_count = 0
    for article in new_articles:
        # Проверяем, нет ли уже такой новости
        if article['id'] in existing_ids:
            continue
        if article.get('link') in existing_links:
            continue
        
        # Подготавливаем статью
        formatted_article = {
            "id": article['id'],
            "title": article['title'][:100],  # Ограничиваем длину
            "summary": article['summary'][:250],
            "content": article['content'][:1500] if article['content'] else article['summary'],
            "source": article.get('source', 'AI News'),
            "source_url": article.get('link', ''),
            "published_at": article.get('published', datetime.now().isoformat()),
            "tags": article.get('tags', generate_tags_from_title(article['title']))
        }
        
        # Добавляем изображение, если есть (опционально)
        # formatted_article["image_url"] = ""  # Можно добавить позже
        
        existing['articles'].insert(0, formatted_article)
        new_count += 1
    
    # Оставляем только MAX_ARTICLES последних
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    
    # Сохраняем
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    return new_count

def main():
    print(f"🚀 Запуск генератора новостей {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 Источников: {len(RSS_SOURCES)}")
    print(f"🤖 AI улучшение: {'ВКЛ' if USE_AI_ENHANCE else 'ВЫКЛ'}")
    print("-" * 50)
    
    all_articles = []
    
    for source in RSS_SOURCES:
        print(f"📥 Парсинг: {source['name']}...")
        articles = fetch_rss_feed(source['url'])
        
        for article in articles:
            article['source'] = source['name']
            if USE_AI_ENHANCE:
                article = enhance_with_ai(article)
            else:
                article['tags'] = generate_tags_from_title(article['title'])
            all_articles.append(article)
        
        print(f"   ✅ Найдено {len(articles)} новостей")
    
    print("-" * 50)
    print(f"📊 Всего собрано: {len(all_articles)} новостей")
    
    # Удаляем дубликаты по ссылке
    unique_articles = []
    seen_links = set()
    for article in all_articles:
        if article['link'] not in seen_links:
            seen_links.add(article['link'])
            unique_articles.append(article)
    
    print(f"🔄 Уникальных: {len(unique_articles)}")
    
    # Обновляем JSON
    new_count = update_news_json(unique_articles)
    print(f"✨ Добавлено новых: {new_count}")
    print(f"💾 Сохранено в {NEWS_FILE}")
    print("✅ Готово!")

if __name__ == "__main__":
    main()
