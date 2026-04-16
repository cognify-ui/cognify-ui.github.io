#!/usr/bin/env python3
"""
Агрегатор реальных новостей - исправлены дубли картинок и ссылки
"""

import json
import hashlib
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

NEWS_FILE = "news.json"
MAX_ARTICLES = 500

# RSS-источники
RSS_FEEDS = {
    "Habr All": "https://habr.com/ru/rss/hub/all/",
    "Habr IT": "https://habr.com/ru/rss/hub/it_news/",
    "TechCrunch": "https://feeds.feedburner.com/TechCrunch",
    "Wired": "https://www.wired.com/feed/rss",
}

def clean_cdata(text):
    """Убирает обёртку CDATA из текста"""
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text)
    return text.strip()

def clean_html(text):
    """Очищает HTML от тегов, но сохраняет структуру"""
    if not text:
        return ""
    # Заменяем <br> и <p> на переносы строк
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    # Удаляем все остальные HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # Декодируем HTML-сущности
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    return text.strip()

def extract_images_from_html(html_text):
    """Извлекает уникальные изображения из HTML (без дублей)"""
    if not html_text:
        return []
    
    soup = BeautifulSoup(html_text, 'html.parser')
    images = []
    seen_urls = set()
    
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and not src.startswith('data:'):
            if not src.startswith('http'):
                src = 'https:' + src if src.startswith('//') else src
            # Убираем параметры из URL для сравнения
            clean_src = src.split('?')[0]
            if clean_src not in seen_urls:
                seen_urls.add(clean_src)
                images.append(src)
    
    return images

def extract_real_link(item, source_name):
    """Извлекает реальную ссылку на статью, а не на картинку"""
    
    # 1. Пробуем guid (часто содержит правильную ссылку)
    guid = item.find('guid')
    if guid:
        guid_text = guid.get_text(strip=True)
        if guid_text and guid_text.startswith('http') and 'habr.com' in guid_text:
            return guid_text
        if guid_text and guid_text.startswith('http') and not guid_text.endswith(('.jpg', '.png', '.gif', '.jpeg')):
            return guid_text
    
    # 2. Пробуем link
    link_elem = item.find('link')
    if link_elem:
        link_text = link_elem.get_text(strip=True)
        if link_text and link_text.startswith('http'):
            # Проверяем, что это не ссылка на картинку
            if not link_text.lower().endswith(('.jpg', '.png', '.gif', '.jpeg', '.webp')):
                return link_text
        if link_elem.get('href'):
            href = link_elem.get('href')
            if href and href.startswith('http') and not href.lower().endswith(('.jpg', '.png', '.gif', '.jpeg', '.webp')):
                return href
    
    # 3. Для Habr, формируем ссылку из заголовка (как fallback)
    if 'habr' in source_name.lower():
        title_elem = item.find('title')
        if title_elem:
            title = clean_cdata(title_elem.get_text(strip=True))
            # Пытаемся найти ID статьи в контенте
            content = str(item)
            id_match = re.search(r'post/(\d+)', content)
            if id_match:
                return f"https://habr.com/ru/post/{id_match.group(1)}/"
    
    return None

def fetch_rss_feed(url, source_name):
    """Получает и парсит RSS-ленту"""
    articles = []
    try:
        response = requests.get(url, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.find_all('item')
        
        for item in items[:20]:
            # Заголовок
            title_elem = item.find('title')
            if not title_elem:
                continue
            title = clean_cdata(title_elem.get_text(strip=True))
            if not title:
                continue
            
            # Реальная ссылка на статью (НЕ на картинку!)
            link = extract_real_link(item, source_name)
            if not link:
                print(f"     ⚠️ Нет ссылки на статью: {title[:50]}...")
                continue
            
            # Получаем полный контент
            full_content = ""
            images = []
            preview_image = None
            
            # Пробуем content:encoded
            content_elem = item.find('content:encoded')
            if content_elem:
                raw_content = clean_cdata(content_elem.get_text(strip=True))
                images = extract_images_from_html(raw_content)
                full_content = clean_html(raw_content)
            
            # Если нет, берем description
            if not full_content:
                desc_elem = item.find('description')
                if desc_elem:
                    raw_desc = clean_cdata(desc_elem.get_text(strip=True))
                    images = extract_images_from_html(raw_desc)
                    full_content = clean_html(raw_desc)
            
            # Убираем дубли картинок из контента (чтобы не показывать дважды)
            for img_url in images:
                full_content = full_content.replace(f'![]({img_url})', '')
                full_content = full_content.replace(f'<img src="{img_url}">', '')
            
            # Первое изображение как превью (только одно!)
            if images:
                preview_image = images[0]
                # Оставляем только первое изображение в списке, чтобы не было дублей
                images = [preview_image]
            
            # Ограничиваем длину до 5000 символов
            if len(full_content) > 5000:
                full_content = full_content[:5000] + "\n\n...(продолжение в оригинале)"
            
            # Краткое описание (первые 300 символов)
            summary = full_content[:300] if full_content else ""
            
            # Дата
            date_elem = item.find('pubDate')
            pub_date = date_elem.get_text(strip=True) if date_elem else datetime.now().isoformat()
            
            articles.append({
                "id": hashlib.md5(title.encode()).hexdigest()[:16],
                "title": title,
                "summary": summary,
                "content": full_content,
                "link": link,  # Теперь это реальная ссылка на статью!
                "source": source_name,
                "published_at": pub_date,
                "tags": ["AI", "технологии", "IT"],
                "images": images,  # Только уникальные изображения, без дублей
                "preview_image": preview_image,  # Только одно изображение для превью
            })
            
            print(f"     ✅ {title[:40]}... → {link[:50]}...")
            
    except Exception as e:
        print(f"  ❌ {source_name}: {str(e)[:50]}")
    
    return articles

def fetch_all_news():
    """Собирает новости со всех источников"""
    all_articles = []
    print("📡 Сбор новостей...")
    print("=" * 50)
    
    for name, url in RSS_FEEDS.items():
        print(f"  📰 {name}...")
        articles = fetch_rss_feed(url, name)
        print(f"     ✅ {len(articles)} новостей с правильными ссылками")
        all_articles.extend(articles)
        time.sleep(1)
    
    # Удаляем дубликаты по заголовку
    unique = {}
    for article in all_articles:
        if article['title'] not in unique:
            unique[article['title']] = article
    
    result = list(unique.values())
    print("=" * 50)
    print(f"📊 Итого: {len(result)} уникальных новостей")
    
    with_links = sum(1 for a in result if a.get('link') and not a['link'].endswith(('.jpg', '.png', '.gif')))
    print(f"🔗 Новостей со ссылками на статьи: {with_links}")
    
    return result

def save_news(articles):
    """Сохраняет новости в JSON"""
    data = {
        "articles": articles[:MAX_ARTICLES],
        "last_updated": datetime.now().isoformat(),
        "total_articles": len(articles),
        "sources": list(RSS_FEEDS.keys())
    }
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Сохранено в {NEWS_FILE}")

def main():
    print("=" * 55)
    print("🚀 АГРЕГАТОР НОВОСТЕЙ (исправлены дубли картинок и ссылки)")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    
    articles = fetch_all_news()
    
    if articles:
        save_news(articles)
        print("\n📰 Последние новости:")
        for i, art in enumerate(articles[:5], 1):
            print(f"   {i}. {art['title'][:60]}...")
            print(f"      📍 {art['source']}")
            print(f"      🔗 {art.get('link', 'НЕТ ССЫЛКИ!')[:60]}...")
            if art['images']:
                print(f"      🖼️ {len(art['images'])} картинка")
            print()
    else:
        print("\n⚠️ Не удалось загрузить новости")

if __name__ "__main__":
    main()
