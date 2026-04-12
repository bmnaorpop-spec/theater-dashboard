import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# הגדרת User-Agent כדי למנוע חסימות של בוטים
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

async def scrape_cameri(browser):
    """סורק את אתר הקאמרי"""
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    results = []
    try:
        print("מתחיל סריקת קאמרי...")
        await page.goto("https://www.cameri.co.il/לוח-הופעות/", wait_until="networkidle")
        
        # לוגיקה לחילוץ ההצגות (מותאם למבנה האתר)
        shows = await page.query_selector_all(".event-item")
        for show in shows:
            title = await show.query_selector(".event-name")
            date = await show.query_selector(".event-date")
            if title and date:
                results.append({
                    "theater": "הקאמרי",
                    "title": (await title.inner_text()).strip(),
                    "date": (await date.inner_text()).strip()
                })
        print(f"סריקת קאמרי הושלמה: נמצאו {len(results)} הופעות")
    except Exception as e:
        print(f"שגיאה בסריקת הקאמרי: {e}")
    finally:
        await context.close()
    return results

async def scrape_habima(browser):
    """סורק את אתר הבימה"""
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    results = []
    try:
        print("מתחיל סריקת הבימה...")
        await page.goto("https://www.habima.co.il/presentations/", wait_until="networkidle")
        
        shows = await page.query_selector_all(".presentation-item")
        for show in shows:
            title = await show.query_selector(".title")
            date = await show.query_selector(".date")
            if title and date:
                results.append({
                    "theater": "הבימה",
                    "title": (await title.inner_text()).strip(),
                    "date": (await date.inner_text()).strip()
                })
        print(f"סריקת הבימה הושלמה: נמצאו {len(results)} הופעות")
    except Exception as e:
        print(f"שגיאה בסריקת הבימה: {e}")
    finally:
        await context.close()
    return results

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # ריצה על כל התיאטראות (אפשר להוסיף כאן את שאר הפונקציות שלך)
        cameri_results = await scrape_cameri(browser)
        habima_results = await scrape_habima(browser)
        
        all_results = cameri_results + habima_results
        
        # שמירה לקובץ JSON
        with open("all_theaters_schedule.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        
        print(f"סיום: סה''כ נשמרו {len(all_results)} הופעות בקובץ ה-JSON")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
