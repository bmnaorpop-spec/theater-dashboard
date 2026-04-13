"""
theater_orchestrator.py  –  סריקת לוחות הצגות תיאטראות ישראל
==============================================================
גרסה עובדת — אפריל 2026. סה"כ ~609 הופעות מ-7 תיאטראות.

אסטרטגיית סריקה לפי אתר:
  קאמרי     – DOM: FullCalendar (.fc-event, data-date, .time)
  ליסין      – DOM: .showlistitem עם data-date attribute
  הבימה      – Network listener → allData.json (Unix timestamps)
  גשר        – Regex על script block (פורמט טקסט מובנה)
  צוותא      – DOM: .shedule_item (שגיאת כתיב באתר — כוונה)
  ירושלים    – API: na_ajax.php?action=getBoard, מסונן ל-eventGrp_theatre
  החאן       – DOM: .board-day > .board-shows

דרישות: pip install playwright && playwright install chromium
"""

import json
import datetime
import asyncio
import re
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ─────────────────────────────────────────────
# כלי עזר
# ─────────────────────────────────────────────

async def safe_text(element, selector: str) -> str:
    """שליפת טקסט בטוחה – מחזיר מחרוזת ריקה אם לא נמצא"""
    try:
        el = await element.query_selector(selector)
        return (await el.inner_text()).strip() if el else ""
    except Exception:
        return ""


async def auto_scroll(page):
    """גלילה איטית לחשיפת Lazy Loading"""
    await page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 150;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 120);
            });
        }
    """)


async def goto_safe(page, url: str, wait: str = "networkidle", timeout: int = 90_000):
    """ניווט בטוח עם fallback ל-domcontentloaded"""
    try:
        await page.goto(url, wait_until=wait, timeout=timeout)
    except Exception:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"  ⚠️  goto נכשל: {e}")


# ─────────────────────────────────────────────
# סריקות ספציפיות לכל תיאטרון
# ─────────────────────────────────────────────

async def scrape_cameri(page) -> list[dict]:
    """
    הקאמרי – לוח אירועים מבוסס FullCalendar.
    כל הופעה היא .fc-event עם data-date + .go-to-show-page (שם) + .time (שעה).
    מה-debug: .fc-event ×154, data-date ×61, .time ×192, .go-to-show-page ×154
    """
    results = []
    theater = "הקאמרי"
    url = "https://www.cameri.co.il/%D7%9C%D7%95%D7%97-%D7%94%D7%95%D7%A4%D7%A2%D7%95%D7%AA/"
    try:
        print(f"--- מתחיל סריקה: {theater} ---")
        await goto_safe(page, url, wait="networkidle")
        await page.wait_for_timeout(4000)

        items = await page.query_selector_all(".fc-event")
        for item in items:
            # שם ההצגה
            t = await safe_text(item, ".go-to-show-page")
            if not t:
                t = await safe_text(item, ".category_name")
            # תאריך מה-data attribute
            date_val = await item.get_attribute("data-date") or ""
            # שעה
            time_val = await safe_text(item, ".time")
            if not time_val:
                time_val = await safe_text(item, ".calendar-show-time-button")
            if t:
                results.append({
                    "theater": theater,
                    "title": t,
                    "date": date_val,
                    "time": time_val,
                })

        # fallback: event-item-inner (תצוגת רשימה)
        if not results:
            items = await page.query_selector_all(".event-item-inner")
            for item in items:
                t = await safe_text(item, ".go-to-show-page")
                d = await safe_text(item, ".date")
                tm = await safe_text(item, ".time")
                if t:
                    results.append({"theater": theater, "title": t, "date": d, "time": tm})

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_lessin(page) -> list[dict]:
    """
    בית ליסין – .showlistitem ×153, data-date ×150, .sec (שעה) ×149
    כל שורה = תאריך+שעה+שם. השם ב-.hidemobile, השעה ב-.sec, התאריך ב-data-date.
    """
    results = []
    theater = "בית ליסין"
    url = "https://www.lessin.co.il/%D7%94%D7%A6%D7%92%D7%95%D7%AA/"
    try:
        print(f"--- מתחיל סריקה: {theater} ---")
        await goto_safe(page, url, wait="networkidle")
        await page.wait_for_timeout(4000)

        items = await page.query_selector_all(".showlistitem")
        for item in items:
            # שם: .hidemobile (הטקסט של שם ההצגה בדסקטופ)
            t = await safe_text(item, ".hidemobile")
            if not t:
                t = await safe_text(item, "a")
            # תאריך: data-date attribute על האלמנט עצמו
            date_val = await item.get_attribute("data-date") or ""
            # שעה: .sec
            time_val = await safe_text(item, ".sec")
            if t:
                results.append({
                    "theater": theater,
                    "title": t,
                    "date": date_val,
                    "time": time_val,
                })

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_habima(page) -> list[dict]:
    """
    הבימה – גישה ישירה ל-API:
    1. allData.json  → show_id → רשימת הופעות עם Unix timestamps
    2. דף presentations/ → כרטיסי הצגות עם data-show-id + שם

    ה-URL של allData.json משתנה עם query param ?v=HASH.
    אנחנו מאזינים ל-network response כדי לתפוס את ה-URL המדויק.
    """
    import datetime
    results = []
    theater = "הבימה"
    url = "https://www.habima.co.il/presentations/"

    try:
        print(f"--- מתחיל סריקה: {theater} ---")

        all_data_json = {}
        all_data_captured = asyncio.Event()

        async def capture_all_data(response):
            if "allData.json" in response.url and response.status == 200:
                try:
                    body = await response.json()
                    all_data_json.update(body)
                    all_data_captured.set()
                except Exception:
                    pass

        page.on("response", capture_all_data)

        await goto_safe(page, url, wait="networkidle")

        # המתן עד ל-allData.json (עד 15 שניות)
        try:
            await asyncio.wait_for(all_data_captured.wait(), timeout=15)
            print(f"  ✅ allData.json נתפס")
        except asyncio.TimeoutError:
            print(f"  ⚠️  allData.json לא נתפס – מנסה fetch ישיר")
            # fallback: חפש את ה-URL מתוך ה-HTML
            content = await page.content()
            match = re.search(r'cache/allData\.json\?v=\w+', content)
            if match:
                data_url = f"https://www.habima.co.il/wp-content/themes/tyco-wp/{match.group()}"
                resp = await page.evaluate(f"fetch('{data_url}').then(r=>r.json())")
                all_data_json.update(resp)

        page.remove_listener("response", capture_all_data)

        if not all_data_json:
            print(f"  ❌ לא הצלחנו לטעון allData.json")
            _log(theater, results)
            return results

        # שלב 2: שלוף שמות הצגות מה-DOM (כרטיסים עם data-show-id או קישורים ל-/shows/)
        await page.wait_for_timeout(3000)

        # בנה מפה: show_id -> title
        show_names: dict[str, str] = {}

        # נסה data-show-id attributes
        cards = await page.query_selector_all("[data-show-id]")
        for card in cards:
            sid = await card.get_attribute("data-show-id")
            title_el = await card.query_selector("h2, h3, .title, .show-title")
            t = (await title_el.inner_text()).strip() if title_el else (await card.inner_text()).strip()
            if sid and t:
                show_names[sid] = t

        # fallback: קישורים ל-/shows/SLUG — חלץ ID מה-slug
        if not show_names:
            links = await page.query_selector_all("a[href*='/shows/']")
            for link in links:
                href = await link.get_attribute("href") or ""
                # נסה לחלץ מספר מה-href (אם קיים) או שמור לפי slug
                t = (await link.inner_text()).strip()
                m = re.search(r'/shows/(\w+)', href)
                if m and t and len(t) > 1:
                    show_names[m.group(1)] = t

        # שלב 3: בנה רשימת הופעות
        presentations = all_data_json.get("presentations", {})
        he_shows = presentations.get("he", presentations.get("en", {}))

        for show_id, performances in he_shows.items():
            title = show_names.get(str(show_id), f"הצגה #{show_id}")
            for perf in performances:
                ts = perf.get("time", 0)
                if ts:
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc) \
                         + datetime.timedelta(hours=3)  # Israel Standard Time (UTC+3)
                    date_str = dt.strftime("%d/%m/%Y")
                    time_str = dt.strftime("%H:%M")
                else:
                    date_str, time_str = "—", ""

                results.append({
                    "theater": theater,
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "show_id": show_id,
                })

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_gesher(page) -> list[dict]:
    """
    גשר – https://www.gesher-theatre.co.il/he/company/a/calendar/
    האתר חושף את כל הנתונים ב-script block בטקסט רגיל:
      "שם הצגה - DD.MM - ID"
    ואחריו רשימת תאריכים בפורמט DD/MM/YYYY HH:MM
    חילוץ ישיר מה-HTML ללא DOM!
    """
    results = []
    theater = "גשר"
    url = "https://www.gesher-theatre.co.il/he/company/a/calendar/"
    try:
        print(f"--- מתחיל סריקה: {theater} ---")
        await goto_safe(page, url)
        await page.wait_for_timeout(3000)

        # שליפת כל תוכן הדף כטקסט
        content = await page.content()

        # שלב 1: מצא שורות בצורה "שם הצגה - DD.M - ID"
        show_lines = re.findall(r"([^\n\r<>]+?) - (\d{1,2}\.\d{1,2}) - (\d{4,})", content)

        # שלב 2: מצא תאריכים בפורמט DD/MM/YYYY HH:MM
        date_times = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", content)

        # בניית מילון: מפתח = ID, ערך = (שם, תאריך קצר)
        show_by_id: dict[str, tuple[str, str]] = {}
        for name, short_date, show_id in show_lines:
            name = name.strip()
            if name and not name.startswith("Storage") and len(name) > 1:
                show_by_id[show_id] = (name, short_date)

        # בניית שורות מהרשימה הסדורה
        if date_times:
            # יש לנו רשימת תאריכים – מתאם לפי סדר עם show_lines
            shows_ordered = [(n, d) for _, (n, d) in sorted(
                show_by_id.items(), key=lambda x: int(x[0])
            )]
            for i, (full_date, time_str) in enumerate(date_times):
                title = shows_ordered[i % len(shows_ordered)][0] if shows_ordered else "—"
                results.append({
                    "theater": theater,
                    "title": title,
                    "date": full_date,
                    "time": time_str,
                })
        else:
            # fallback: רק שמות + תאריכים קצרים
            for show_id, (name, short_date) in show_by_id.items():
                results.append({
                    "theater": theater,
                    "title": name,
                    "date": short_date,
                    "time": "",
                })

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_tzavta(page) -> list[dict]:
    """
    צוותא – .shedule_item ×30, .shedule_name_txt (שם), .shedule_date_txt (תאריך), .time (שעה)
    שים לב: שגיאת כתיב באתר — shedule ולא schedule.
    """
    results = []
    theater = "צוותא"
    url = "https://www.tzavta.co.il/shows/4"
    try:
        print(f"--- מתחיל סריקה: {theater} ---")
        await goto_safe(page, url, wait="networkidle")
        await page.wait_for_timeout(4000)

        items = await page.query_selector_all(".shedule_item")
        for item in items:
            t = await safe_text(item, ".shedule_name_txt")
            d = await safe_text(item, ".shedule_date_txt")
            tm = await safe_text(item, ".time")
            if not t:
                t = await safe_text(item, ".name")
            if t:
                results.append({
                    "theater": theater,
                    "title": t,
                    "date": d or "—",
                    "time": tm,
                })

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_jerusalem(page) -> list[dict]:
    """
    תיאטרון ירושלים – API ישיר:
      GET https://www.jerusalem-theatre.co.il/na_ajax.php?action=getBoard
      מחזיר JSON: {"items": {"<unix_ts>": {"id":..,"title":..,"date_next":..,"type":..}, ...}}

    הממצא מ-inspect: .details×72, data-id×72 — גיבוי דרך DOM אם ה-API נכשל.
    """
    results = []
    theater = "תיאטרון ירושלים"
    api_url = "https://www.jerusalem-theatre.co.il/na_ajax.php?action=getBoard"

    try:
        print(f"--- מתחיל סריקה: {theater} ---")

        # ─── שלב 1: נסה API ישיר ─────────────────────────────
        api_captured = {}
        captured_event = asyncio.Event()

        async def capture_board(response):
            if "na_ajax.php" in response.url and response.status == 200:
                try:
                    body = await response.json(content_type=None)
                    api_captured.update(body)
                    captured_event.set()
                except Exception:
                    pass

        page.on("response", capture_board)

        await goto_safe(page, "https://www.jerusalem-theatre.co.il/%D7%9C%D7%95%D7%97_%D7%90%D7%99%D7%A8%D7%95%D7%A2%D7%99%D7%9D",
                        wait="networkidle")

        try:
            await asyncio.wait_for(captured_event.wait(), timeout=15)
            print(f"  ✅ getBoard API נתפס")
        except asyncio.TimeoutError:
            # fallback: fetch ישיר דרך הדפדפן (כדי לעבור CORS/cookies)
            print(f"  ⚠️  API לא נתפס אוטומטית – מנסה fetch ידני")
            try:
                raw = await page.evaluate(
                    f"fetch('{api_url}').then(r=>r.json())"
                )
                api_captured.update(raw)
                print(f"  ✅ fetch ידני הצליח")
            except Exception as e:
                print(f"  ❌ fetch ידני נכשל: {e}")

        page.remove_listener("response", capture_board)

        # ─── שלב 2: עבד את ה-JSON ────────────────────────────
        if api_captured:
            items = api_captured.get("items", {})

            # הדפס קטגוריות קיימות בפעם הראשונה לאבחון
            groups_seen = set(ev.get("parent-group", "") for ev in items.values())
            print(f"  קטגוריות בלוח: {groups_seen}")

            # סינון: רק תיאטרון
            THEATRE_GROUP = "eventGrp_theatre"

            for ts_str, ev in items.items():
                if ev.get("parent-group") != THEATRE_GROUP:
                    continue

                title = ev.get("title", "").strip()
                if not title:
                    continue

                # כל מועד בנפרד (dates = רשימת כל ההופעות של אירוע זה)
                dates = ev.get("dates", [])
                if not dates:
                    dates = [{"date": int(ts_str)}]

                for date_entry in dates:
                    ts = int(date_entry.get("date", ts_str))
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc) \
                         + datetime.timedelta(hours=3)
                    date_str = dt.strftime("%d/%m/%Y")
                    time_str = dt.strftime("%H:%M")
                    hall = date_entry.get("hall", "")
                    status = date_entry.get("status", "")

                    results.append({
                        "theater": theater,
                        "title": title,
                        "date": date_str,
                        "time": time_str,
                        "hall": hall,
                        "status": status,
                    })

        # ─── שלב 3: fallback DOM ─────────────────────────────
        if not results:
            print(f"  ⚠️  API ריק – חוזר ל-DOM (.details)")
            await page.wait_for_timeout(3000)
            dom_items = await page.query_selector_all(".details")
            for item in dom_items:
                # .name מכיל cat+title צמודים — ננסה data-id להפריד
                data_id = await item.get_attribute("data-id")
                t = await safe_text(item, ".name")
                cat = await safe_text(item, ".cat-name")
                # הסר את שם הקטגוריה מתחילת הכותרת אם הוא צמוד
                if cat and t.startswith(cat):
                    t = t[len(cat):].strip()
                d = await safe_text(item, ".date")
                if t and len(t) > 1:
                    results.append({
                        "theater": theater,
                        "title": t,
                        "date": d or "—",
                        "time": "",
                        "category": cat,
                    })

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


async def scrape_khan(page) -> list[dict]:
    """
    החאן – .board-day ×32 מכיל: .date (תאריך היום), ובתוכו .board-shows עם .info (שם) + .hall (אולם)
    .ticket ×72 = כפתורי רכישה (לא נצטרך)
    """
    results = []
    theater = "החאן"
    url = "https://www.khan.co.il/shows-list"
    try:
        print(f"--- מתחיל סריקה: {theater} ---")
        await goto_safe(page, url, wait="networkidle")
        await page.wait_for_timeout(5000)

        # כל board-day הוא יום בלוח — שולפים תאריך ואז את ההצגות בתוכו
        days = await page.query_selector_all(".board-day")
        for day in days:
            date_val = await safe_text(day, ".date")
            shows = await day.query_selector_all(".board-shows")
            if not shows:
                # fallback: כל .info ישיר בתוך ה-day
                shows = [day]
            for show in shows:
                t = await safe_text(show, ".info")
                hall = await safe_text(show, ".hall")
                # שעה לפעמים מופיעה ב-.group
                tm = await safe_text(show, ".group")
                if t and len(t) > 1:
                    results.append({
                        "theater": theater,
                        "title": t,
                        "date": date_val or "—",
                        "time": tm,
                        "hall": hall,
                    })

        # fallback: אם board-day לא עבד — נסה .wrapper
        if not results:
            items = await page.query_selector_all(".wrapper")
            for item in items:
                t = await safe_text(item, ".info")
                d = await safe_text(item, ".date")
                if t and len(t) > 1:
                    results.append({"theater": theater, "title": t, "date": d, "time": ""})

        _log(theater, results)
    except Exception as e:
        print(f"❌ שגיאה ב{theater}: {e}")
    return results


# ─────────────────────────────────────────────
# עזר
# ─────────────────────────────────────────────

def _log(theater: str, results: list):
    if results:
        print(f"✅ {theater}: נמצאו {len(results)} הופעות")
    else:
        print(f"⚠️  {theater}: הסריקה הסתיימה אך נמצאו 0 הופעות "
              f"(ייתכן שינוי במבנה האתר – יש לבדוק בדפדפן)")


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=True בייצור
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="he-IL",
        )
        # הסתרת webdriver fingerprint
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()
        all_results: list[dict] = []

        scrapers = [
            scrape_cameri,
            scrape_lessin,
            scrape_habima,
            scrape_gesher,
            scrape_tzavta,
            scrape_jerusalem,
            scrape_khan,
        ]

        for scraper in scrapers:
            await asyncio.sleep(3)  # הפסקה בין אתרים
            res = await scraper(page)
            all_results.extend(res)

        # ─── שמירת תוצאות ───
        output_file = "all_theaters_schedule.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)

        print(f"\n🚀 סיום: סה\"כ {len(all_results)} הופעות נשמרו ב-{output_file}")
        print("\n📋 סיכום לפי תיאטרון:")
        from collections import Counter
        counts = Counter(r["theater"] for r in all_results)
        for t, c in counts.most_common():
            print(f"   {t}: {c}")

        await asyncio.sleep(10)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
