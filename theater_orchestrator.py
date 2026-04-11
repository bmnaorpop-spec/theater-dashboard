from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import re

# --- פונקציות סריקה ייעודיות ---

def scrape_cameri(page, offset):
    print(f"סורק קאמרי: אופסט {offset}...")
    try:
        page.goto(f"https://www.cameri.co.il/לוח-הופעות/?month={offset}", timeout=60000)
        page.wait_for_selector('.event-container', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        return [{"theater": "הקאמרי", "date": e.find('p', class_='date').text.strip(), "title": e.find('h3', class_='visuallyhidden').text.strip(), "time": t[1], "link": f"https://tickets.cameri.co.il/order/{t[3]}"} 
                for e in soup.find_all('div', class_='event-container') if e.get('data-times') for t in json.loads(e.get('data-times'))]
    except: return []

def scrape_habima(page, y, m):
    print(f"סורק הבימה: {m}/{y}...")
    try:
        page.goto(f"https://www.habima.co.il/presentations/?date={y}-{m:02d}-01", timeout=60000)
        page.wait_for_selector('.calendar-day__content', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for day in soup.find_all('div', class_='calendar-day__content'):
            date = day.find('button', class_='date').get('aria-label', '').split(':')[-1].strip()
            if f"/{m}/" not in date and f"/{m:02d}/" not in date: continue
            for item in day.find_all('li', class_='item'):
                link = item.find('a')
                if link:
                    parts = link.text.strip().rsplit('-', 1)
                    shows.append({"theater": "הבימה", "date": date, "title": parts[0].strip(), "time": parts[1].strip() if len(parts)>1 else "", "link": link.get('href', '')})
        return shows
    except: return []

def scrape_lessin(page):
    print("סורק בית ליסין...")
    try:
        page.goto("https://www.lessin.co.il/%D7%94%D7%A6%D7%92%D7%95%D7%AA/", timeout=60000)
        page.wait_for_selector('.showlistitem', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        return [{"theater": "בית ליסין", "date": r.get('data-date','').replace('-','/'), "title": (r.find('strong') or r.find('a')).text.strip(), "time": r.find('a').text.strip(), "link": r.find('a')['href']} 
                for r in soup.find_all('tr', class_='showlistitem') if r.get('data-date')]
    except: return []

def scrape_gesher(page, y, m):
    print(f"סורק גשר: {m}/{y}...")
    try:
        page.goto(f"https://www.gesher-theatre.co.il/he/company/a/calendar/?Month={m}&Year={y}", timeout=60000)
        page.wait_for_selector('.showItemList', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for i in soup.find_all('li', class_='showItemList'):
            title = i.find('div', class_='showItemListName')
            link = i.find('div', class_='showItemListBtn').find('a') if i.find('div', class_='showItemListBtn') else None
            if title:
                shows.append({"theater": "גשר", "date": i.find('div', class_='showItemListDate').text.strip(), "title": title.text.strip(), "time": i.find('div', class_='showItemListTime').text.strip(), "link": "https://www.gesher-theatre.co.il"+link['href'] if link else ""})
        return shows
    except: return []

def scrape_jerusalem(page):
    print("סורק תיאטרון ירושלים...")
    try:
        page.goto("https://www.jerusalem-theatre.co.il/%D7%9C%D7%95%D7%97_%D7%90%D7%99%D7%A8%D7%95%D7%A2%D7%99%D7%9D", timeout=60000)
        page.wait_for_selector('.list-events', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for row in soup.find_all('tr'):
            time_tag = row.find('time', datetime=True)
            title_el = row.find('td', class_='name')
            if time_tag and title_el:
                dt = time_tag['datetime'].split(' ')
                shows.append({"theater": "תיאטרון ירושלים", "date": dt[0].replace('-', '/'), "title": title_el.text.strip(), "time": dt[1] if len(dt) > 1 else "", "link": title_el.find('a')['href'] if title_el.find('a') else ""})
        return shows
    except: return []

def scrape_khan(page):
    print("סורק החאן...")
    try:
        page.goto("https://www.khan.co.il/shows-list", timeout=60000)
        page.wait_for_selector('.board-shows', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        for item in soup.find_all('li', attrs={"data-group": "showsGroups"}):
            time_tag = item.find('time', datetime=True)
            title_el = item.find('h4')
            if time_tag and title_el:
                dt = time_tag['datetime'].split(' ')
                return [{"theater": "החאן", "date": dt[0].replace('.', '/'), "title": title_el.text.strip(), "time": dt[1] if len(dt) > 1 else "", "link": item.find('a', class_='ticket')['href'] if item.find('a', class_='ticket') else ""}]
    except: return []

def scrape_tzavta(page, m):
    print(f"סורק צוותא: חודש {m}...")
    try:
        page.goto(f"https://www.tzavta.co.il/shows/{m}", timeout=60000)
        page.wait_for_selector('.shedule_item', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        return [{"theater": "צוותא", "date": i.find('div', class_='date').text.strip(), "title": i.find('a', class_='shedule_name_txt').text.strip(), "time": i.find('div', class_='time').text.strip(), "link": "https://www.tzavta.co.il"+i.find('a')['href']} 
                for i in soup.find_all('li', class_='shedule_item') if i.find('a')]
    except: return []

def scrape_yiddishpiel(page):
    print("סורק יידישפיל...")
    try:
        page.goto("https://yiddishpiel.co.il/plays/", timeout=60000)
        page.wait_for_selector('.wp-block-post-title', timeout=20000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        # יידישפיל משתמש ב-WP Blocks
        items = soup.find_all('li', class_='wp-block-post')
        for item in items:
            title_el = item.find('h2', class_='wp-block-post-title')
            link_el = title_el.find('a') if title_el else None
            if title_el:
                shows.append({
                    "theater": "יידישפיל",
                    "date": "ראה פרטים בקישור",
                    "title": title_el.text.strip(),
                    "time": "ראה באתר",
                    "link": link_el['href'] if link_el else ""
                })
        return shows
    except: return []

def scrape_jaffa(page):
    print("סורק תיאטרון יפו...")
    try:
        page.goto("https://www.jaffatheatre.org.il/events/", timeout=60000)
        page.wait_for_selector('.tribe-events-calendar-list__event-title', timeout=20000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for item in soup.find_all('article', class_=re.compile('tribe-events-calendar-list__event')):
            title_el = item.find('h3', class_='tribe-events-calendar-list__event-title')
            date_el = item.find('time', class_='tribe-events-calendar-list__event-datetime')
            if title_el:
                shows.append({"theater": "תיאטרון יפו", "date": date_el.text.strip() if date_el else "", "title": title_el.text.strip(), "time": "ראה בקישור", "link": title_el.find('a')['href'] if title_el.find('a') else ""})
        return shows
    except: return []

def scrape_incubator(page):
    print("סורק אינקובטור...")
    try:
        page.goto("https://incubator.org.il/show-type/play-category/", timeout=60000)
        page.wait_for_selector('.jet-listing-grid', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for item in soup.find_all('div', class_='jet-listing-grid__item'):
            f = item.find_all('div', class_='jet-listing-dynamic-field__content')
            if len(f) >= 2:
                shows.append({"theater": "האינקובטור", "date": f[1].text.strip(), "title": f[0].text.strip(), "time": f[2].text.strip() if len(f)>2 else "", "link": item.find('a')['href'] if item.find('a') else ""})
        return shows
    except: return []

def scrape_habait(page):
    print("סורק תיאטרון הבית...")
    try:
        page.goto("https://www.habait-theatre.org.il/he/home#!95", timeout=60000)
        page.wait_for_selector('.project-title', timeout=20000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for i in soup.find_all('div', class_='element_holder'):
            t = i.find('h3', class_='project-title')
            if t:
                parts = t.text.split('//')
                shows.append({"theater": "תיאטרון הבית", "date": parts[1].strip() if len(parts)>1 else "", "title": parts[0].strip(), "time": "ראה באתר", "link": "https://www.habait-theatre.org.il"+i.find('a')['href'] if i.find('a') else ""})
        return shows
    except: return []

def scrape_nikonitai(page):
    print("סורק ניקו ניתאי...")
    try:
        page.goto("https://nikonitai.smarticket.co.il/", timeout=60000)
        page.wait_for_selector('.show_cube', timeout=15000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        shows = []
        for c in soup.find_all('div', class_='show_cube'):
            name = c.find('div', id=re.compile('show_name_'))
            dt = c.find('div', id=re.compile('show_datetime_'))
            if name:
                shows.append({"theater": "ניקו ניתאי", "date": dt.text.strip() if dt else "", "title": name.text.strip(), "time": "כלול בתאריך", "link": c.find('a')['href'] if c.find('a') else ""})
        return shows
    except: return []

def scrape_wix_theaters(page, url, theater_name):
    print(f"סורק {theater_name} (Wix)...")
    try:
        page.goto(url, timeout=60000)
        page.wait_for_selector('[data-hook="event-list-item"]', timeout=20000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        return [{"theater": theater_name, "date": i.find(attrs={"data-hook": "ev-date"}).text.strip(), "title": i.find(attrs={"data-hook": "ev-title"}).text.strip(), "time": "ראה באתר", "link": i.find('a')['href']} 
                for i in soup.find_all(attrs={"data-hook": "event-list-item"}) if i.find(attrs={"data-hook": "ev-title"})]
    except: return []

# --- הרצה מרכזית ---

def run_orchestrator():
    all_shows = []
    start = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # איסוף
        for i in [0, 1, 2]: all_shows.extend(scrape_cameri(page, i))
        for m in [4, 5, 6]: 
            all_shows.extend(scrape_habima(page, 2026, m))
            all_shows.extend(scrape_gesher(page, 2026, m))
            all_shows.extend(scrape_tzavta(page, m))
        
        all_shows.extend(scrape_lessin(page))
        all_shows.extend(scrape_jerusalem(page))
        all_shows.extend(scrape_khan(page))
        all_shows.extend(scrape_yiddishpiel(page)) # הוספת יידישפיל
        all_shows.extend(scrape_incubator(page))
        all_shows.extend(scrape_jaffa(page))
        all_shows.extend(scrape_habait(page))
        all_shows.extend(scrape_nikonitai(page))
        all_shows.extend(scrape_wix_theaters(page, "https://www.hanut31.co.il/%D7%94%D7%A6%D7%92%D7%95%D7%AA", "החנות"))
        all_shows.extend(scrape_wix_theaters(page, "https://www.homemade-dancetheater.com/event-list", "תוצרת בית"))
        
        browser.close()

    # סינון כפילויות ושמירה
    unique = list({(s['theater'], s['title'], s['date'], s['time']): s for s in all_shows}.values())
    with open('all_theaters_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    
    print(f"\n--- סיכום: {len(unique)} הופעות ייחודיות נשמרו ב-{int(time.time()-start)} שניות ---")

if __name__ == "__main__":
    run_orchestrator()