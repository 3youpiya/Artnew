import os
import json
import requests
from playwright.sync_api import sync_playwright

TARGET_URL = "https://artale.live/tw/news"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = "seen.json"

def main():
    seen = set(json.load(open(STATE_FILE, encoding="utf-8"))) if os.path.exists(STATE_FILE) else set()
    is_init = len(seen) == 0
    articles = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        # 只要 HTML 載入出公告連結就立刻抓取，不再等待隱藏元素變可見
        page.wait_for_selector('a[href*="/tw/news/"]', state="attached", timeout=20000)
        page.wait_for_timeout(2000)  # 緩衝 2 秒確保所有標題渲染完成
        
        for link in page.query_selector_all('a[href*="/tw/news/"]'):
            href = link.get_attribute("href")
            if href and href != "/tw/news" and "/tw/news/" in href:
                url = f"https://artale.live{href}" if href.startswith("/") else href
                title = " ".join((link.text_content() or "").split())
                if title and url not in [a["url"] for a in articles]:
                    articles.append({"title": title, "url": url})
        browser.close()

    print(f"成功抓取到 {len(articles)} 篇公告")
    updated = False
    for art in reversed(articles):
        if art["url"] not in seen:
            seen.add(art["url"])
            updated = True
            if not is_init:
                requests.post(WEBHOOK_URL, json={
                    "username": "Artale 官網速報",
                    "embeds": [{
                        "title": f"📢 {art['title']}",
                        "url": art["url"],
                        "color": 16753920,
                        "description": f"官網剛剛發布了新公告！\n🔗 {art['url']}"
                    }]
                })

    if updated:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen), f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
