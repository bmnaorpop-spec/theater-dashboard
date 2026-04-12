import json
import asyncio
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

async def scrape_theater(page, theater_name, url, selector, title_sub, date_sub):
    results = []
    try:
        print(f"סורק {theater_name}...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000) # המתנה נוספת לטעינה דינמית
        
        items = await page.query_selector_all(selector)
        for item in items:
            title = await item.query_selector(title_sub)
            date = await item.query_selector(date_sub)
            if title and date:
                results.append({
                    "theater": theater_name,
                    "title": (await title.inner_text()).strip(),
                    "date": (await date.inner_text()).strip()
                })
        print(f"נמצאו {len(results)} הופעות ב{theater_name}")
    except Exception as e:
        print(f"שגיאה ב{theater_name}: {e}")
    return results

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        all_results = []
        
        # רשימת התיאטראות - מחזירים את כולם!
        theaters = [
            ("הקאמרי", "https://www.cameri.co.il/לוח-הופעות/", ".event-item", ".event-name", ".event-date"),
            ("הבימה", "https://www.habima.co.il/presentations/", ".presentation-item", ".title", ".date"),
            ("גשר", "https://www.gesher-theatre.co.il/he/company/a/calendar/", ".show_item", ".show_name", ".show_date"),
            ("בית ליסין", "https://www.lessin.co.il/הצגות/", ".showlistitem", ".showname", ".showdate"),
            ("צוותא", "https://www.tzavta.co.il/shows/4", ".schedule_item", ".show_title", ".show_date"),
            ("תיאטרון ירושלים", "https://www.jerusalem-theatre.co.il/לוח_אירועים", ".event-item", "h3", ".date"),
            ("החאן", "https://www.khan.co.il/shows-list", ".board-item", ".title", ".date"),
            ("אינקובטור", "https://incubator.org.il/show-type/play-category/", ".jet-listing-grid__item", ".jet-listing-dynamic-field__content", ".jet-listing-dynamic-field__content"),
            ("תיאטרון הבית", "https://www.habait-theatre.org.il/he/shows", ".project-item", ".project-title", ".project-title"),
            ("ניקו ניתאי", "https://nikonitai.smarticket.co.il/", ".show_cube", ".show_name", ".show_datetime"),
            ("קליפה", "https://clipa.co.il/#run-on-clipa", ".hp-featured-show", ".show-title", ".top-r-date")
        ]

        for theater in theaters:
            res = await scrape_theater(page, *theater)
            all_results.extend(res)

        # שמירה לקובץ
        with open("all_theaters_schedule.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        
        print(f"--- סיכום: {len(all_results)} הופעות נשמרו ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
